from src.models.user import db
from datetime import datetime
import enum

class ProjectStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ProjectType(enum.Enum):
    IMAGE_CLASSIFICATION = "image_classification"
    OBJECT_DETECTION = "object_detection"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    TEXT_CLASSIFICATION = "text_classification"
    NAMED_ENTITY_RECOGNITION = "named_entity_recognition"
    AUDIO_CLASSIFICATION = "audio_classification"
    VIDEO_ANNOTATION = "video_annotation"
    CUSTOM = "custom"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_type = db.Column(db.Enum(ProjectType), nullable=False)
    status = db.Column(db.Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    # Organization relationship
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    
    # Project manager (AI Bridge team member)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Project configuration
    annotation_schema = db.Column(db.JSON, nullable=True)  # Flexible schema definition
    quality_threshold = db.Column(db.Float, default=0.95)  # Quality requirement (0-1)
    instructions = db.Column(db.Text, nullable=True)  # Annotation instructions
    
    # Timeline and pricing
    deadline = db.Column(db.DateTime, nullable=True)
    estimated_hours = db.Column(db.Integer, nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    fixed_price = db.Column(db.Float, nullable=True)
    
    # Progress tracking
    total_items = db.Column(db.Integer, default=0)
    completed_items = db.Column(db.Integer, default=0)
    approved_items = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    datasets = db.relationship('Dataset', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    annotations = db.relationship('Annotation', backref='project', lazy='dynamic')
    reviews = db.relationship('Review', backref='project', lazy='dynamic')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def progress_percentage(self):
        if self.total_items == 0:
            return 0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def approval_percentage(self):
        if self.completed_items == 0:
            return 0
        return (self.approved_items / self.completed_items) * 100
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_type': self.project_type.value if self.project_type else None,
            'status': self.status.value if self.status else None,
            'organization_id': self.organization_id,
            'manager_id': self.manager_id,
            'annotation_schema': self.annotation_schema,
            'quality_threshold': self.quality_threshold,
            'instructions': self.instructions,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'estimated_hours': self.estimated_hours,
            'hourly_rate': self.hourly_rate,
            'fixed_price': self.fixed_price,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'approved_items': self.approved_items,
            'progress_percentage': self.progress_percentage,
            'approval_percentage': self.approval_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

