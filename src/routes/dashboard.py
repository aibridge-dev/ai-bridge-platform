"""
Dashboard routes for role-based user interfaces
"""
from flask import Blueprint, request, jsonify, g
from src.models.user import User, UserRole
from src.models.project import Project
from src.models.dataset import Dataset
from src.models.annotation import Annotation
from src.models.organization import Organization
from src.routes.auth import token_required
from src.services.redis_service import redis_service
from datetime import datetime, timedelta
from sqlalchemy import func, desc

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/admin', methods=['GET'])
@token_required
def admin_dashboard():
    """Admin dashboard with system-wide statistics"""
    if g.current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Check cache first
        cache_key = 'admin_dashboard_stats'
        cached_data = redis_service.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Calculate fresh statistics
        stats = {
            'overview': {
                'total_users': User.query.count(),
                'active_users': User.query.filter_by(is_active=True).count(),
                'total_organizations': Organization.query.count(),
                'total_projects': Project.query.count(),
                'active_projects': Project.query.filter_by(status='active').count(),
                'total_datasets': Dataset.query.count(),
                'total_annotations': Annotation.query.count()
            },
            'user_breakdown': {
                'admins': User.query.filter_by(role=UserRole.ADMIN).count(),
                'project_managers': User.query.filter_by(role=UserRole.PROJECT_MANAGER).count(),
                'labelers': User.query.filter_by(role=UserRole.LABELER).count(),
                'reviewers': User.query.filter_by(role=UserRole.REVIEWER).count(),
                'client_admins': User.query.filter_by(role=UserRole.CLIENT_ADMIN).count(),
                'client_users': User.query.filter_by(role=UserRole.CLIENT_USER).count()
            },
            'recent_activity': {
                'new_users_this_week': User.query.filter(
                    User.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count(),
                'new_projects_this_week': Project.query.filter(
                    Project.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count(),
                'annotations_this_week': Annotation.query.filter(
                    Annotation.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
            }
        }
        
        # Get recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
        stats['recent_users'] = [user.to_dict() for user in recent_users]
        
        # Get recent projects
        recent_projects = Project.query.order_by(desc(Project.created_at)).limit(10).all()
        stats['recent_projects'] = [project.to_dict() for project in recent_projects]
        
        # Cache for 5 minutes
        redis_service.set(cache_key, stats, expire=300)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch admin dashboard: {str(e)}'}), 500

@dashboard_bp.route('/client', methods=['GET'])
@token_required
def client_dashboard():
    """Client dashboard with organization-specific data"""
    if not g.current_user.is_client_user:
        return jsonify({'error': 'Client access required'}), 403
    
    try:
        organization_id = g.current_user.organization_id
        if not organization_id:
            return jsonify({'error': 'No organization associated with user'}), 400
        
        # Check cache first
        cache_key = f'client_dashboard_stats_{organization_id}'
        cached_data = redis_service.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get organization projects
        projects = Project.query.filter_by(organization_id=organization_id).all()
        project_ids = [p.id for p in projects]
        
        # Calculate statistics
        stats = {
            'overview': {
                'total_projects': len(projects),
                'active_projects': len([p for p in projects if p.status == 'active']),
                'completed_projects': len([p for p in projects if p.status == 'completed']),
                'total_datasets': Dataset.query.filter(Dataset.project_id.in_(project_ids)).count() if project_ids else 0,
                'total_annotations': Annotation.query.join(Dataset).filter(Dataset.project_id.in_(project_ids)).count() if project_ids else 0
            },
            'project_status': {
                'draft': len([p for p in projects if p.status == 'draft']),
                'active': len([p for p in projects if p.status == 'active']),
                'review': len([p for p in projects if p.status == 'review']),
                'completed': len([p for p in projects if p.status == 'completed']),
                'paused': len([p for p in projects if p.status == 'paused'])
            },
            'recent_activity': {
                'projects_this_month': len([p for p in projects if p.created_at >= datetime.utcnow() - timedelta(days=30)]),
                'annotations_this_week': Annotation.query.join(Dataset).filter(
                    Dataset.project_id.in_(project_ids),
                    Annotation.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count() if project_ids else 0
            }
        }
        
        # Get recent projects
        recent_projects = sorted(projects, key=lambda x: x.created_at, reverse=True)[:5]
        stats['recent_projects'] = [project.to_dict() for project in recent_projects]
        
        # Get project progress
        project_progress = []
        for project in projects[:10]:  # Limit to 10 most recent projects
            datasets = Dataset.query.filter_by(project_id=project.id).all()
            total_items = sum(dataset.item_count or 0 for dataset in datasets)
            completed_annotations = Annotation.query.join(Dataset).filter(
                Dataset.project_id == project.id,
                Annotation.status == 'completed'
            ).count()
            
            progress_percentage = (completed_annotations / total_items * 100) if total_items > 0 else 0
            
            project_progress.append({
                'project_id': project.id,
                'project_name': project.name,
                'total_items': total_items,
                'completed_annotations': completed_annotations,
                'progress_percentage': round(progress_percentage, 2),
                'status': project.status
            })
        
        stats['project_progress'] = project_progress
        
        # Cache for 3 minutes
        redis_service.set(cache_key, stats, expire=180)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch client dashboard: {str(e)}'}), 500

@dashboard_bp.route('/annotator', methods=['GET'])
@token_required
def annotator_dashboard():
    """Annotator dashboard with task assignments and performance"""
    if g.current_user.role not in [UserRole.LABELER, UserRole.REVIEWER]:
        return jsonify({'error': 'Annotator access required'}), 403
    
    try:
        user_id = g.current_user.id
        
        # Check cache first
        cache_key = f'annotator_dashboard_stats_{user_id}'
        cached_data = redis_service.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get user's annotations
        user_annotations = Annotation.query.filter_by(labeler_id=user_id).all()
        
        # Calculate statistics
        stats = {
            'overview': {
                'total_annotations': len(user_annotations),
                'completed_annotations': len([a for a in user_annotations if a.status == 'completed']),
                'pending_annotations': len([a for a in user_annotations if a.status == 'pending']),
                'in_progress_annotations': len([a for a in user_annotations if a.status == 'in_progress']),
                'average_quality_score': g.current_user.average_quality_score or 0,
                'average_speed_score': g.current_user.average_speed_score or 0
            },
            'performance': {
                'annotations_today': len([a for a in user_annotations if a.created_at.date() == datetime.utcnow().date()]),
                'annotations_this_week': len([a for a in user_annotations if a.created_at >= datetime.utcnow() - timedelta(days=7)]),
                'annotations_this_month': len([a for a in user_annotations if a.created_at >= datetime.utcnow() - timedelta(days=30)])
            }
        }
        
        # Get assigned tasks (pending annotations)
        assigned_tasks = Annotation.query.filter_by(
            labeler_id=user_id,
            status='pending'
        ).join(Dataset).join(Project).limit(20).all()
        
        tasks_data = []
        for annotation in assigned_tasks:
            task_data = {
                'annotation_id': annotation.id,
                'project_name': annotation.dataset.project.name,
                'dataset_name': annotation.dataset.name,
                'task_type': annotation.task_type,
                'priority': annotation.priority or 'medium',
                'due_date': annotation.due_date.isoformat() if annotation.due_date else None,
                'estimated_time': annotation.estimated_time_minutes,
                'created_at': annotation.created_at.isoformat()
            }
            tasks_data.append(task_data)
        
        stats['assigned_tasks'] = tasks_data
        
        # Get recent completed work
        recent_completed = Annotation.query.filter_by(
            labeler_id=user_id,
            status='completed'
        ).order_by(desc(Annotation.updated_at)).limit(10).all()
        
        completed_data = []
        for annotation in recent_completed:
            completed_data.append({
                'annotation_id': annotation.id,
                'project_name': annotation.dataset.project.name,
                'dataset_name': annotation.dataset.name,
                'task_type': annotation.task_type,
                'quality_score': annotation.quality_score,
                'completed_at': annotation.updated_at.isoformat(),
                'time_spent_minutes': annotation.time_spent_minutes
            })
        
        stats['recent_completed'] = completed_data
        
        # Cache for 2 minutes
        redis_service.set(cache_key, stats, expire=120)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch annotator dashboard: {str(e)}'}), 500

@dashboard_bp.route('/project-manager', methods=['GET'])
@token_required
def project_manager_dashboard():
    """Project manager dashboard with project oversight"""
    if g.current_user.role != UserRole.PROJECT_MANAGER:
        return jsonify({'error': 'Project manager access required'}), 403
    
    try:
        # Check cache first
        cache_key = f'pm_dashboard_stats_{g.current_user.id}'
        cached_data = redis_service.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get managed projects
        managed_projects = Project.query.filter_by(manager_id=g.current_user.id).all()
        project_ids = [p.id for p in managed_projects]
        
        # Calculate statistics
        stats = {
            'overview': {
                'total_projects': len(managed_projects),
                'active_projects': len([p for p in managed_projects if p.status == 'active']),
                'projects_in_review': len([p for p in managed_projects if p.status == 'review']),
                'completed_projects': len([p for p in managed_projects if p.status == 'completed']),
                'total_annotators': len(set(a.labeler_id for p in managed_projects for d in p.datasets for a in d.annotations if a.labeler_id))
            },
            'workload': {
                'annotations_pending': Annotation.query.join(Dataset).filter(
                    Dataset.project_id.in_(project_ids),
                    Annotation.status == 'pending'
                ).count() if project_ids else 0,
                'annotations_in_progress': Annotation.query.join(Dataset).filter(
                    Dataset.project_id.in_(project_ids),
                    Annotation.status == 'in_progress'
                ).count() if project_ids else 0,
                'annotations_completed': Annotation.query.join(Dataset).filter(
                    Dataset.project_id.in_(project_ids),
                    Annotation.status == 'completed'
                ).count() if project_ids else 0
            }
        }
        
        # Get project details with progress
        project_details = []
        for project in managed_projects:
            datasets = Dataset.query.filter_by(project_id=project.id).all()
            total_items = sum(dataset.item_count or 0 for dataset in datasets)
            completed_annotations = Annotation.query.join(Dataset).filter(
                Dataset.project_id == project.id,
                Annotation.status == 'completed'
            ).count()
            
            progress_percentage = (completed_annotations / total_items * 100) if total_items > 0 else 0
            
            # Get assigned annotators
            annotator_ids = set(a.labeler_id for d in datasets for a in d.annotations if a.labeler_id)
            annotators = User.query.filter(User.id.in_(annotator_ids)).all() if annotator_ids else []
            
            project_details.append({
                'project_id': project.id,
                'project_name': project.name,
                'client_name': project.organization.name if project.organization else 'Unknown',
                'status': project.status,
                'total_items': total_items,
                'completed_annotations': completed_annotations,
                'progress_percentage': round(progress_percentage, 2),
                'assigned_annotators': len(annotators),
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'created_at': project.created_at.isoformat()
            })
        
        stats['managed_projects'] = project_details
        
        # Get team performance
        if project_ids:
            team_performance = []
            annotator_stats = Annotation.query.join(Dataset).filter(
                Dataset.project_id.in_(project_ids),
                Annotation.labeler_id.isnot(None)
            ).all()
            
            # Group by annotator
            annotator_data = {}
            for annotation in annotator_stats:
                labeler_id = annotation.labeler_id
                if labeler_id not in annotator_data:
                    annotator_data[labeler_id] = {
                        'total': 0,
                        'completed': 0,
                        'quality_scores': [],
                        'user': annotation.labeler
                    }
                
                annotator_data[labeler_id]['total'] += 1
                if annotation.status == 'completed':
                    annotator_data[labeler_id]['completed'] += 1
                    if annotation.quality_score:
                        annotator_data[labeler_id]['quality_scores'].append(annotation.quality_score)
            
            for labeler_id, data in annotator_data.items():
                avg_quality = sum(data['quality_scores']) / len(data['quality_scores']) if data['quality_scores'] else 0
                completion_rate = (data['completed'] / data['total'] * 100) if data['total'] > 0 else 0
                
                team_performance.append({
                    'user_id': labeler_id,
                    'username': data['user'].username if data['user'] else 'Unknown',
                    'full_name': data['user'].full_name if data['user'] else 'Unknown',
                    'total_annotations': data['total'],
                    'completed_annotations': data['completed'],
                    'completion_rate': round(completion_rate, 2),
                    'average_quality_score': round(avg_quality, 2)
                })
            
            stats['team_performance'] = sorted(team_performance, key=lambda x: x['completed_annotations'], reverse=True)
        else:
            stats['team_performance'] = []
        
        # Cache for 3 minutes
        redis_service.set(cache_key, stats, expire=180)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch project manager dashboard: {str(e)}'}), 500

@dashboard_bp.route('/profile', methods=['GET'])
@token_required
def user_profile():
    """Get current user's profile information"""
    try:
        user_data = g.current_user.to_dict(include_sensitive=True)
        
        # Add role-specific information
        if g.current_user.role in [UserRole.LABELER, UserRole.REVIEWER]:
            # Add annotation statistics
            user_annotations = Annotation.query.filter_by(labeler_id=g.current_user.id).all()
            user_data['annotation_stats'] = {
                'total_annotations': len(user_annotations),
                'completed_annotations': len([a for a in user_annotations if a.status == 'completed']),
                'average_quality_score': g.current_user.average_quality_score or 0,
                'annotations_this_month': len([a for a in user_annotations if a.created_at >= datetime.utcnow() - timedelta(days=30)])
            }
        
        if g.current_user.role == UserRole.PROJECT_MANAGER:
            # Add project management statistics
            managed_projects = Project.query.filter_by(manager_id=g.current_user.id).all()
            user_data['management_stats'] = {
                'total_projects': len(managed_projects),
                'active_projects': len([p for p in managed_projects if p.status == 'active']),
                'completed_projects': len([p for p in managed_projects if p.status == 'completed'])
            }
        
        return jsonify(user_data)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch user profile: {str(e)}'}), 500

@dashboard_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update current user's profile"""
    try:
        data = request.get_json()
        user = g.current_user
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'phone', 'timezone', 'notification_preferences', 'ui_preferences']
        
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        
        from src.config import db
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        from src.config import db
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

