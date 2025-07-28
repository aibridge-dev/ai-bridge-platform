#!/usr/bin/env python3
"""
Test script to debug login issue
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_fixed import app, db, User
from werkzeug.security import check_password_hash

def test_login():
    with app.app_context():
        # Find admin user
        user = User.query.filter_by(email='admin@aibridge.com').first()
        if not user:
            print("❌ Admin user not found!")
            return
        
        print(f"✅ Found user: {user.email}")
        print(f"Password hash: {user.password_hash}")
        
        # Test password
        password = 'admin123'
        is_valid = check_password_hash(user.password_hash, password)
        print(f"Password check result: {is_valid}")
        
        # Test user method
        is_valid_method = user.check_password(password)
        print(f"User method check result: {is_valid_method}")

if __name__ == '__main__':
    test_login()

