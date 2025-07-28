"""
Enhanced Label Studio API Routes with Arabic/RTL Support
"""
from flask import Blueprint, request, jsonify
from src.services.labelstudio_enhanced import labelstudio_service
from src.services.s3_service import s3_service
from src.services.redis_service import redis_service
from src.models.project import Project
from src.models.dataset import Dataset, DataItem
import json

labelstudio_bp = Blueprint('labelstudio', __name__)

@labelstudio_bp.route('/status')
def get_status():
    """Get Label Studio service status"""
    try:
        is_connected = labelstudio_service.check_connection()
        
        status = {
            'service': 'Label Studio',
            'status': 'connected' if is_connected else 'disconnected',
            'url': labelstudio_service.base_url,
            'templates_available': len(labelstudio_service.get_annotation_templates())
        }
        
        if is_connected:
            return jsonify(status), 200
        else:
            return jsonify(status), 503
            
    except Exception as e:
        return jsonify({'error': f'Failed to check Label Studio status: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio', methods=['POST'])
def create_labelstudio_project(project_id):
    """Create a Label Studio project for an AI Bridge project"""
    try:
        # Get AI Bridge project
        project = Project.query.get_or_404(project_id)
        
        # Get request data
        data = request.get_json() or {}
        
        # Prepare Label Studio project configuration
        annotation_type = data.get('annotation_type', 'text_classification')
        templates = labelstudio_service.get_annotation_templates()
        
        project_config = {
            'title': f"{project.name} - Annotation Project",
            'description': project.description or f"Data labeling project for {project.name}",
            'label_config': templates.get(annotation_type, templates['text_classification']),
            'instructions': data.get('instructions', 'Please annotate the data according to the project guidelines.'),
            'ai_bridge_project_id': project_id
        }
        
        # Create Label Studio project
        ls_project = labelstudio_service.create_project(project_config)
        
        if ls_project:
            # Update AI Bridge project with Label Studio project ID
            project.labelstudio_project_id = ls_project['id']
            project.annotation_config = json.dumps({
                'annotation_type': annotation_type,
                'labelstudio_project_id': ls_project['id'],
                'instructions': data.get('instructions', ''),
                'created_at': ls_project.get('created_at')
            })
            
            from src.models.user import db
            db.session.commit()
            
            return jsonify({
                'message': 'Label Studio project created successfully',
                'labelstudio_project': ls_project,
                'ai_bridge_project_id': project_id,
                'annotation_type': annotation_type
            }), 201
        else:
            return jsonify({'error': 'Failed to create Label Studio project'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create Label Studio project: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/sync', methods=['POST'])
def sync_data_to_labelstudio(project_id):
    """Sync AI Bridge project data to Label Studio as tasks"""
    try:
        # Get AI Bridge project
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated with this project'}), 400
        
        # Get project datasets
        datasets = Dataset.query.filter_by(project_id=project_id).all()
        
        if not datasets:
            return jsonify({'error': 'No datasets found for this project'}), 400
        
        # Prepare tasks for Label Studio
        tasks = []
        total_files = 0
        
        for dataset in datasets:
            data_items = DataItem.query.filter_by(dataset_id=dataset.id).all()
            
            for item in data_items:
                # Generate presigned URL for file access
                presigned_url = s3_service.generate_presigned_url(item.s3_key)
                
                if presigned_url:
                    # Determine task format based on file type
                    task_data = {
                        'id': item.id,
                        'data': {}
                    }
                    
                    # Configure task based on file type
                    if item.file_type.startswith('image/'):
                        task_data['data']['image'] = presigned_url
                    elif item.file_type.startswith('audio/'):
                        task_data['data']['audio'] = presigned_url
                    elif item.file_type.startswith('text/') or item.file_type == 'application/json':
                        # For text files, we might want to read content
                        task_data['data']['text'] = f"File: {item.filename}"
                    else:
                        task_data['data']['file'] = presigned_url
                    
                    # Add metadata
                    task_data['data']['filename'] = item.filename
                    task_data['data']['dataset'] = dataset.name
                    task_data['data']['file_size'] = item.file_size
                    task_data['data']['upload_date'] = item.created_at.isoformat()
                    
                    tasks.append(task_data)
                    total_files += 1
        
        if not tasks:
            return jsonify({'error': 'No valid files found to sync'}), 400
        
        # Import tasks to Label Studio
        success = labelstudio_service.import_tasks(project.labelstudio_project_id, tasks)
        
        if success:
            # Cache sync status
            sync_info = {
                'synced_at': 'now',
                'total_tasks': len(tasks),
                'datasets_synced': len(datasets),
                'files_synced': total_files
            }
            redis_service.set(f"labelstudio_sync:{project_id}", sync_info, expire=3600)
            
            return jsonify({
                'message': 'Data synced to Label Studio successfully',
                'total_tasks': len(tasks),
                'datasets_synced': len(datasets),
                'files_synced': total_files,
                'labelstudio_project_id': project.labelstudio_project_id
            }), 200
        else:
            return jsonify({'error': 'Failed to sync data to Label Studio'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to sync data: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/tasks')
def get_labelstudio_tasks(project_id):
    """Get Label Studio tasks for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated'}), 400
        
        # Get project statistics
        stats = labelstudio_service.get_project_stats(project.labelstudio_project_id)
        
        if stats:
            return jsonify({
                'project_id': project_id,
                'labelstudio_project_id': project.labelstudio_project_id,
                'stats': stats
            }), 200
        else:
            return jsonify({'error': 'Failed to get Label Studio tasks'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to get tasks: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/annotations')
def get_annotations(project_id):
    """Get annotations from Label Studio"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated'}), 400
        
        annotations = labelstudio_service.get_annotations(project.labelstudio_project_id)
        
        if annotations is not None:
            return jsonify({
                'project_id': project_id,
                'labelstudio_project_id': project.labelstudio_project_id,
                'total_annotations': len(annotations),
                'annotations': annotations
            }), 200
        else:
            return jsonify({'error': 'Failed to get annotations'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to get annotations: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/annotations/export')
def export_annotations(project_id):
    """Export annotations from Label Studio"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated'}), 400
        
        export_format = request.args.get('format', 'JSON')
        
        exported_data = labelstudio_service.export_annotations(
            project.labelstudio_project_id, 
            export_format
        )
        
        if exported_data:
            return jsonify({
                'project_id': project_id,
                'labelstudio_project_id': project.labelstudio_project_id,
                'export_format': export_format,
                'data': exported_data
            }), 200
        else:
            return jsonify({'error': 'Failed to export annotations'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to export annotations: {str(e)}'}), 500

@labelstudio_bp.route('/templates')
def get_annotation_templates():
    """Get available annotation templates"""
    try:
        templates = labelstudio_service.get_annotation_templates()
        
        return jsonify({
            'templates': templates,
            'total_templates': len(templates),
            'supported_types': list(templates.keys())
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get templates: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/progress')
def get_annotation_progress(project_id):
    """Get real-time annotation progress"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated'}), 400
        
        # Check cache first
        cached_progress = redis_service.get_annotation_progress(project_id)
        if cached_progress:
            return jsonify(cached_progress), 200
        
        # Get fresh stats from Label Studio
        stats = labelstudio_service.get_project_stats(project.labelstudio_project_id)
        
        if stats:
            progress = {
                'project_id': project_id,
                'labelstudio_project_id': project.labelstudio_project_id,
                'total_tasks': stats['total_tasks'],
                'completed_tasks': stats['completed_tasks'],
                'total_annotations': stats['total_annotations'],
                'progress_percentage': stats['progress_percentage'],
                'remaining_tasks': stats['total_tasks'] - stats['completed_tasks'],
                'last_updated': 'now'
            }
            
            # Cache progress
            redis_service.cache_annotation_progress(project_id, progress)
            
            return jsonify(progress), 200
        else:
            return jsonify({'error': 'Failed to get annotation progress'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to get progress: {str(e)}'}), 500

@labelstudio_bp.route('/projects/<int:project_id>/labelstudio/url')
def get_labelstudio_url(project_id):
    """Get Label Studio project URL for direct access"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if not project.labelstudio_project_id:
            return jsonify({'error': 'No Label Studio project associated'}), 400
        
        url = f"{labelstudio_service.base_url}/projects/{project.labelstudio_project_id}/"
        
        return jsonify({
            'project_id': project_id,
            'labelstudio_project_id': project.labelstudio_project_id,
            'labelstudio_url': url,
            'base_url': labelstudio_service.base_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get URL: {str(e)}'}), 500

