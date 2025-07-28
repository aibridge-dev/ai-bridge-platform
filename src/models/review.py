from src.models.user import db
from datetime import datetime
import enum

class ReviewStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class ReviewDecision(enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUIRED = "revision_required"
    ESCALATED = "escalated"

class ReviewType(enum.Enum):
    ANNOTATION_REVIEW = "annotation_review"
    PROJECT_REVIEW = "project_review"
    QUALITY_AUDIT = "quality_audit"
    FINAL_DELIVERY = "final_delivery"

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    annotation_id = db.Column(db.Integer, db.ForeignKey('annotation.id'), nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Review details
    review_type = db.Column(db.Enum(ReviewType), nullable=False)
    status = db.Column(db.Enum(ReviewStatus), default=ReviewStatus.PENDING)
    decision = db.Column(db.Enum(ReviewDecision), nullable=True)
    
    # Quality assessment
    quality_score = db.Column(db.Float, nullable=True)  # Overall quality score (0-1)
    accuracy_score = db.Column(db.Float, nullable=True)  # Accuracy assessment (0-1)
    completeness_score = db.Column(db.Float, nullable=True)  # Completeness assessment (0-1)
    consistency_score = db.Column(db.Float, nullable=True)  # Consistency assessment (0-1)
    
    # Feedback
    comments = db.Column(db.Text, nullable=True)
    feedback_for_labeler = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    
    # Issues and improvements
    issues_found = db.Column(db.JSON, nullable=True)  # List of specific issues
    suggested_improvements = db.Column(db.Text, nullable=True)
    
    # Time tracking
    review_time_seconds = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Review {self.id} for Project {self.project_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'annotation_id': self.annotation_id,
            'reviewer_id': self.reviewer_id,
            'review_type': self.review_type.value if self.review_type else None,
            'status': self.status.value if self.status else None,
            'decision': self.decision.value if self.decision else None,
            'quality_score': self.quality_score,
            'accuracy_score': self.accuracy_score,
            'completeness_score': self.completeness_score,
            'consistency_score': self.consistency_score,
            'comments': self.comments,
            'feedback_for_labeler': self.feedback_for_labeler,
            'internal_notes': self.internal_notes,
            'issues_found': self.issues_found,
            'suggested_improvements': self.suggested_improvements,
            'review_time_seconds': self.review_time_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class QualityMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    labeler_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Metric details
    metric_name = db.Column(db.String(100), nullable=False)  # e.g., "accuracy", "speed", "consistency"
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(50), nullable=True)  # e.g., "percentage", "seconds", "count"
    
    # Context
    measurement_period_start = db.Column(db.DateTime, nullable=True)
    measurement_period_end = db.Column(db.DateTime, nullable=True)
    sample_size = db.Column(db.Integer, nullable=True)
    
    # Metadata
    metric_metadata = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<QualityMetric {self.metric_name}: {self.metric_value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'labeler_id': self.labeler_id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'measurement_period_start': self.measurement_period_start.isoformat() if self.measurement_period_start else None,
            'measurement_period_end': self.measurement_period_end.isoformat() if self.measurement_period_end else None,
            'sample_size': self.sample_size,
            'metadata': self.metric_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

