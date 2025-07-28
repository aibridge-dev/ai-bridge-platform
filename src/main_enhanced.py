"""
AI Bridge Data Labeling Platform - Enhanced Flask Application
"""
import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from src.config import get_config
from src.services.redis_service import redis_service

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.config.from_object(config)

# Initialize CORS
CORS(app, origins=app.config['CORS_ORIGINS'])

# Initialize database
from src.models.user import db
db.init_app(app)

# Import all models to ensure they're registered
from src.models.organization import Organization
from src.models.project import Project
from src.models.dataset import Dataset, DataItem
from src.models.annotation import Annotation
from src.models.review import Review, QualityMetric

# Create database directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Initialize services
from src.services.s3_service import s3_service

# Import and register blueprints
from src.routes.auth import auth_bp
from src.routes.projects import projects_bp
from src.routes.files import files_bp
from src.routes.labelstudio_enhanced import labelstudio_bp
from src.routes.dashboard    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(labelstudio_bp, url_prefix='/api/labelstudio')
    
    # Import and register payments blueprint
    from src.routes.payments import payments_bp
    app.register_blueprint(payments_bp, url_prefix='/api/payments')# Health check endpoint
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
        s3_connected = s3_service and s3_service.test_connection()
        health_status['services']['s3'] = 'connected' if s3_connected else 'disconnected'
    except:
        health_status['services']['s3'] = 'disconnected'
    
    # Check if any critical services are down
    critical_services = ['database']  # S3 is important but not critical for basic health
    if any(health_status['services'].get(service) == 'disconnected' for service in critical_services):
        health_status['status'] = 'degraded'
        return jsonify(health_status), 503
    
    return jsonify(health_status)

@app.route('/api/info')
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'AI Bridge Data Labeling Platform API',
        'version': '1.0.0',
        'description': 'Professional data labeling and annotation platform',
        'endpoints': {
            'health': '/api/health',
            'auth': {
                'register': '/api/auth/register',
                'login': '/api/auth/login',
                'logout': '/api/auth/logout',
                'refresh-token': '/api/auth/refresh-token',
                'me': '/api/auth/me',
                'change-password': '/api/auth/change-password'
            },
            'projects': {
                'list': '/api/projects/',
                'create': '/api/projects/',
                'get': '/api/projects/{id}',
                'update': '/api/projects/{id}',
                'delete': '/api/projects/{id}',
                'stats': '/api/projects/{id}/stats'
            },
            'files': {
                'upload': '/api/files/upload',
                'datasets': '/api/files/datasets',
                'dataset': '/api/files/datasets/{id}',
                'items': '/api/files/datasets/{id}/items',
                'download': '/api/files/items/{id}/download'
            },
            'labelstudio': {
                'status': '/api/labelstudio/status',
                'create-project': '/api/labelstudio/projects/{id}/labelstudio',
                'sync-data': '/api/labelstudio/projects/{id}/labelstudio/sync',
                'get-tasks': '/api/labelstudio/projects/{id}/labelstudio/tasks',
                'get-annotations': '/api/labelstudio/projects/{id}/labelstudio/annotations',
                'export-annotations': '/api/labelstudio/projects/{id}/labelstudio/annotations/export',
                'get-progress': '/api/labelstudio/projects/{id}/labelstudio/progress',
                'get-url': '/api/labelstudio/projects/{id}/labelstudio/url',
                'templates': '/api/labelstudio/templates'
            }
        }
    })

@app.route('/api/stats')
def platform_stats():
    """Platform statistics endpoint"""
    try:
        # Get cached stats or calculate fresh
        cached_stats = redis_service.get('platform_stats')
        if cached_stats:
            return jsonify(cached_stats)
        
        # Calculate fresh stats
        from src.models.user import User
        from src.models.project import Project
        from src.models.dataset import Dataset
        from src.models.annotation import Annotation
        
        stats = {
            'total_users': User.query.count(),
            'total_projects': Project.query.count(),
            'total_datasets': Dataset.query.count(),
            'total_annotations': Annotation.query.count(),
            'active_projects': Project.query.filter_by(status='active').count(),
            'completed_projects': Project.query.filter_by(status='completed').count()
        }
        
        # Cache for 5 minutes
        redis_service.set('platform_stats', stats, expire=300)
        
        return jsonify(stats)
    except Exception as e:
        print(f"Stats endpoint error: {e}")
        # Return basic stats even if there's an error
        return jsonify({
            'total_users': 0,
            'total_projects': 0,
            'total_datasets': 0,
            'total_annotations': 0,
            'active_projects': 0,
            'completed_projects': 0,
            'note': 'Statistics calculated from empty database'
        }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def file_too_large(error):
    """Handle file too large errors"""
    return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413

# Request logging middleware
@app.before_request
def log_request_info():
    """Log request information for debugging"""
    if app.config['DEBUG']:
        print(f"Request: {request.method} {request.url}")

# Response headers middleware
@app.after_request
def after_request(response):
    """Add security headers to responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Initialize database tables
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

if __name__ == '__main__':
    # Development server configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting AI Bridge Platform on port {port}")
    print(f"📊 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🔄 Redis: {app.config['REDIS_URL']}")
    print(f"☁️  S3 Bucket: {app.config['S3_BUCKET']}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

