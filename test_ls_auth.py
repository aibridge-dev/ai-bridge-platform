#!/usr/bin/env python3
"""
Test Label Studio authentication and get API token
"""
import requests
import json
from bs4 import BeautifulSoup

def get_label_studio_token():
    """Get authentication token from Label Studio"""
    session = requests.Session()
    
    try:
        # Step 1: Get login page to get CSRF token
        print("Getting login page...")
        response = session.get('http://localhost:8080/user/login/')
        if response.status_code != 200:
            print(f"Failed to get login page: {response.status_code}")
            return None
        
        # Parse CSRF token from the page
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = None
        
        # Look for CSRF token in various places
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        if not csrf_token:
            # Try to get from cookies
            csrf_token = session.cookies.get('csrftoken')
        
        if not csrf_token:
            print("Could not find CSRF token")
            return None
        
        print(f"Found CSRF token: {csrf_token[:20]}...")
        
        # Step 2: Login with CSRF token
        login_data = {
            'email': 'admin@aibridge.com',
            'password': 'aibridge123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Referer': 'http://localhost:8080/user/login/',
            'X-CSRFToken': csrf_token
        }
        
        print("Attempting login...")
        response = session.post('http://localhost:8080/user/login/', 
                              data=login_data, 
                              headers=headers,
                              allow_redirects=False)
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code in [302, 200]:
            print("Login successful!")
            
            # Step 3: Try to get API token
            print("Getting API token...")
            response = session.get('http://localhost:8080/api/current-user/token')
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"Token data: {token_data}")
                return token_data.get('token')
            else:
                print(f"Failed to get token: {response.status_code} - {response.text}")
                
                # Try alternative endpoint
                response = session.get('http://localhost:8080/api/current-user/')
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"User data: {json.dumps(user_data, indent=2)}")
                    return user_data.get('token')
        else:
            print(f"Login failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return None

def test_api_with_session():
    """Test API access with session authentication"""
    session = requests.Session()
    
    try:
        # Login first
        print("\nTesting session-based API access...")
        
        # Get login page
        response = session.get('http://localhost:8080/user/login/')
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        csrf_token = csrf_input.get('value') if csrf_input else session.cookies.get('csrftoken')
        
        # Login
        login_data = {
            'email': 'admin@aibridge.com',
            'password': 'aibridge123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Referer': 'http://localhost:8080/user/login/',
            'X-CSRFToken': csrf_token
        }
        
        response = session.post('http://localhost:8080/user/login/', 
                              data=login_data, 
                              headers=headers,
                              allow_redirects=False)
        
        if response.status_code in [302, 200]:
            print("Session login successful!")
            
            # Test API endpoints with session
            print("Testing projects API...")
            response = session.get('http://localhost:8080/api/projects/')
            print(f"Projects API status: {response.status_code}")
            
            if response.status_code == 200:
                projects = response.json()
                print(f"Found {len(projects)} projects")
                return session
            else:
                print(f"Projects API failed: {response.text}")
        
    except Exception as e:
        print(f"Session test error: {e}")
    
    return None

if __name__ == "__main__":
    # Try to get token
    token = get_label_studio_token()
    if token:
        print(f"\nSuccess! API Token: {token}")
    else:
        print("\nFailed to get token, trying session-based approach...")
        session = test_api_with_session()
        if session:
            print("Session-based API access working!")
        else:
            print("All authentication methods failed")

