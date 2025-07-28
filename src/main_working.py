"""
Working Flask application for AI Bridge Data Labeling Platform
Fixed database initialization and authentication
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import datetime

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

# Import models after db initialization
from src.models.user import User, UserRole
from src.models.organization import Organization
from src.models.project import Project
from src.models.dataset import Dataset
from src.models.annotation import Annotation
from src.models.review import Review

# Create database tables
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
            
            db.session.commit()
            print("✅ Demo users created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Import and register blueprints
from src.routes.auth import auth_bp
from src.routes.projects import projects_bp
from src.routes.files import files_bp
from src.routes.dashboard import dashboard_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(projects_bp, url_prefix='/api/projects')
app.register_blueprint(files_bp, url_prefix='/api/files')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint with service status"""
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
    """Get platform statistics"""
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count() if Project.query.first() else 0,
            'total_datasets': Dataset.query.count() if Dataset.query.first() else 0,
            'total_annotations': Annotation.query.count() if Annotation.query.first() else 0,
            'active_users': User.query.filter_by(is_active=True).count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500

# API information endpoint
@app.route('/api/info')
def api_info():
    """Get API information and available endpoints"""
    endpoints = {
        'authentication': {
            'POST /api/auth/register': 'Register new user',
            'POST /api/auth/login': 'User login',
            'POST /api/auth/logout': 'User logout',
            'GET /api/auth/profile': 'Get user profile'
        },
        'projects': {
            'GET /api/projects': 'List user projects',
            'POST /api/projects': 'Create new project',
            'GET /api/projects/{id}': 'Get project details'
        },
        'dashboard': {
            'GET /api/dashboard/stats': 'Get dashboard statistics',
            'GET /api/dashboard/activity': 'Get recent activity'
        },
        'system': {
            'GET /api/health': 'Health check',
            'GET /api/stats': 'Platform statistics',
            'GET /api/info': 'API information'
        }
    }
    
    return jsonify({
        'service': 'AI Bridge Data Labeling Platform API',
        'version': '1.0.0',
        'endpoints': endpoints
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

