"""
Enhanced Label Studio Integration Service with Containerization Support
"""
import os
import json
import requests
import subprocess
import time
from typing import Dict, List, Optional, Any
from src.config import get_config
from src.services.redis_service import redis_service

class LabelStudioService:
    """Enhanced Label Studio service with containerization and deployment support"""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.LABEL_STUDIO_URL
        self.api_token = self.config.LABEL_STUDIO_API_TOKEN
        self.headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        } if self.api_token else {'Content-Type': 'application/json'}
        self.container_name = 'aibridge-labelstudio'
        
    def check_connection(self) -> bool:
        """Check if Label Studio is accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/health/", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_containerized_labelstudio(self) -> bool:
        """Start Label Studio in a Docker container"""
        try:
            # Check if container already exists
            check_cmd = f"docker ps -a --filter name={self.container_name} --format '{{{{.Names}}}}'"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if self.container_name in result.stdout:
                # Container exists, start it
                start_cmd = f"docker start {self.container_name}"
                subprocess.run(start_cmd, shell=True, check=True)
                print(f"✅ Started existing Label Studio container: {self.container_name}")
            else:
                # Create and start new container
                create_cmd = f"""
                docker run -d \
                    --name {self.container_name} \
                    -p 8080:8080 \
                    -e LABEL_STUDIO_HOST=0.0.0.0 \
                    -e LABEL_STUDIO_PORT=8080 \
                    -v labelstudio_data:/label-studio/data \
                    heartexlabs/label-studio:latest
                """
                subprocess.run(create_cmd, shell=True, check=True)
                print(f"✅ Created and started Label Studio container: {self.container_name}")
            
            # Wait for Label Studio to be ready
            for i in range(30):  # Wait up to 30 seconds
                if self.check_connection():
                    print("✅ Label Studio is ready and accessible")
                    return True
                time.sleep(1)
            
            print("⚠️ Label Studio container started but not accessible")
            return False
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Label Studio container: {e}")
            return False
        except Exception as e:
            print(f"❌ Error starting containerized Label Studio: {e}")
            return False
    
    def start_local_labelstudio(self) -> bool:
        """Start Label Studio locally (fallback method)"""
        try:
            # Check if Label Studio is already running
            if self.check_connection():
                print("✅ Label Studio is already running")
                return True
            
            # Start Label Studio in background
            cmd = [
                'label-studio',
                '--host', '0.0.0.0',
                '--port', '8080',
                '--username', 'admin@aibridge.com',
                '--password', 'aibridge123'
            ]
            
            # Start process in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(__file__)
            )
            
            # Wait for Label Studio to start
            for i in range(30):
                if self.check_connection():
                    print("✅ Label Studio started locally")
                    return True
                time.sleep(1)
            
            print("⚠️ Label Studio process started but not accessible")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start local Label Studio: {e}")
            return False
    
    def ensure_labelstudio_running(self) -> bool:
        """Ensure Label Studio is running, try multiple methods"""
        # First check if already running
        if self.check_connection():
            print("✅ Label Studio is already accessible")
            return True
        
        print("🚀 Starting Label Studio...")
        
        # Try containerized approach first
        if self.start_containerized_labelstudio():
            return True
        
        print("🔄 Containerized approach failed, trying local installation...")
        
        # Fallback to local installation
        if self.start_local_labelstudio():
            return True
        
        print("❌ All Label Studio startup methods failed")
        return False
    
    def create_project(self, project_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a new Label Studio project"""
        try:
            if not self.ensure_labelstudio_running():
                return None
            
            # Prepare project configuration
            config = {
                'title': project_data.get('title', 'AI Bridge Project'),
                'description': project_data.get('description', ''),
                'label_config': project_data.get('label_config', self._get_default_config()),
                'expert_instruction': project_data.get('instructions', ''),
                'show_instruction': True,
                'show_skip_button': True,
                'enable_empty_annotation': False
            }
            
            response = requests.post(
                f"{self.base_url}/api/projects/",
                headers=self.headers,
                json=config,
                timeout=30
            )
            
            if response.status_code == 201:
                project = response.json()
                print(f"✅ Created Label Studio project: {project['id']}")
                
                # Cache project info
                redis_service.set(
                    f"labelstudio_project:{project_data.get('ai_bridge_project_id')}",
                    project,
                    expire=3600
                )
                
                return project
            else:
                print(f"❌ Failed to create project: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating Label Studio project: {e}")
            return None
    
    def import_tasks(self, project_id: int, tasks: List[Dict]) -> bool:
        """Import tasks into Label Studio project"""
        try:
            if not self.ensure_labelstudio_running():
                return False
            
            response = requests.post(
                f"{self.base_url}/api/projects/{project_id}/import",
                headers=self.headers,
                json=tasks,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Imported {len(tasks)} tasks to project {project_id}")
                return True
            else:
                print(f"❌ Failed to import tasks: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error importing tasks: {e}")
            return False
    
    def get_annotations(self, project_id: int) -> Optional[List[Dict]]:
        """Get all annotations from a project"""
        try:
            if not self.ensure_labelstudio_running():
                return None
            
            response = requests.get(
                f"{self.base_url}/api/projects/{project_id}/annotations/",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                annotations = response.json()
                print(f"✅ Retrieved {len(annotations)} annotations from project {project_id}")
                return annotations
            else:
                print(f"❌ Failed to get annotations: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting annotations: {e}")
            return None
    
    def export_annotations(self, project_id: int, export_type: str = 'JSON') -> Optional[Dict]:
        """Export annotations from a project"""
        try:
            if not self.ensure_labelstudio_running():
                return None
            
            response = requests.get(
                f"{self.base_url}/api/projects/{project_id}/export",
                headers=self.headers,
                params={'exportType': export_type},
                timeout=60
            )
            
            if response.status_code == 200:
                if export_type.upper() == 'JSON':
                    return response.json()
                else:
                    return {'data': response.text, 'format': export_type}
            else:
                print(f"❌ Failed to export annotations: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error exporting annotations: {e}")
            return None
    
    def get_project_stats(self, project_id: int) -> Optional[Dict]:
        """Get project statistics"""
        try:
            if not self.ensure_labelstudio_running():
                return None
            
            # Check cache first
            cached_stats = redis_service.get(f"labelstudio_stats:{project_id}")
            if cached_stats:
                return cached_stats
            
            response = requests.get(
                f"{self.base_url}/api/projects/{project_id}/",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                project_data = response.json()
                stats = {
                    'total_tasks': project_data.get('task_number', 0),
                    'completed_tasks': project_data.get('num_tasks_with_annotations', 0),
                    'total_annotations': project_data.get('total_annotations_number', 0),
                    'progress_percentage': 0
                }
                
                if stats['total_tasks'] > 0:
                    stats['progress_percentage'] = round(
                        (stats['completed_tasks'] / stats['total_tasks']) * 100, 2
                    )
                
                # Cache for 5 minutes
                redis_service.set(f"labelstudio_stats:{project_id}", stats, expire=300)
                
                return stats
            else:
                print(f"❌ Failed to get project stats: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting project stats: {e}")
            return None
    
    def _get_default_config(self) -> str:
        """Get default Label Studio configuration"""
        return '''
        <View>
          <Text name="text" value="$text"/>
          <Choices name="sentiment" toName="text">
            <Choice value="positive"/>
            <Choice value="negative"/>
            <Choice value="neutral"/>
          </Choices>
        </View>
        '''
    
    def get_annotation_templates(self) -> Dict[str, str]:
        """Get predefined annotation templates"""
        return {
            'text_classification': '''
            <View>
              <Text name="text" value="$text"/>
              <Choices name="label" toName="text">
                <Choice value="positive"/>
                <Choice value="negative"/>
                <Choice value="neutral"/>
              </Choices>
            </View>
            ''',
            'named_entity_recognition': '''
            <View>
              <Text name="text" value="$text"/>
              <Labels name="label" toName="text">
                <Label value="PERSON" background="red"/>
                <Label value="ORG" background="blue"/>
                <Label value="LOC" background="green"/>
                <Label value="MISC" background="yellow"/>
              </Labels>
            </View>
            ''',
            'image_classification': '''
            <View>
              <Image name="image" value="$image"/>
              <Choices name="choice" toName="image">
                <Choice value="cat"/>
                <Choice value="dog"/>
                <Choice value="other"/>
              </Choices>
            </View>
            ''',
            'object_detection': '''
            <View>
              <Image name="image" value="$image"/>
              <RectangleLabels name="label" toName="image">
                <Label value="person" background="red"/>
                <Label value="car" background="blue"/>
                <Label value="object" background="green"/>
              </RectangleLabels>
            </View>
            ''',
            'audio_classification': '''
            <View>
              <Audio name="audio" value="$audio"/>
              <Choices name="emotion" toName="audio">
                <Choice value="happy"/>
                <Choice value="sad"/>
                <Choice value="angry"/>
                <Choice value="neutral"/>
              </Choices>
            </View>
            '''
        }
    
    def cleanup_container(self) -> bool:
        """Clean up Label Studio container"""
        try:
            stop_cmd = f"docker stop {self.container_name}"
            subprocess.run(stop_cmd, shell=True, check=False)
            
            remove_cmd = f"docker rm {self.container_name}"
            subprocess.run(remove_cmd, shell=True, check=False)
            
            print(f"✅ Cleaned up Label Studio container: {self.container_name}")
            return True
        except Exception as e:
            print(f"❌ Error cleaning up container: {e}")
            return False

# Global Label Studio service instance
labelstudio_service = LabelStudioService()

