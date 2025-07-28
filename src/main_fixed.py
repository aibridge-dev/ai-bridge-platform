"""
Fixed Flask application for AI Bridge Data Labeling Platform
Proper database initialization and authentication
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import datetime
from werkzeug.security import generate_password_hash
import enum

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ai-bridge-data-labeling-platform-secret-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'ai-bridge-jwt-secret-key-2025')

# AWS Configuration
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', 'AKIAQKPPQX254CXDLLY5')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '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')
app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-2')
app.config['S3_BUCKET'] = os.getenv('S3_BUCKET', 'signaldrop-file-storage')

# Initialize extensions
CORS(app, origins="*")
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Create database directory
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Define models directly in main file to avoid import issues
class UserRole(enum.Enum):
    ADMIN = "admin"
    CLIENT_ADMIN = "client_admin"
    PROJECT_MANAGER = "project_manager"
    LABELER = "labeler"
    REVIEWER = "reviewer"
    CLIENT_USER = "client_user"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LABELER)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value if self.role else None,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Authentication routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Generate token (simplified)
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=user.id)

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400

        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role=UserRole.CLIENT_USER
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()

        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

# Dashboard routes
@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count(),
            'total_datasets': Dataset.query.count(),
            'total_annotations': Annotation.query.count(),
            'active_projects': Project.query.filter_by(status='active').count(),
            'active_users': User.query.filter_by(is_active=True).count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500

@app.route('/api/dashboard/activity', methods=['GET'])
def dashboard_activity():
    try:
        # Mock activity data for now
        activities = [
            {
                'id': 1,
                'type': 'project_created',
                'description': 'New project "Image Classification" created',
                'timestamp': datetime.utcnow().isoformat(),
                'user': 'admin'
            },
            {
                'id': 2,
                'type': 'dataset_uploaded',
                'description': 'Dataset "Training Images" uploaded',
                'timestamp': datetime.utcnow().isoformat(),
                'user': 'client'
            }
        ]
        return jsonify(activities)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch activity: {str(e)}'}), 500

# Health check endpoint
@app.route('/api/health')
def health_check():
    return jsonify({
        'service': 'AI Bridge Data Labeling Platform',
        'status': 'healthy',
        'version': '1.0.0',
        'database': 'connected',
        'users_count': User.query.count()
    })

# Platform statistics endpoint
@app.route('/api/stats')
def platform_stats():
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count(),
            'total_datasets': Dataset.query.count(),
            'total_annotations': Annotation.query.count(),
            'active_users': User.query.filter_by(is_active=True).count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Initialize database and create demo data
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Create demo users if they don't exist
        if not User.query.filter_by(email='admin@aibridge.com').first():
            admin_user = User(
                username='admin',
                email='admin@aibridge.com',
                first_name='Admin',
                last_name='User',
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            
            client_user = User(
                username='client',
                email='client@example.com',
                first_name='Client',
                last_name='User',
                role=UserRole.CLIENT_USER,
                is_active=True,
                is_verified=True
            )
            client_user.set_password('client123')
            db.session.add(client_user)
            
            annotator_user = User(
                username='annotator',
                email='annotator@example.com',
                first_name='Annotator',
                last_name='User',
                role=UserRole.LABELER,
                is_active=True,
                is_verified=True
            )
            annotator_user.set_password('annotator123')
            db.session.add(annotator_user)
            
            # Create demo projects
            project1 = Project(
                name='Image Classification Project',
                description='Classify images into different categories',
                status='active'
            )
            db.session.add(project1)
            
            project2 = Project(
                name='Text Annotation Project',
                description='Annotate text for sentiment analysis',
                status='active'
            )
            db.session.add(project2)
            
            db.session.commit()
            print("✅ Demo users and projects created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

