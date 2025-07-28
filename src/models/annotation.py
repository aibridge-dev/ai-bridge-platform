from src.models.user import db
from datetime import datetime
import enum

class AnnotationStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUIRED = "revision_required"

class AnnotationType(enum.Enum):
    CLASSIFICATION = "classification"
    BOUNDING_BOX = "bounding_box"
    POLYGON = "polygon"
    SEGMENTATION = "segmentation"
    KEYPOINT = "keypoint"
    TEXT_SPAN = "text_span"
    TRANSCRIPTION = "transcription"
    CUSTOM = "custom"

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    data_item_id = db.Column(db.Integer, db.ForeignKey('data_item.id'), nullable=False)
    labeler_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Annotation details
    annotation_type = db.Column(db.Enum(AnnotationType), nullable=False)
    annotation_data = db.Column(db.JSON, nullable=False)  # Flexible annotation storage
    confidence_score = db.Column(db.Float, nullable=True)  # AI-generated confidence (0-1)
    
    # Status and workflow
    status = db.Column(db.Enum(AnnotationStatus), default=AnnotationStatus.PENDING)
    priority = db.Column(db.Integer, default=1)  # 1=low, 2=medium, 3=high, 4=urgent
    
    # Quality metrics
    quality_score = db.Column(db.Float, nullable=True)  # Calculated quality score (0-1)
    consistency_score = db.Column(db.Float, nullable=True)  # Consistency with other annotations
    
    # Time tracking
    time_spent_seconds = db.Column(db.Integer, default=0)
    estimated_time_seconds = db.Column(db.Integer, nullable=True)
    
    # Feedback and notes
    labeler_notes = db.Column(db.Text, nullable=True)
    reviewer_notes = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    
    # Version control
    version = db.Column(db.Integer, default=1)
    parent_annotation_id = db.Column(db.Integer, db.ForeignKey('annotation.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Self-referential relationship for revisions
    revisions = db.relationship('Annotation', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    
    def __repr__(self):
        return f'<Annotation {self.id} for DataItem {self.data_item_id}>'
    
    @property
    def is_overdue(self):
        if not self.created_at or not self.estimated_time_seconds:
            return False
        estimated_completion = self.created_at + datetime.timedelta(seconds=self.estimated_time_seconds)
        return datetime.utcnow() > estimated_completion and self.status not in [AnnotationStatus.COMPLETED, AnnotationStatus.APPROVED]
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'data_item_id': self.data_item_id,
            'labeler_id': self.labeler_id,
            'reviewer_id': self.reviewer_id,
            'annotation_type': self.annotation_type.value if self.annotation_type else None,
            'annotation_data': self.annotation_data,
            'confidence_score': self.confidence_score,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'quality_score': self.quality_score,
            'consistency_score': self.consistency_score,
            'time_spent_seconds': self.time_spent_seconds,
            'estimated_time_seconds': self.estimated_time_seconds,
            'labeler_notes': self.labeler_notes,
            'reviewer_notes': self.reviewer_notes,
            'feedback': self.feedback,
            'version': self.version,
            'parent_annotation_id': self.parent_annotation_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'is_overdue': self.is_overdue
        }

