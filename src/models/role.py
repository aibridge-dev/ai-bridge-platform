"""
Role-based access control model for AI Bridge Platform
"""
from src.config import db
from datetime import datetime
from enum import Enum

class RoleType(Enum):
    """User role types"""
    ADMIN = "admin"
    CLIENT = "client"
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"

class Role(db.Model):
    """Role model for user access control"""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON)  # Store permissions as JSON
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='role_obj', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def to_dict(self):
        """Convert role to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions or {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_default_permissions(role_type):
        """Get default permissions for a role type"""
        permissions = {
            RoleType.ADMIN.value: {
                'users': ['create', 'read', 'update', 'delete'],
                'projects': ['create', 'read', 'update', 'delete'],
                'datasets': ['create', 'read', 'update', 'delete'],
                'annotations': ['create', 'read', 'update', 'delete'],
                'reviews': ['create', 'read', 'update', 'delete'],
                'organizations': ['create', 'read', 'update', 'delete'],
                'system': ['manage', 'configure', 'monitor']
            },
            RoleType.CLIENT.value: {
                'projects': ['create', 'read', 'update'],
                'datasets': ['create', 'read', 'update'],
                'annotations': ['read'],
                'reviews': ['read'],
                'billing': ['read', 'manage']
            },
            RoleType.ANNOTATOR.value: {
                'projects': ['read'],
                'datasets': ['read'],
                'annotations': ['create', 'read', 'update'],
                'tasks': ['read', 'complete']
            },
            RoleType.REVIEWER.value: {
                'projects': ['read'],
                'datasets': ['read'],
                'annotations': ['read', 'update'],
                'reviews': ['create', 'read', 'update'],
                'quality': ['monitor', 'report']
            }
        }
        return permissions.get(role_type, {})
    
    @classmethod
    def create_default_roles(cls):
        """Create default system roles"""
        default_roles = [
            {
                'name': RoleType.ADMIN.value,
                'description': 'System administrator with full access',
                'permissions': cls.get_default_permissions(RoleType.ADMIN.value)
            },
            {
                'name': RoleType.CLIENT.value,
                'description': 'Client who creates projects and manages datasets',
                'permissions': cls.get_default_permissions(RoleType.CLIENT.value)
            },
            {
                'name': RoleType.ANNOTATOR.value,
                'description': 'Annotator who labels data and completes tasks',
                'permissions': cls.get_default_permissions(RoleType.ANNOTATOR.value)
            },
            {
                'name': RoleType.REVIEWER.value,
                'description': 'Reviewer who validates and approves annotations',
                'permissions': cls.get_default_permissions(RoleType.REVIEWER.value)
            }
        ]
        
        for role_data in default_roles:
            existing_role = cls.query.filter_by(name=role_data['name']).first()
            if not existing_role:
                role = cls(**role_data)
                db.session.add(role)
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default roles: {e}")
            return False

class UserRole(db.Model):
    """Association table for user-role relationships"""
    __tablename__ = 'user_role'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    is_active = db.Column(db.Boolean, default=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='user_roles')
    role = db.relationship('Role', backref='user_assignments')
    organization = db.relationship('Organization', backref='role_assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'
    
    def to_dict(self):
        """Convert user role to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'organization_id': self.organization_id,
            'is_active': self.is_active,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'role': self.role.to_dict() if self.role else None,
            'organization': self.organization.to_dict() if self.organization else None
        }

def has_permission(user, resource, action, organization_id=None):
    """Check if user has permission for a specific action on a resource"""
    if not user:
        return False
    
    # Get user's active roles
    user_roles = UserRole.query.filter_by(
        user_id=user.id,
        is_active=True
    ).all()
    
    # If organization_id is specified, filter by organization
    if organization_id:
        user_roles = [ur for ur in user_roles if ur.organization_id == organization_id]
    
    # Check permissions in each role
    for user_role in user_roles:
        role = user_role.role
        if not role or not role.is_active:
            continue
        
        permissions = role.permissions or {}
        resource_permissions = permissions.get(resource, [])
        
        if action in resource_permissions:
            return True
    
    return False

def require_permission(resource, action, organization_id=None):
    """Decorator to require specific permission for a route"""
    def decorator(f):
        from functools import wraps
        from flask import g, jsonify
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not has_permission(g.current_user, resource, action, organization_id):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

