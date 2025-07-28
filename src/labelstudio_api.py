"""
Label Studio API Integration Service
Handles all communication with Label Studio instance
"""
import requests
import json
import os
from typing import Dict, List, Optional, Any

class LabelStudioAPI:
    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # Set up authentication headers
        if api_key:
            self.session.headers.update({
                'Authorization': f'Token {api_key}',
                'Content-Type': 'application/json'
            })
    
    def health_check(self) -> bool:
        """Check if Label Studio is running and accessible"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            return response.status_code == 200
        except Exception as e:
            print(f"Label Studio health check failed: {e}")
            return False
    
    def get_or_create_user(self, email: str, first_name: str = "", last_name: str = "") -> Optional[Dict]:
        """Get existing user or create new one in Label Studio"""
        try:
            # First try to get existing user
            response = self.session.get(f"{self.base_url}/api/users")
            if response.status_code == 200:
                users = response.json()
                for user in users:
                    if user.get('email') == email:
                        return user
            
            # Create new user if not found
            user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'username': email.split('@')[0]
            }
            
            response = self.session.post(f"{self.base_url}/api/users", json=user_data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Failed to create user: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error managing user: {e}")
            return None
    
    def create_project(self, title: str, description: str = "", label_config: str = None) -> Optional[Dict]:
        """Create a new project in Label Studio"""
        try:
            # Default label config for image classification
            if not label_config:
                label_config = '''
                <View>
                  <Image name="image" value="$image"/>
                  <Choices name="choice" toName="image">
                    <Choice value="Electronics"/>
                    <Choice value="Clothing"/>
                    <Choice value="Home & Garden"/>
                    <Choice value="Sports"/>
                    <Choice value="Books"/>
                  </Choices>
                </View>
                '''
            
            project_data = {
                'title': title,
                'description': description,
                'label_config': label_config,
                'expert_instruction': 'Please classify the image into one of the provided categories.',
                'show_instruction': True,
                'show_skip_button': True,
                'enable_empty_annotation': False
            }
            
            response = self.session.post(f"{self.base_url}/api/projects", json=project_data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Failed to create project: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating project: {e}")
            return None
    
    def import_tasks(self, project_id: int, tasks: List[Dict]) -> bool:
        """Import tasks (data) into a Label Studio project"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/projects/{project_id}/import",
                json=tasks
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error importing tasks: {e}")
            return False
    
    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Get all tasks for a project"""
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}/tasks")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return []
    
    def get_project_annotations(self, project_id: int) -> List[Dict]:
        """Get all annotations for a project"""
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}/annotations")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting annotations: {e}")
            return []
    
    def assign_user_to_project(self, project_id: int, user_id: int) -> bool:
        """Assign a user to a project"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/projects/{project_id}/members",
                json={'user': user_id}
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error assigning user to project: {e}")
            return False
    
    def get_project_stats(self, project_id: int) -> Dict:
        """Get project statistics"""
        try:
            response = self.session.get(f"{self.base_url}/api/projects/{project_id}")
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
    
    def delete_project(self, project_id: int) -> bool:
        """Delete a project"""
        try:
            response = self.session.delete(f"{self.base_url}/api/projects/{project_id}")
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False

# Global instance with authentication
label_studio_api = LabelStudioAPI(api_key="3fdbf2e68fe2fb1dac23f6f6501c5ab388d0ab74")

