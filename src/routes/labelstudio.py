from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.project import Project
from src.models.dataset import Dataset, DataItem
from src.services.labelstudio_service import get_labelstudio_service
from src.routes.auth import token_required
import json

labelstudio_bp = Blueprint('labelstudio', __name__)

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio', methods=['POST'])
@token_required
def create_labelstudio_project(current_user, project_id):
    """Create a Label Studio project for an existing AI Bridge project"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        # Get request data
        data = request.get_json()
        label_config_type = data.get('label_config_type', 'image_classification')
        custom_label_config = data.get('custom_label_config')
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Get label configuration
        if custom_label_config:
            label_config = custom_label_config
        else:
            templates = ls_service.get_label_config_templates()
            label_config = templates.get(label_config_type, templates['image_classification'])
        
        # Create Label Studio project
        ls_project = ls_service.create_project(
            name=f"{project.name} - Labeling",
            description=f"Data labeling project for {project.name}: {project.description}",
            label_config=label_config
        )
        
        # Update AI Bridge project with Label Studio project ID
        project.labelstudio_project_id = ls_project['id']
        project.annotation_schema = {
            'labelstudio_config': label_config,
            'config_type': label_config_type
        }
        db.session.commit()
        
        return jsonify({
            'message': 'Label Studio project created successfully',
            'labelstudio_project': ls_project,
            'ai_bridge_project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create Label Studio project: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/sync', methods=['POST'])
@token_required
def sync_data_to_labelstudio(current_user, project_id):
    """Sync dataset files to Label Studio as tasks"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not project.labelstudio_project_id:
            return jsonify({'message': 'No Label Studio project associated with this project'}), 400
        
        # Get dataset ID from request
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        
        if dataset_id:
            # Sync specific dataset
            dataset = Dataset.query.filter_by(id=dataset_id, project_id=project_id).first()
            if not dataset:
                return jsonify({'message': 'Dataset not found'}), 404
            
            datasets = [dataset]
        else:
            # Sync all datasets in the project
            datasets = Dataset.query.filter_by(project_id=project_id).all()
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        total_synced = 0
        sync_results = []
        
        for dataset in datasets:
            # Get all data items in the dataset
            data_items = DataItem.query.filter_by(dataset_id=dataset.id).all()
            
            if not data_items:
                continue
            
            # Extract S3 file keys
            file_keys = [item.file_path for item in data_items]
            
            # Create tasks in Label Studio
            result = ls_service.create_tasks_from_s3_files(
                project_id=project.labelstudio_project_id,
                s3_file_keys=file_keys,
                data_type=dataset.data_type or project.data_type
            )
            
            total_synced += result.get('task_count', 0)
            sync_results.append({
                'dataset_id': dataset.id,
                'dataset_name': dataset.name,
                'files_synced': len(file_keys),
                'tasks_created': result.get('task_count', 0),
                'result': result
            })
        
        return jsonify({
            'message': f'Successfully synced {total_synced} tasks to Label Studio',
            'total_tasks_created': total_synced,
            'sync_results': sync_results
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to sync data: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/tasks', methods=['GET'])
@token_required
def get_labelstudio_tasks(current_user, project_id):
    """Get tasks from Label Studio project"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not project.labelstudio_project_id:
            return jsonify({'message': 'No Label Studio project associated with this project'}), 400
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Get tasks from Label Studio
        tasks = ls_service.get_tasks(
            project_id=project.labelstudio_project_id,
            page=page,
            page_size=page_size
        )
        
        return jsonify(tasks), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get tasks: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/annotations/export', methods=['GET'])
@token_required
def export_labelstudio_annotations(current_user, project_id):
    """Export annotations from Label Studio project"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not project.labelstudio_project_id:
            return jsonify({'message': 'No Label Studio project associated with this project'}), 400
        
        # Get export type from query parameters
        export_type = request.args.get('export_type', 'JSON')
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Export annotations
        annotations = ls_service.export_annotations(
            project_id=project.labelstudio_project_id,
            export_type=export_type
        )
        
        return jsonify({
            'message': 'Annotations exported successfully',
            'export_type': export_type,
            'annotations': annotations
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to export annotations: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/config', methods=['GET'])
@token_required
def get_labelstudio_config(current_user, project_id):
    """Get Label Studio project configuration"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not project.labelstudio_project_id:
            return jsonify({'message': 'No Label Studio project associated with this project'}), 400
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Get project details from Label Studio
        ls_project = ls_service.get_project(project.labelstudio_project_id)
        
        return jsonify({
            'labelstudio_project': ls_project,
            'ai_bridge_project': project.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get configuration: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/config', methods=['PUT'])
@token_required
def update_labelstudio_config(current_user, project_id):
    """Update Label Studio project configuration"""
    try:
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not project.labelstudio_project_id:
            return jsonify({'message': 'No Label Studio project associated with this project'}), 400
        
        # Get update data
        data = request.get_json()
        
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Update Label Studio project
        updated_project = ls_service.update_project(
            project_id=project.labelstudio_project_id,
            data=data
        )
        
        # Update AI Bridge project annotation schema if label_config changed
        if 'label_config' in data:
            project.annotation_schema = project.annotation_schema or {}
            project.annotation_schema['labelstudio_config'] = data['label_config']
            db.session.commit()
        
        return jsonify({
            'message': 'Label Studio project updated successfully',
            'labelstudio_project': updated_project
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update configuration: {str(e)}'}), 500

@labelstudio_bp.route('/labelstudio/templates', methods=['GET'])
@token_required
def get_label_config_templates(current_user):
    """Get available label configuration templates"""
    try:
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Get templates
        templates = ls_service.get_label_config_templates()
        
        return jsonify({
            'templates': templates,
            'available_types': list(templates.keys())
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get templates: {str(e)}'}), 500

@labelstudio_bp.route('/labelstudio/status', methods=['GET'])
@token_required
def check_labelstudio_status(current_user):
    """Check Label Studio service status"""
    try:
        # Get Label Studio service
        ls_service = get_labelstudio_service()
        
        # Validate connection
        is_connected = ls_service.validate_connection()
        
        return jsonify({
            'status': 'connected' if is_connected else 'disconnected',
            'url': ls_service.label_studio_url,
            'has_token': bool(ls_service.api_token)
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

