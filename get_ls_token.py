#!/usr/bin/env python3
"""
Get Label Studio authentication token
"""
import requests
import json

# Try to get token using session authentication
session = requests.Session()

# First, try to access the web interface to get session
try:
    # Get the main page to establish session
    response = session.get('http://localhost:8080/')
    print(f"Main page status: {response.status_code}")
    
    # Try to get current user info
    response = session.get('http://localhost:8080/api/current-user/')
    print(f"Current user status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"User data: {json.dumps(user_data, indent=2)}")
        
        # Try to get token
        response = session.get('http://localhost:8080/api/current-user/token')
        print(f"Token status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token: {token_data}")
        else:
            print(f"Token error: {response.text}")
    else:
        print(f"User error: {response.text}")

except Exception as e:
    print(f"Error: {e}")

# Try alternative approach - check if we can create projects without auth
try:
    print("\nTrying to create project without auth...")
    project_data = {
        'title': 'Test Project',
        'description': 'Test project creation',
        'label_config': '''
        <View>
          <Image name="image" value="$image"/>
          <Choices name="choice" toName="image">
            <Choice value="Test"/>
          </Choices>
        </View>
        '''
    }
    
    response = requests.post('http://localhost:8080/api/projects', json=project_data)
    print(f"Project creation status: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Project creation error: {e}")

