
"""
AI Bridge Platform - Production Application
Optimized for Railway deployment with PostgreSQL and Redis
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import uuid

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from werkzeug.security import generate_password_hash, check_password_hash

# Import configuration and models
from src.config.production import ProductionConfig
from src.models.production_models import Base, User, Project, Dataset, Annotation, Organization, UserSession, ProjectAssignment, ActivityLog

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'production')
if config_name == 'production':
    app.config.from_object(ProductionConfig)
    ProductionConfig.init_app(app)
else:
    app.config.from_object(ProductionConfig)

# Initialize extensions
CORS(app, 
     origins=app.config.get('CORS_ORIGINS', ['*']),
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# Database setup
db = SQLAlchemy(app)
db.Model = Base

# JWT setup
jwt = JWTManager(app)

# Redis setup for rate limiting and caching
try:
    redis_client = redis.from_url(app.config['REDIS_URL'])
    redis_client.ping()
    app.logger.info("Redis connection established")
except Exception as e:
    app.logger.error(f"Redis connection failed: {e}")
    redis_client = None

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri=app.config.get('REDIS_URL')
)

# Database initialization
@app.before_first_request
def create_tables():
    """Create database tables if they don't exist"""
    try:
        db.create_all()
        app.logger.info("Database tables created successfully")
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(email='admin@aibridge.com').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@aibridge.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                is_active=True,
                is_verified=True,
                is_ai_bridge_staff=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            
            # Create sample client user
            client_user = User(
                username='client',
                email='client@example.com',
                first_name='Client',
                last_name='User',
                role='client_user',
                is_active=True,
                is_verified=True
            )
            client_user.set_password('client123')
            db.session.add(client_user)
            
            # Create sample labeler
            labeler_user = User(
                username='labeler',
                email='labeler@example.com',
                first_name='Labeler',
                last_name='User',
                role='labeler',
                is_active=True,
                is_verified=True
            )
            labeler_user.set_password('labeler123')
            db.session.add(labeler_user)
            
            db.session.commit()
            app.logger.info("Default users created successfully")
            
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")

# Request logging middleware
@app.before_request
def log_request_info():
    """Log request information for monitoring"""
    g.start_time = datetime.utcnow()
    app.logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log response information for monitoring"""
    if hasattr(g, 'start_time'):
        duration = datetime.utcnow() - g.start_time
        app.logger.info(f"Response: {response.status_code} in {duration.total_seconds():.3f}s")
    return response

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis connection
    redis_status = "healthy" if redis_client and redis_client.ping() else "unhealthy"
    
    return jsonify({
        "service": "AI Bridge Data Labeling Platform",
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status
        }
    })

# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """User authentication endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if not user or not user.check_password(password):
            app.logger.warning(f"Failed login attempt for email: {email}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": user.role,
                "organization_id": str(user.organization_id) if user.organization_id else None
            }
        )
        
        # Log successful login
        activity_log = ActivityLog(
            user_id=user.id,
            action="login",
            description="User logged in successfully",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(activity_log)
        db.session.commit()
        
        app.logger.info(f"Successful login for user: {email}")
        
        return jsonify({
            "message": "Login successful",
            "token": access_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_client_user": user.is_client_user,
                "is_ai_bridge_staff": user.is_ai_bridge_staff,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "last_activity": user.last_activity.isoformat() if user.last_activity else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "total_annotations": user.total_annotations,
                "average_quality_score": float(user.average_quality_score) if user.average_quality_score else None,
                "average_speed_score": float(user.average_speed_score) if user.average_speed_score else None,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "timezone": user.timezone,
                "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None
            }
        })
        
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint"""
    try:
        user_id = get_jwt_identity()
        
        # Log logout activity
        activity_log = ActivityLog(
            user_id=uuid.UUID(user_id),
            action="logout",
            description="User logged out",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(activity_log)
        db.session.commit()
        
        return jsonify({"message": "Logout successful"})
        
    except Exception as e:
        app.logger.error(f"Logout error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Dashboard endpoints
@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(uuid.UUID(user_id))
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update last activity
        user.last_activity = datetime.utcnow()
        db.session.commit()
        
        # Get statistics based on user role
        if user.role == 'admin':
            total_users = User.query.filter_by(is_active=True).count()
            total_projects = Project.query.count()
            total_datasets = Dataset.query.count()
            total_annotations = Annotation.query.count()
            active_projects = Project.query.filter_by(status='active').count()
        elif user.role == 'client_user':
            total_users = User.query.filter_by(is_active=True).count()
            total_projects = Project.query.filter_by(client_id=user.id).count()
            total_datasets = Dataset.query.join(Project).filter(Project.client_id == user.id).count()
            total_annotations = Annotation.query.join(Project).filter(Project.client_id == user.id).count()
            active_projects = Project.query.filter_by(client_id=user.id, status='active').count()
        else:  # labeler
            total_users = User.query.filter_by(is_active=True).count()
            total_projects = Project.query.join(ProjectAssignment).filter(ProjectAssignment.user_id == user.id).count()
            total_datasets = Dataset.query.join(Project).join(ProjectAssignment).filter(ProjectAssignment.user_id == user.id).count()
            total_annotations = Annotation.query.filter_by(labeler_id=user.id).count()
            active_projects = Project.query.join(ProjectAssignment).filter(ProjectAssignment.user_id == user.id, Project.status == 'active').count()
        
        return jsonify({
            "total_users": total_users,
            "total_projects": total_projects,
            "total_datasets": total_datasets,
            "total_annotations": total_annotations,
            "active_users": total_users,  # Simplified for now
            "active_projects": active_projects,
            "completed_annotations": total_annotations  # Simplified for now
        })
        
    except Exception as e:
        app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

# JWT error handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token has expired"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": "Invalid token"}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"error": "Authorization token is required"}), 401
@app.route("/api/health", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # This should not be used in production (Gunicorn handles this)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)


