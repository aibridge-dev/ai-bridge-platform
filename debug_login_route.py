#!/usr/bin/env python3
"""
Debug login route step by step
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_fixed import app, db, User
from flask import request
import json

def debug_login_route():
    with app.app_context():
        # Simulate the login request
        data = {'email': 'admin@aibridge.com', 'password': 'admin123'}
        email = data.get('email')
        password = data.get('password')
        
        print(f"Email: {email}")
        print(f"Password: {password}")
        
        if not email or not password:
            print("❌ Missing email or password")
            return
        
        user = User.query.filter_by(email=email).first()
        print(f"User found: {user}")
        
        if not user:
            print("❌ User not found")
            return
            
        print(f"User email: {user.email}")
        print(f"User active: {user.is_active}")
        
        password_check = user.check_password(password)
        print(f"Password check result: {password_check}")
        
        if not user or not password_check:
            print("❌ Invalid credentials")
            return
            
        if not user.is_active:
            print("❌ Account deactivated")
            return
            
        print("✅ Login should succeed")

if __name__ == '__main__':
    debug_login_route()

