from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    ADMIN = "admin"  # AI Bridge admin
    CLIENT_ADMIN = "client_admin"  # Client organization admin
    PROJECT_MANAGER = "project_manager"  # AI Bridge project manager
    LABELER = "labeler"  # Annotation labeler
    REVIEWER = "reviewer"  # Quality reviewer
    CLIENT_USER = "client_user"  # Client organization user

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    timezone = db.Column(db.String(50), default='UTC')
    
    # Role and permissions
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LABELER)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Performance metrics (for labelers/reviewers)
    total_annotations = db.Column(db.Integer, default=0)
    average_quality_score = db.Column(db.Float, nullable=True)
    average_speed_score = db.Column(db.Float, nullable=True)
    
    # Preferences
    notification_preferences = db.Column(db.JSON, nullable=True)
    ui_preferences = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    organization = db.relationship('Organization', backref='users')
    managed_projects = db.relationship('Project', backref='manager', lazy='dynamic')
    annotations = db.relationship('Annotation', foreign_keys='Annotation.labeler_id', backref='labeler', lazy='dynamic')
    reviewed_annotations = db.relationship('Annotation', foreign_keys='Annotation.reviewer_id', backref='reviewer', lazy='dynamic')
    reviews = db.relationship('Review', backref='reviewer', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_ai_bridge_staff(self):
        return self.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.LABELER, UserRole.REVIEWER]

    @property
    def is_client_user(self):
        return self.role in [UserRole.CLIENT_ADMIN, UserRole.CLIENT_USER]

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self, secret_key, expires_in=3600):
        payload = {
            'user_id': self.id,
            'role': self.role.value if self.role else None,
            'organization_id': self.organization_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')

    @staticmethod
    def verify_token(token, secret_key):
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        permissions = {
            UserRole.ADMIN: ['all'],
            UserRole.PROJECT_MANAGER: ['manage_projects', 'assign_tasks', 'review_work', 'view_analytics'],
            UserRole.REVIEWER: ['review_work', 'approve_annotations', 'provide_feedback'],
            UserRole.LABELER: ['create_annotations', 'view_assigned_tasks'],
            UserRole.CLIENT_ADMIN: ['manage_organization', 'view_projects', 'upload_data'],
            UserRole.CLIENT_USER: ['view_projects', 'upload_data']
        }
        
        user_permissions = permissions.get(self.role, [])
        return 'all' in user_permissions or permission in user_permissions

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'timezone': self.timezone,
            'role': self.role.value if self.role else None,
            'organization_id': self.organization_id,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'total_annotations': self.total_annotations,
            'average_quality_score': self.average_quality_score,
            'average_speed_score': self.average_speed_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_ai_bridge_staff': self.is_ai_bridge_staff,
            'is_client_user': self.is_client_user
        }
        
        if include_sensitive:
            data.update({
                'notification_preferences': self.notification_preferences,
                'ui_preferences': self.ui_preferences
            })
        
        return data
