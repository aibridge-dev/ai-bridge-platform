from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from src.models.user import db
from src.models.dataset import Dataset, DataItem
from src.models.project import Project
from src.services.s3_service import get_s3_service
from src.routes.auth import token_required
import os
import hashlib
from datetime import datetime
import mimetypes
import tempfile
import requests

files_bp = Blueprint('files', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'images': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'},
    'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
    'audio': {'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg'},
    'video': {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'},
    'data': {'csv', 'json', 'xml', 'xlsx', 'xls'},
    'archives': {'zip', 'rar', '7z', 'tar', 'gz'}
}

ALL_ALLOWED_EXTENSIONS = set()
for extensions in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(extensions)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALL_ALLOWED_EXTENSIONS

def get_file_category(filename):
    if '.' not in filename:
        return 'other'
    
    ext = filename.rsplit('.', 1)[1].lower()
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return category
    return 'other'

@files_bp.route('/upload', methods=['POST'])
@token_required
def upload_files(current_user):
    """Upload files to S3 and create dataset entries"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({'message': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'message': 'No files selected'}), 400
        
        # Get project_id from form data
        project_id = request.form.get('project_id')
        if not project_id:
            return jsonify({'message': 'Project ID is required'}), 400
        
        # Verify project exists and user has access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        # Get or create dataset
        dataset_name = request.form.get('dataset_name', f'Dataset_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}')
        dataset = Dataset.query.filter_by(project_id=project_id, name=dataset_name).first()
        
        if not dataset:
            dataset = Dataset(
                name=dataset_name,
                project_id=project_id,
                description=request.form.get('dataset_description', ''),
                data_type=request.form.get('data_type', 'mixed'),
                created_by=current_user.id
            )
            db.session.add(dataset)
            db.session.flush()  # Get dataset ID
        
        # Initialize S3 service
        s3_service = get_s3_service()
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename):
                failed_files.append({
                    'filename': file.filename,
                    'error': 'File type not allowed'
                })
                continue
            
            try:
                # Upload to S3
                s3_metadata = s3_service.upload_file(
                    file_obj=file,
                    project_id=project_id,
                    dataset_id=dataset.id,
                    filename=file.filename
                )
                
                # Create DataItem record
                data_item = DataItem(
                    dataset_id=dataset.id,
                    filename=file.filename,
                    file_path=s3_metadata['file_key'],  # S3 key
                    file_size=s3_metadata['file_size'],
                    file_hash=s3_metadata['file_hash'],
                    content_type=s3_metadata['content_type'],
                    file_metadata={
                        'bucket': s3_metadata['bucket'],
                        'region': s3_metadata['region'],
                        'category': get_file_category(file.filename),
                        'upload_method': 's3_direct'
                    },
                    uploaded_by=current_user.id
                )
                
                db.session.add(data_item)
                
                uploaded_files.append({
                    'id': data_item.id,
                    'filename': file.filename,
                    'file_size': s3_metadata['file_size'],
                    'content_type': s3_metadata['content_type'],
                    'file_key': s3_metadata['file_key']
                })
                
            except Exception as e:
                failed_files.append({
                    'filename': file.filename,
                    'error': str(e)
                })
        
        # Update dataset statistics
        dataset.total_items = DataItem.query.filter_by(dataset_id=dataset.id).count()
        dataset.total_size = db.session.query(db.func.sum(DataItem.file_size)).filter_by(dataset_id=dataset.id).scalar() or 0
        
        # Update project statistics
        project.total_items = db.session.query(db.func.sum(Dataset.total_items)).filter_by(project_id=project_id).scalar() or 0
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully uploaded {len(uploaded_files)} files',
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'uploaded_files': uploaded_files,
            'failed_files': failed_files
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Upload failed: {str(e)}'}), 500

@files_bp.route('/download/<int:file_id>', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    """Generate presigned URL for file download"""
    try:
        # Get file record
        data_item = DataItem.query.join(Dataset).join(Project).filter(
            DataItem.id == file_id,
            Project.organization_id == current_user.organization_id
        ).first()
        
        if not data_item:
            return jsonify({'message': 'File not found or access denied'}), 404
        
        # Generate presigned URL
        s3_service = get_s3_service()
        presigned_url = s3_service.generate_presigned_url(
            file_key=data_item.file_path,
            expiration=3600  # 1 hour
        )
        
        return jsonify({
            'download_url': presigned_url,
            'filename': data_item.filename,
            'content_type': data_item.content_type,
            'file_size': data_item.file_size,
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Download failed: {str(e)}'}), 500

@files_bp.route('/presigned-upload', methods=['POST'])
@token_required
def get_presigned_upload_url(current_user):
    """Generate presigned URL for direct browser upload to S3"""
    try:
        data = request.get_json()
        
        project_id = data.get('project_id')
        filename = data.get('filename')
        content_type = data.get('content_type')
        
        if not all([project_id, filename]):
            return jsonify({'message': 'Project ID and filename are required'}), 400
        
        # Verify project access
        project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
        if not project:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        if not allowed_file(filename):
            return jsonify({'message': 'File type not allowed'}), 400
        
        # Generate S3 key
        s3_service = get_s3_service()
        file_key = s3_service.generate_file_key(project_id, 'temp', filename)
        
        # Generate presigned POST
        presigned_post = s3_service.generate_presigned_post(
            file_key=file_key,
            expiration=3600,
            max_file_size=100*1024*1024  # 100MB
        )
        
        return jsonify({
            'presigned_post': presigned_post,
            'file_key': file_key,
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to generate presigned URL: {str(e)}'}), 500

@files_bp.route('/datasets/<int:dataset_id>/files', methods=['GET'])
@token_required
def list_dataset_files(current_user, dataset_id):
    """List all files in a dataset with presigned URLs"""
    try:
        # Verify dataset access
        dataset = Dataset.query.join(Project).filter(
            Dataset.id == dataset_id,
            Project.organization_id == current_user.organization_id
        ).first()
        
        if not dataset:
            return jsonify({'message': 'Dataset not found or access denied'}), 404
        
        # Get files with pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        files_query = DataItem.query.filter_by(dataset_id=dataset_id)
        files_paginated = files_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Generate presigned URLs for files
        s3_service = get_s3_service()
        files_with_urls = []
        
        for data_item in files_paginated.items:
            try:
                presigned_url = s3_service.generate_presigned_url(
                    file_key=data_item.file_path,
                    expiration=3600
                )
                
                file_info = data_item.to_dict()
                file_info['download_url'] = presigned_url
                file_info['expires_in'] = 3600
                files_with_urls.append(file_info)
                
            except Exception as e:
                # If presigned URL generation fails, include file without URL
                file_info = data_item.to_dict()
                file_info['download_url'] = None
                file_info['error'] = str(e)
                files_with_urls.append(file_info)
        
        return jsonify({
            'files': files_with_urls,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': files_paginated.total,
                'pages': files_paginated.pages,
                'has_next': files_paginated.has_next,
                'has_prev': files_paginated.has_prev
            },
            'dataset': dataset.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to list files: {str(e)}'}), 500

@files_bp.route('/delete/<int:file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user, file_id):
    """Delete a file from S3 and database"""
    try:
        # Get file record
        data_item = DataItem.query.join(Dataset).join(Project).filter(
            DataItem.id == file_id,
            Project.organization_id == current_user.organization_id
        ).first()
        
        if not data_item:
            return jsonify({'message': 'File not found or access denied'}), 404
        
        # Delete from S3
        s3_service = get_s3_service()
        s3_service.delete_file(data_item.file_path)
        
        # Delete from database
        dataset_id = data_item.dataset_id
        db.session.delete(data_item)
        
        # Update dataset statistics
        dataset = Dataset.query.get(dataset_id)
        if dataset:
            dataset.total_items = DataItem.query.filter_by(dataset_id=dataset_id).count()
            dataset.total_size = db.session.query(db.func.sum(DataItem.file_size)).filter_by(dataset_id=dataset_id).scalar() or 0
        
        db.session.commit()
        
        return jsonify({'message': 'File deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Delete failed: {str(e)}'}), 500

