#!/usr/bin/env python3
"""
Debug authentication issue
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_fixed import app, db, User
import requests
import json

def debug_auth():
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(email='admin@aibridge.com').first()
        if user:
            print(f"✅ User found: {user.email}")
            print(f"Password hash: {user.password_hash}")
            print(f"Password check: {user.check_password('admin123')}")
        else:
            print("❌ User not found")
            
        # Test API call
        print("\n--- Testing API call ---")
        try:
            response = requests.post(
                'http://localhost:5000/api/auth/login',
                json={'email': 'admin@aibridge.com', 'password': 'admin123'},
                headers={'Content-Type': 'application/json'}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    debug_auth()

