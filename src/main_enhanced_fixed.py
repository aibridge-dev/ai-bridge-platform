"""
Enhanced Flask application for AI Bridge Data Labeling Platform
Production-ready with PostgreSQL, Redis, Gunicorn, and Stripe integration
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from src.config import Config
from src.services.redis_service import redis_service
from src.services.s3_service import s3_service
from src.services.stripe_service import stripe_service

# Initialize Flask app
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Initialize extensions
CORS(app, origins="*")
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Initialize services
# Redis service is already initialized globally

# Import models to ensure they're registered
from src.models.user import User
from src.models.organization import Organization
from src.models.project import Project
from src.models.dataset import Dataset
from src.models.annotation import Annotation
from src.models.review import Review

# Create database tables
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Import and register blueprints
from src.routes.auth import auth_bp
from src.routes.projects import projects_bp
from src.routes.files import files_bp
from src.routes.labelstudio_enhanced import labelstudio_bp
from src.routes.dashboard import dashboard_bp
from src.routes.payments import payments_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(projects_bp, url_prefix='/api/projects')
app.register_blueprint(files_bp, url_prefix='/api/files')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(labelstudio_bp, url_prefix='/api/labelstudio')
app.register_blueprint(payments_bp, url_prefix='/api/payments')

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint with service status"""
    health_status = {
        'service': 'AI Bridge Data Labeling Platform',
        'status': 'healthy',
        'version': '1.0.0',
        'services': {
            'database': 'connected',
            'redis': 'connected' if redis_service.is_connected() else 'disconnected'
        }
    }
    
    # Test S3 connection safely
    try:
        if s3_service.test_connection():
            health_status['services']['s3'] = 'connected'
        else:
            health_status['services']['s3'] = 'disconnected'
    except Exception:
        health_status['services']['s3'] = 'error'
    
    # Test Stripe connection
    try:
        if stripe_service.test_connection():
            health_status['services']['stripe'] = 'connected'
        else:
            health_status['services']['stripe'] = 'disconnected'
    except Exception:
        health_status['services']['stripe'] = 'error'
    
    # Test Label Studio connection
    try:
        from src.services.labelstudio_enhanced import labelstudio_service
        if labelstudio_service.test_connection():
            health_status['services']['labelstudio'] = 'connected'
        else:
            health_status['services']['labelstudio'] = 'disconnected'
    except Exception:
        health_status['services']['labelstudio'] = 'error'
    
    return jsonify(health_status)

# Platform statistics endpoint
@app.route('/api/stats')
def platform_stats():
    """Get platform statistics"""
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count(),
            'total_datasets': Dataset.query.count(),
            'total_annotations': Annotation.query.count(),
            'active_projects': Project.query.filter_by(status='active').count(),
            'completed_projects': Project.query.filter_by(status='completed').count()
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
            'GET /api/projects/{id}': 'Get project details',
            'PUT /api/projects/{id}': 'Update project',
            'DELETE /api/projects/{id}': 'Delete project'
        },
        'files': {
            'POST /api/files/upload': 'Upload files to project',
            'GET /api/files/{id}': 'Get file details',
            'DELETE /api/files/{id}': 'Delete file'
        },
        'dashboard': {
            'GET /api/dashboard/stats': 'Get dashboard statistics',
            'GET /api/dashboard/activity': 'Get recent activity',
            'GET /api/dashboard/projects': 'Get user projects summary'
        },
        'labelstudio': {
            'GET /api/labelstudio/status': 'Check Label Studio connection',
            'GET /api/labelstudio/templates': 'Get annotation templates',
            'POST /api/labelstudio/projects/{id}/labelstudio': 'Create Label Studio project',
            'POST /api/labelstudio/projects/{id}/labelstudio/sync': 'Sync data to Label Studio',
            'GET /api/labelstudio/projects/{id}/labelstudio/progress': 'Get annotation progress'
        },
        'payments': {
            'GET /api/payments/pricing': 'Get pricing information',
            'POST /api/payments/calculate-cost': 'Calculate project cost',
            'POST /api/payments/create-payment-intent': 'Create payment intent',
            'POST /api/payments/create-subscription': 'Create subscription',
            'GET /api/payments/payment-history': 'Get payment history',
            'GET /api/payments/subscription-status': 'Get subscription status',
            'GET /api/payments/usage-stats': 'Get usage statistics'
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
        'endpoints': endpoints,
        'features': [
            'Role-based authentication',
            'Project management',
            'File upload to S3',
            'Label Studio integration',
            'Stripe payment processing',
            'Arabic/RTL support',
            'Real-time statistics',
            'Quality assurance workflows'
        ]
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Access forbidden'}), 403

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Authentication required'}), 401

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)

