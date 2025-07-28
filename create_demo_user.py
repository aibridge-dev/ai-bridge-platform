#!/usr/bin/env python3
"""
Script to create demo users for AI Bridge platform
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_fixed import app, db, User, UserRole
from werkzeug.security import generate_password_hash

def create_demo_users():
    with app.app_context():
        # Clear existing users
        User.query.delete()
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@aibridge.com',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        admin.password_hash = generate_password_hash('admin123')
        db.session.add(admin)
        
        # Create client user
        client = User(
            username='client',
            email='client@example.com',
            first_name='Client',
            last_name='User',
            role=UserRole.CLIENT_USER,
            is_active=True,
            is_verified=True
        )
        client.password_hash = generate_password_hash('client123')
        db.session.add(client)
        
        # Create annotator user
        annotator = User(
            username='annotator',
            email='annotator@example.com',
            first_name='Annotator',
            last_name='User',
            role=UserRole.LABELER,
            is_active=True,
            is_verified=True
        )
        annotator.password_hash = generate_password_hash('annotator123')
        db.session.add(annotator)
        
        db.session.commit()
        print("✅ Demo users created successfully!")
        
        # Verify users
        users = User.query.all()
        for user in users:
            print(f"User: {user.email} - Role: {user.role.value}")

if __name__ == '__main__':
    create_demo_users()

