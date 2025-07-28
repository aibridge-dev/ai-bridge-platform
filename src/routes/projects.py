from flask import Blueprint, request, jsonify
from src.models.user import db, User, UserRole
from src.models.organization import Organization
from src.models.project import Project, ProjectStatus, ProjectType
from src.routes.auth import token_required, role_required
from datetime import datetime

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/', methods=['GET'])
@token_required
def get_projects(current_user):
    """Get projects based on user role"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        project_type = request.args.get('type')
        
        # Build query based on user role
        query = Project.query
        
        if current_user.is_client_user:
            # Client users see only their organization's projects
            query = query.filter(Project.organization_id == current_user.organization_id)
        elif current_user.role == UserRole.LABELER:
            # Labelers see projects they're assigned to
            query = query.join(Project.annotations).filter_by(labeler_id=current_user.id)
        elif current_user.role == UserRole.REVIEWER:
            # Reviewers see projects they're reviewing
            query = query.join(Project.reviews).filter_by(reviewer_id=current_user.id)
        # Admins and project managers see all projects
        
        # Apply filters
        if status:
            try:
                status_enum = ProjectStatus(status)
                query = query.filter(Project.status == status_enum)
            except ValueError:
                return jsonify({'message': 'Invalid status value'}), 400
        
        if project_type:
            try:
                type_enum = ProjectType(project_type)
                query = query.filter(Project.project_type == type_enum)
            except ValueError:
                return jsonify({'message': 'Invalid project type value'}), 400
        
        # Order by creation date (newest first)
        query = query.order_by(Project.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        projects = [project.to_dict() for project in pagination.items]
        
        return jsonify({
            'projects': projects,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get projects: {str(e)}'}), 500

@projects_bp.route('/', methods=['POST'])
@token_required
@role_required(UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.CLIENT_ADMIN)
def create_project(current_user):
    """Create a new project"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'project_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400
        
        # Validate project type
        try:
            project_type = ProjectType(data['project_type'])
        except ValueError:
            return jsonify({'message': 'Invalid project type'}), 400
        
        # Determine organization
        organization_id = current_user.organization_id
        if current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
            # AI Bridge staff can create projects for any organization
            organization_id = data.get('organization_id', organization_id)
            if organization_id and not Organization.query.get(organization_id):
                return jsonify({'message': 'Organization not found'}), 404
        
        # Create project
        project = Project(
            name=data['name'].strip(),
            description=data.get('description', '').strip(),
            project_type=project_type,
            organization_id=organization_id,
            manager_id=current_user.id if current_user.role == UserRole.PROJECT_MANAGER else None,
            annotation_schema=data.get('annotation_schema'),
            quality_threshold=data.get('quality_threshold', 0.95),
            instructions=data.get('instructions', '').strip(),
            estimated_hours=data.get('estimated_hours'),
            hourly_rate=data.get('hourly_rate'),
            fixed_price=data.get('fixed_price')
        )
        
        # Parse deadline if provided
        if data.get('deadline'):
            try:
                project.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'message': 'Invalid deadline format. Use ISO format.'}), 400
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project created successfully',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Project creation failed: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
@token_required
def get_project(current_user, project_id):
    """Get a specific project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check access permissions
        if current_user.is_client_user and project.organization_id != current_user.organization_id:
            return jsonify({'message': 'Access denied'}), 403
        
        return jsonify({'project': project.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get project: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@token_required
@role_required(UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.CLIENT_ADMIN)
def update_project(current_user, project_id):
    """Update a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check access permissions
        if current_user.is_client_user and project.organization_id != current_user.organization_id:
            return jsonify({'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['name', 'description', 'annotation_schema', 'quality_threshold',
                         'instructions', 'estimated_hours', 'hourly_rate', 'fixed_price']
        
        for field in allowed_fields:
            if field in data:
                setattr(project, field, data[field])
        
        # Update project type if provided
        if 'project_type' in data:
            try:
                project.project_type = ProjectType(data['project_type'])
            except ValueError:
                return jsonify({'message': 'Invalid project type'}), 400
        
        # Update status if provided
        if 'status' in data:
            try:
                new_status = ProjectStatus(data['status'])
                
                # Handle status transitions
                if new_status == ProjectStatus.ACTIVE and project.status == ProjectStatus.DRAFT:
                    project.started_at = datetime.utcnow()
                elif new_status == ProjectStatus.COMPLETED and project.status != ProjectStatus.COMPLETED:
                    project.completed_at = datetime.utcnow()
                
                project.status = new_status
            except ValueError:
                return jsonify({'message': 'Invalid status value'}), 400
        
        # Update deadline if provided
        if 'deadline' in data:
            if data['deadline']:
                try:
                    project.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'message': 'Invalid deadline format. Use ISO format.'}), 400
            else:
                project.deadline = None
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Project updated successfully',
            'project': project.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Project update failed: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@token_required
@role_required(UserRole.ADMIN, UserRole.PROJECT_MANAGER)
def delete_project(current_user, project_id):
    """Delete a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Only allow deletion of draft projects or by admin
        if project.status != ProjectStatus.DRAFT and current_user.role != UserRole.ADMIN:
            return jsonify({'message': 'Only draft projects can be deleted'}), 400
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'message': 'Project deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Project deletion failed: {str(e)}'}), 500

@projects_bp.route('/<int:project_id>/stats', methods=['GET'])
@token_required
def get_project_stats(current_user, project_id):
    """Get project statistics"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check access permissions
        if current_user.is_client_user and project.organization_id != current_user.organization_id:
            return jsonify({'message': 'Access denied'}), 403
        
        # Calculate statistics
        stats = {
            'total_items': project.total_items,
            'completed_items': project.completed_items,
            'approved_items': project.approved_items,
            'progress_percentage': project.progress_percentage,
            'approval_percentage': project.approval_percentage,
            'datasets_count': project.datasets.count(),
            'annotations_count': project.annotations.count(),
            'reviews_count': project.reviews.count(),
            'active_labelers': project.annotations.filter_by(status='in_progress').distinct().count(),
            'pending_reviews': project.reviews.filter_by(status='pending').count()
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get project stats: {str(e)}'}), 500

