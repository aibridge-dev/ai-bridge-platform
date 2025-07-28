"""
Label Studio Session-Based API Integration
Uses session authentication instead of tokens
"""
import requests
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

class LabelStudioSessionAPI:
    def __init__(self, base_url: str = "http://localhost:8080", username: str = "admin@aibridge.com", password: str = "aibridge123"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False
        
        # Authenticate on initialization
        self.authenticate()
    
    def authenticate(self) -> bool:
        """Authenticate with Label Studio using session"""
        try:
            # Step 1: Get login page to get CSRF token
            response = self.session.get(f'{self.base_url}/user/login/')
            if response.status_code != 200:
                print(f"Failed to get login page: {response.status_code}")
                return False
            
            # Parse CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input.get('value') if csrf_input else self.session.cookies.get('csrftoken')
            
            if not csrf_token:
                print("Could not find CSRF token")
                return False
            
            # Step 2: Login with CSRF token
            login_data = {
                'email': self.username,
                'password': self.password,
                'csrfmiddlewaretoken': csrf_token
            }
            
            headers = {
                'Referer': f'{self.base_url}/user/login/',
                'X-CSRFToken': csrf_token
            }
            
            response = self.session.post(f'{self.base_url}/user/login/', 
                                      data=login_data, 
                                      headers=headers,
                                      allow_redirects=False)
            
            if response.status_code in [302, 200]:
                self.authenticated = True
                print("Label Studio authentication successful!")
                return True
            else:
                print(f"Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if Label Studio is running and accessible"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            return response.status_code == 200
        except Exception as e:
            print(f"Label Studio health check failed: {e}")
            return False
    
    def create_project(self, title: str, description: str = "", label_config: str = None) -> Optional[Dict]:
        """Create a new project in Label Studio"""
        if not self.authenticated:
            print("Not authenticated with Label Studio")
            return None
            
        try:
            # Default label config for image classification
            if not label_config:
                label_config = '''<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image">
    <Choice value="Electronics"/>
    <Choice value="Clothing"/>
    <Choice value="Home &amp; Garden"/>
    <Choice value="Sports"/>
    <Choice value="Books"/>
  </Choices>
</View>'''
            
            project_data = {
                'title': title,
                'description': description,
                'label_config': label_config,
                'expert_instruction': 'Please classify the image into one of the provided categories.',
                'show_instruction': True,
                'show_skip_button': True,
                'enable_empty_annotation': False
            }
            
            # Get CSRF token for API call
            csrf_token = self.session.cookies.get('csrftoken')
            headers = {
                'X-CSRFToken': csrf_token,
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(f"{self.base_url}/api/projects/", 
                                       json=project_data,
                                       headers=headers)
            
            if response.status_code in [200, 201]:
                project = response.json()
                print(f"Created Label Studio project: {project.get('id')} - {title}")
                return project
            else:
                print(f"Failed to create project: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating project: {e}")
            return None
    
    def import_tasks(self, project_id: int, tasks: List[Dict]) -> bool:
        """Import tasks (data) into a Label Studio project"""
        if not self.authenticated:
            return False
            
        try:
            csrf_token = self.session.cookies.get('csrftoken')
            headers = {
                'X-CSRFToken': csrf_token,
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/projects/{project_id}/import",
                json=tasks,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                print(f"Imported {len(tasks)} tasks to project {project_id}")
                return True
            else:
                print(f"Failed to import tasks: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error importing tasks: {e}")
            return False
    
    def get_projects(self) -> List[Dict]:
        """Get all projects"""
        if not self.authenticated:
            return []
            
        try:
            response = self.session.get(f"{self.base_url}/api/projects/")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get projects: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting projects: {e}")
            return []
    
    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Get all tasks for a project"""
        if not self.authenticated:
            return []
            
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}/tasks/")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return []
    
    def get_project_annotations(self, project_id: int) -> List[Dict]:
        """Get all annotations for a project"""
        if not self.authenticated:
            return []
            
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}/annotations/")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting annotations: {e}")
            return []
    
    def get_project_stats(self, project_id: int) -> Dict:
        """Get project statistics"""
        if not self.authenticated:
            return {}
            
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}/")
            if response.status_code == 200:
                project_data = response.json()
                
                # Get tasks and annotations
                tasks = self.get_project_tasks(project_id)
                annotations = self.get_project_annotations(project_id)
                
                return {
                    'project_id': project_id,
                    'title': project_data.get('title', ''),
                    'total_tasks': len(tasks),
                    'completed_tasks': len([t for t in tasks if t.get('is_labeled', False)]),
                    'total_annotations': len(annotations),
                    'progress_percentage': (len([t for t in tasks if t.get('is_labeled', False)]) / len(tasks) * 100) if tasks else 0
                }
            return {}
        except Exception as e:
            print(f"Error getting project stats: {e}")
            return {}

# Global instance
label_studio_session_api = LabelStudioSessionAPI()

