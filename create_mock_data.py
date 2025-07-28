#!/usr/bin/env python3
"""
Create comprehensive mock data for AI Bridge platform
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_simple import app, db, User, UserRole
from datetime import datetime, timedelta
import random

def create_comprehensive_mock_data():
    with app.app_context():
        print("Creating comprehensive mock data...")
        
        # Create additional users
        users_data = [
            {
                'username': 'sarah_manager',
                'email': 'sarah@aibridge.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'role': UserRole.ADMIN,
                'password': 'manager123'
            },
            {
                'username': 'mike_client',
                'email': 'mike@techcorp.com',
                'first_name': 'Mike',
                'last_name': 'Chen',
                'role': UserRole.CLIENT_USER,
                'password': 'client123'
            },
            {
                'username': 'anna_labeler',
                'email': 'anna@aibridge.com',
                'first_name': 'Anna',
                'last_name': 'Rodriguez',
                'role': UserRole.LABELER,
                'password': 'labeler123'
            },
            {
                'username': 'david_reviewer',
                'email': 'david@aibridge.com',
                'first_name': 'David',
                'last_name': 'Kim',
                'role': UserRole.LABELER,
                'password': 'reviewer123'
            },
            {
                'username': 'lisa_client',
                'email': 'lisa@medtech.com',
                'first_name': 'Lisa',
                'last_name': 'Wang',
                'role': UserRole.CLIENT_USER,
                'password': 'client456'
            }
        ]
        
        created_users = []
        for user_data in users_data:
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if not existing_user:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role=user_data['role'],
                    is_active=True,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
                    last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                created_users.append(user)
                print(f"✅ Created user: {user.email}")
        
        db.session.commit()
        print(f"✅ Created {len(created_users)} additional users")
        
        # Update existing users with more realistic data
        admin_user = User.query.filter_by(email='admin@aibridge.com').first()
        if admin_user:
            admin_user.last_login = datetime.utcnow() - timedelta(minutes=5)
            
        client_user = User.query.filter_by(email='client@example.com').first()
        if client_user:
            client_user.last_login = datetime.utcnow() - timedelta(hours=2)
            
        annotator_user = User.query.filter_by(email='annotator@example.com').first()
        if annotator_user:
            annotator_user.last_login = datetime.utcnow() - timedelta(hours=1)
        
        db.session.commit()
        
        print("✅ Mock data creation completed!")
        
        # Print summary
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.filter_by(role=UserRole.ADMIN).count()
        client_users = User.query.filter_by(role=UserRole.CLIENT_USER).count()
        labeler_users = User.query.filter_by(role=UserRole.LABELER).count()
        
        print(f"\n📊 Platform Statistics:")
        print(f"Total Users: {total_users}")
        print(f"Active Users: {active_users}")
        print(f"Admin Users: {admin_users}")
        print(f"Client Users: {client_users}")
        print(f"Labeler Users: {labeler_users}")
        
        print(f"\n👥 User List:")
        users = User.query.all()
        for user in users:
            print(f"- {user.email} ({user.role.value}) - Last login: {user.last_login}")

if __name__ == '__main__':
    create_comprehensive_mock_data()

