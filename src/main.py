import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp

# Import all models to ensure they're registered with SQLAlchemy
from src.models.organization import Organization
from src.models.project import Project
from src.models.dataset import Dataset, DataItem
from src.models.annotation import Annotation
from src.models.review import Review, QualityMetric

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ai-bridge-data-labeling-platform-secret-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file upload

# Environment variables
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', 'AKIAQKPPQX254CXDLLY5')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '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')
app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-2')
app.config['S3_BUCKET'] = os.getenv('S3_BUCKET', 'signaldrop-file-storage')

# Label Studio configuration
app.config['LABEL_STUDIO_URL'] = os.getenv('LABEL_STUDIO_URL', 'http://localhost:8080')
app.config['LABEL_STUDIO_API_TOKEN'] = os.getenv('LABEL_STUDIO_API_TOKEN', 'm1xPV8A3pDJK6XB5StE6wcVODLqnzHvs')

# Set environment variables for services
os.environ['AWS_ACCESS_KEY_ID'] = app.config['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = app.config['AWS_SECRET_ACCESS_KEY']
os.environ['AWS_REGION'] = app.config['AWS_REGION']
os.environ['S3_BUCKET'] = app.config['S3_BUCKET']
os.environ['LABEL_STUDIO_URL'] = app.config['LABEL_STUDIO_URL']
os.environ['LABEL_STUDIO_API_TOKEN'] = app.config['LABEL_STUDIO_API_TOKEN']

# Enable CORS for all routes
CORS(app, origins=['*'], supports_credentials=True)

# Initialize database
db.init_app(app)

# Create database directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')

# Import and register new blueprints
from src.routes.auth import auth_bp
from src.routes.projects import projects_bp
from src.routes.files import files_bp
# from src.routes.labelstudio import labelstudio_bp  # Disabled for deployment

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(projects_bp, url_prefix='/api/projects')
app.register_blueprint(files_bp, url_prefix='/api/files')
# app.register_blueprint(labelstudio_bp, url_prefix='/api/labelstudio')  # Disabled for deployment

# Health check endpoint
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'AI Bridge Data Labeling Platform',
        'version': '1.0.0'
    })

# API info endpoint
@app.route('/api/info')
def api_info():
    return jsonify({
        'name': 'AI Bridge Data Labeling Platform API',
        'version': '1.0.0',
        'description': 'Professional data labeling and annotation platform',
        'endpoints': {
            'health': '/api/health',
            'users': '/api/users',
            'auth': {
                'register': '/api/auth/register',
                'login': '/api/auth/login',
                'me': '/api/auth/me',
                'change-password': '/api/auth/change-password',
                'refresh-token': '/api/auth/refresh-token',
                'logout': '/api/auth/logout'
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
                'datasets': '/api/files/datasets',
                'upload': '/api/files/upload',
                'dataset': '/api/files/datasets/{id}',
                'items': '/api/files/datasets/{id}/items',
                'download': '/api/files/items/{id}/download'
            }
        }
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# Initialize database tables
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
