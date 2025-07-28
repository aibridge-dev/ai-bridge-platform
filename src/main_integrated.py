"""
AI Bridge Platform - Integrated Backend with Label Studio
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum
import json
from src.labelstudio_session_api import label_studio_session_api as label_studio_api

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'ai-bridge-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'integrated_app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'ai-bridge-jwt-secret-2025'

# Initialize extensions
CORS(app, 
     origins=["https://utfejjbt.manus.space", "http://localhost:5173"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Create database directory
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Define models
class UserRole(enum.Enum):
    ADMIN = "admin"
    CLIENT_USER = "client_user"
    LABELER = "labeler"

class ProjectStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LABELER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    labelstudio_user_id = db.Column(db.Integer, nullable=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    labelstudio_project_id = db.Column(db.Integer, nullable=True)
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    
    # Relationships
    client = db.relationship('User', backref='projects')

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    file_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='datasets')

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check Label Studio connection
    ls_status = label_studio_api.health_check()
    
    return jsonify({
        'status': 'healthy',
        'service': 'AI Bridge Data Labeling Platform',
        'version': '1.0.0',
        'database': 'connected',
        'labelstudio': 'connected' if ls_status else 'disconnected',
        'users_count': User.query.count(),
        'projects_count': Project.query.count()
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Create access token
            access_token = create_access_token(identity=str(user.id))
            
            return jsonify({
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role.value,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Base stats
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count(),
            'total_datasets': Dataset.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'active_projects': Project.query.filter_by(status=ProjectStatus.ACTIVE).count()
        }
        
        # Role-specific stats
        if user.role == UserRole.CLIENT_USER:
            user_projects = Project.query.filter_by(client_id=user.id).all()
            stats.update({
                'user_projects': len(user_projects),
                'user_datasets': sum(len(p.datasets) for p in user_projects),
                'total_annotations': sum(p.completed_tasks for p in user_projects)
            })
        elif user.role == UserRole.ADMIN:
            stats.update({
                'total_annotations': sum(p.completed_tasks for p in Project.query.all())
            })
        else:  # LABELER
            stats.update({
                'total_annotations': 150,  # Mock data for now
                'tasks_completed_today': 47,
                'accuracy_score': 98.3
            })
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """Get projects for current user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role == UserRole.CLIENT_USER:
            projects = Project.query.filter_by(client_id=user.id).all()
        else:
            projects = Project.query.all()
        
        projects_data = []
        for project in projects:
            projects_data.append({
                'id': project.id,
                'title': project.title,
                'description': project.description,
                'status': project.status.value,
                'total_tasks': project.total_tasks,
                'completed_tasks': project.completed_tasks,
                'progress': (project.completed_tasks / project.total_tasks * 100) if project.total_tasks > 0 else 0,
                'created_at': project.created_at.isoformat(),
                'client_name': f"{project.client.first_name} {project.client.last_name}".strip()
            })
        
        return jsonify(projects_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        
        if not title:
            return jsonify({'error': 'Project title is required'}), 400
        
        # Create project in our database
        project = Project(
            title=title,
            description=description,
            client_id=user.id,
            status=ProjectStatus.DRAFT
        )
        db.session.add(project)
        db.session.flush()  # Get the ID
        
        # Create corresponding project in Label Studio
        ls_project = label_studio_api.create_project(
            title=f"AI Bridge - {title}",
            description=description
        )
        
        if ls_project:
            project.labelstudio_project_id = ls_project['id']
        
        db.session.commit()
        
        return jsonify({
            'id': project.id,
            'title': project.title,
            'description': project.description,
            'status': project.status.value,
            'labelstudio_project_id': project.labelstudio_project_id,
            'created_at': project.created_at.isoformat()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/upload', methods=['POST'])
@jwt_required()
def upload_project_data(project_id):
    """Upload data to a project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check permissions
        if user.role == UserRole.CLIENT_USER and project.client_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        tasks = data.get('tasks', [])
        
        if not tasks:
            return jsonify({'error': 'No tasks provided'}), 400
        
        # Import tasks to Label Studio
        if project.labelstudio_project_id:
            success = label_studio_api.import_tasks(project.labelstudio_project_id, tasks)
            
            if success:
                # Update project stats
                project.total_tasks += len(tasks)
                project.status = ProjectStatus.ACTIVE
                db.session.commit()
                
                return jsonify({
                    'message': f'Successfully uploaded {len(tasks)} tasks',
                    'project_id': project.id,
                    'total_tasks': project.total_tasks
                })
            else:
                return jsonify({'error': 'Failed to upload tasks to Label Studio'}), 500
        else:
            return jsonify({'error': 'Project not properly configured with Label Studio'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/stats', methods=['GET'])
@jwt_required()
def get_project_stats(project_id):
    """Get detailed project statistics"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get stats from Label Studio
        if project.labelstudio_project_id:
            ls_stats = label_studio_api.get_project_stats(project.labelstudio_project_id)
            
            # Update our database with latest stats
            if ls_stats:
                project.total_tasks = ls_stats.get('total_tasks', project.total_tasks)
                project.completed_tasks = ls_stats.get('completed_tasks', project.completed_tasks)
                db.session.commit()
        
        return jsonify({
            'id': project.id,
            'title': project.title,
            'status': project.status.value,
            'total_tasks': project.total_tasks,
            'completed_tasks': project.completed_tasks,
            'progress': (project.completed_tasks / project.total_tasks * 100) if project.total_tasks > 0 else 0,
            'labelstudio_url': f"http://localhost:8080/projects/{project.labelstudio_project_id}" if project.labelstudio_project_id else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database and create test data
def init_db():
    """Initialize database with test data"""
    with app.app_context():
        db.create_all()
        
        # Create test users if they don't exist
        if User.query.count() == 0:
            users = [
                {
                    'username': 'admin',
                    'email': 'admin@aibridge.com',
                    'password': 'admin123',
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'role': UserRole.ADMIN
                },
                {
                    'username': 'client',
                    'email': 'client@example.com',
                    'password': 'client123',
                    'first_name': 'Client',
                    'last_name': 'User',
                    'role': UserRole.CLIENT_USER
                },
                {
                    'username': 'annotator',
                    'email': 'annotator@example.com',
                    'password': 'annotator123',
                    'first_name': 'Annotator',
                    'last_name': 'User',
                    'role': UserRole.LABELER
                }
            ]
            
            for user_data in users:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role=user_data['role']
                )
                db.session.add(user)
            
            db.session.commit()
            print("Test users created successfully")

if __name__ == '__main__':
    init_db()
    print("Starting AI Bridge Platform with Label Studio integration...")
    print("Backend: http://localhost:5000")
    print("Label Studio: http://localhost:8080")
    app.run(host='0.0.0.0', port=5000, debug=True)

