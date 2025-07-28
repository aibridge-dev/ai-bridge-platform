"""
AI Bridge Platform - Production Models
SQLAlchemy models designed for PostgreSQL with proper relationships and indexing
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Decimal, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class Organization(Base):
    __tablename__ = 'organizations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    website = Column(String(255))
    contact_email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    role = Column(String(20), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))
    timezone = Column(String(50), default='UTC')
    total_annotations = Column(Integer, default=0)
    average_quality_score = Column(Decimal(5,2))
    average_speed_score = Column(Decimal(5,2))
    is_ai_bridge_staff = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'client_user', 'labeler')", name='check_user_role'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        Index('idx_users_organization', 'organization_id'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_last_activity', 'last_activity'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    client_projects = relationship("Project", foreign_keys="Project.client_id", back_populates="client")
    annotations = relationship("Annotation", back_populates="labeler")
    sessions = relationship("UserSession", back_populates="user")
    assignments = relationship("ProjectAssignment", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def is_client_user(self):
        return self.role == 'client_user'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    client_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    status = Column(String(20), nullable=False, default='draft')
    project_type = Column(String(50), nullable=False)
    annotation_guidelines = Column(Text)
    quality_threshold = Column(Decimal(5,2), default=95.0)
    target_annotations = Column(Integer)
    completed_annotations = Column(Integer, default=0)
    estimated_completion_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))
    budget_amount = Column(Decimal(10,2))
    cost_per_annotation = Column(Decimal(6,3))
    labelstudio_project_id = Column(Integer)
    priority = Column(Integer, default=1)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'completed', 'paused', 'cancelled')", name='check_project_status'),
        Index('idx_projects_client', 'client_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_organization', 'organization_id'),
        Index('idx_projects_created', 'created_at'),
    )
    
    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="client_projects")
    organization = relationship("Organization", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project")
    annotations = relationship("Annotation", back_populates="project")
    assignments = relationship("ProjectAssignment", back_populates="project")
    activity_logs = relationship("ActivityLog", back_populates="project")

class Dataset(Base):
    __tablename__ = 'datasets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    s3_bucket = Column(String(100))
    s3_key = Column(String(500))
    upload_status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("upload_status IN ('pending', 'uploading', 'completed', 'failed')", name='check_upload_status'),
        Index('idx_datasets_project', 'project_id'),
        Index('idx_datasets_status', 'upload_status'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="datasets")
    annotations = relationship("Annotation", back_populates="dataset")

class Annotation(Base):
    __tablename__ = 'annotations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    labeler_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    labelstudio_task_id = Column(Integer)
    labelstudio_annotation_id = Column(Integer)
    annotation_data = Column(JSONB)
    quality_score = Column(Decimal(5,2))
    time_spent_seconds = Column(Integer)
    status = Column(String(20), default='pending')
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'rejected', 'approved')", name='check_annotation_status'),
        Index('idx_annotations_project', 'project_id'),
        Index('idx_annotations_labeler', 'labeler_id'),
        Index('idx_annotations_status', 'status'),
        Index('idx_annotations_created', 'created_at'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="annotations")
    dataset = relationship("Dataset", back_populates="annotations")
    labeler = relationship("User", foreign_keys=[labeler_id], back_populates="annotations")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_sessions_user', 'user_id'),
        Index('idx_sessions_token', 'session_token'),
        Index('idx_sessions_expires', 'expires_at'),
    )
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class ProjectAssignment(Base):
    __tablename__ = 'project_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_active = Column(Boolean, default=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('manager', 'labeler', 'reviewer')", name='check_assignment_role'),
        UniqueConstraint('project_id', 'user_id', 'role', name='unique_project_user_role'),
        Index('idx_assignments_project', 'project_id'),
        Index('idx_assignments_user', 'user_id'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="assignments")
    user = relationship("User", back_populates="assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='SET NULL'))
    action = Column(String(100), nullable=False)
    description = Column(Text)
    metadata = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_activity_user', 'user_id'),
        Index('idx_activity_project', 'project_id'),
        Index('idx_activity_created', 'created_at'),
    )
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    project = relationship("Project", back_populates="activity_logs")

