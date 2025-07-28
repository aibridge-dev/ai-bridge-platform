#!/usr/bin/env python3
"""
Simple working Flask backend for AI Bridge
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

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'ai-bridge-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'simple_app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'ai-bridge-jwt-secret-2025'

# Initialize extensions
CORS(app, origins="*")
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Create database directory
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Define models
class UserRole(enum.Enum):
    ADMIN = "admin"
    CLIENT_USER = "client_user"
    LABELER = "labeler"

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

# Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        print("=== LOGIN REQUEST ===")
        data = request.get_json()
        print(f"Request data: {data}")
        
        email = data.get('email')
        password = data.get('password')
        print(f"Email: {email}, Password: {'*' * len(password) if password else None}")

        if not email or not password:
            print("Missing email or password")
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()
        print(f"User found: {user}")
        
        if not user:
            print("User not found")
            return jsonify({'error': 'Invalid email or password'}), 401
            
        print(f"User active: {user.is_active}")
        password_valid = user.check_password(password)
        print(f"Password valid: {password_valid}")
        
        if not password_valid:
            print("Invalid password")
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            print("Account deactivated")
            return jsonify({'error': 'Account is deactivated'}), 401

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        print("Updated last login")

        # Generate token
        access_token = create_access_token(identity=str(user.id))
        print(f"Generated token: {access_token[:20]}...")

        response_data = {
            'access_token': access_token,
            'user': user.to_dict()
        }
        print(f"Response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        print(f"Login error: {e}")
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

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': 3,  # Mock data
            'total_datasets': 5,  # Mock data
            'total_annotations': 150,  # Mock data
            'active_projects': 2,  # Mock data
            'active_users': User.query.filter_by(is_active=True).count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500

@app.route('/api/dashboard/activity', methods=['GET'])
@jwt_required()
def dashboard_activity():
    try:
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

@app.route('/api/health')
def health_check():
    return jsonify({
        'service': 'AI Bridge Data Labeling Platform',
        'status': 'healthy',
        'version': '1.0.0',
        'database': 'connected',
        'users_count': User.query.count()
    })

@app.route('/api/stats')
def platform_stats():
    try:
        stats = {
            'total_users': User.query.count(),
            'total_projects': 3,
            'total_datasets': 5,
            'total_annotations': 150,
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
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            
            client_user = User(
                username='client',
                email='client@example.com',
                first_name='Client',
                last_name='User',
                role=UserRole.CLIENT_USER,
                is_active=True
            )
            client_user.set_password('client123')
            db.session.add(client_user)
            
            annotator_user = User(
                username='annotator',
                email='annotator@example.com',
                first_name='Annotator',
                last_name='User',
                role=UserRole.LABELER,
                is_active=True
            )
            annotator_user.set_password('annotator123')
            db.session.add(annotator_user)
            
            db.session.commit()
            print("✅ Demo users created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# Payment and Subscription Models
class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    features = db.Column(db.Text, nullable=True)
    max_projects = db.Column(db.Integer, default=5)
    max_annotations = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='active')
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Payment Routes
@app.route('/api/payments/plans', methods=['GET'])
def get_subscription_plans():
    try:
        plans = SubscriptionPlan.query.all()
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'price': plan.price,
                'features': plan.features.split(',') if plan.features else [],
                'max_projects': plan.max_projects,
                'max_annotations': plan.max_annotations
            })
        return jsonify(plans_data)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch plans: {str(e)}'}), 500

@app.route('/api/payments/create-subscription', methods=['POST'])
@jwt_required()
def create_subscription():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        plan_id = data.get('plan_id')
        
        if not plan_id:
            return jsonify({'error': 'Plan ID is required'}), 400
        
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Create subscription record
        subscription = UserSubscription(
            user_id=int(user_id),
            plan_id=plan_id,
            status='active',
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription created successfully',
            'subscription_id': subscription.id,
            'plan_name': plan.name,
            'status': subscription.status
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create subscription: {str(e)}'}), 500

@app.route('/api/payments/subscription-status', methods=['GET'])
@jwt_required()
def get_subscription_status():
    try:
        user_id = get_jwt_identity()
        subscription = UserSubscription.query.filter_by(user_id=int(user_id), status='active').first()
        
        if not subscription:
            return jsonify({
                'has_subscription': False,
                'plan_name': 'Free',
                'status': 'none'
            })
        
        plan = SubscriptionPlan.query.get(subscription.plan_id)
        return jsonify({
            'has_subscription': True,
            'plan_name': plan.name if plan else 'Unknown',
            'status': subscription.status,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            'max_projects': plan.max_projects if plan else 5,
            'max_annotations': plan.max_annotations if plan else 1000
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch subscription status: {str(e)}'}), 500

# User Management Routes
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if not current_user or current_user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        users = User.query.all()
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        return jsonify(users_data)
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch users: {str(e)}'}), 500

@app.route('/api/users/<int:user_id>/role', methods=['PUT'])
@jwt_required()
def update_user_role():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if not current_user or current_user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in [role.value for role in UserRole]:
            return jsonify({'error': 'Invalid role'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.role = UserRole(new_role)
        db.session.commit()
        
        return jsonify({
            'message': 'User role updated successfully',
            'user_id': user.id,
            'new_role': user.role.value
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to update user role: {str(e)}'}), 500

