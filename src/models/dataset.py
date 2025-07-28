from src.models.user import db
from datetime import datetime
import enum

class DatasetStatus(enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class FileType(enum.Enum):
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CSV = "csv"
    JSON = "json"

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Project relationship
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # File information
    file_type = db.Column(db.Enum(FileType), nullable=False)
    file_count = db.Column(db.Integer, default=0)
    total_size_bytes = db.Column(db.BigInteger, default=0)
    
    # Storage information
    storage_path = db.Column(db.String(500), nullable=True)  # S3 path or local path
    original_filename = db.Column(db.String(255), nullable=True)
    
    # Processing status
    status = db.Column(db.Enum(DatasetStatus), default=DatasetStatus.UPLOADING)
    processing_log = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Metadata
    file_metadata = db.Column(db.JSON, nullable=True)  # Flexible metadata storage
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    data_items = db.relationship('DataItem', backref='dataset', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Dataset {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_id': self.project_id,
            'file_type': self.file_type.value if self.file_type else None,
            'file_count': self.file_count,
            'total_size_bytes': self.total_size_bytes,
            'storage_path': self.storage_path,
            'original_filename': self.original_filename,
            'status': self.status.value if self.status else None,
            'processing_log': self.processing_log,
            'error_message': self.error_message,
            'metadata': self.file_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'item_count': self.data_items.count()
        }

class DataItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Dataset relationship
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # S3 path or local path
    file_size_bytes = db.Column(db.Integer, nullable=True)
    file_hash = db.Column(db.String(64), nullable=True)  # SHA-256 hash for deduplication
    
    # Content information
    content_type = db.Column(db.String(100), nullable=True)  # MIME type
    dimensions = db.Column(db.String(50), nullable=True)  # For images/videos: "1920x1080"
    duration = db.Column(db.Float, nullable=True)  # For audio/video: duration in seconds
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False)
    processing_error = db.Column(db.Text, nullable=True)
    
    # Metadata
    item_metadata = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    annotations = db.relationship('Annotation', backref='data_item', lazy='dynamic')
    
    def __repr__(self):
        return f'<DataItem {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'dataset_id': self.dataset_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'file_hash': self.file_hash,
            'content_type': self.content_type,
            'dimensions': self.dimensions,
            'duration': self.duration,
            'is_processed': self.is_processed,
            'processing_error': self.processing_error,
            'metadata': self.item_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'annotation_count': self.annotations.count()
        }

