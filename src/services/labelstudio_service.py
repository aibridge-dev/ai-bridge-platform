import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from werkzeug.utils import secure_filename
from src.services.s3_service import get_s3_service

class LabelStudioService:
    def __init__(self):
        self.label_studio_url = os.getenv('LABEL_STUDIO_URL', 'http://localhost:8080')
        self.api_token = os.getenv('LABEL_STUDIO_API_TOKEN', '')
        self.s3_service = get_s3_service()
        
    def get_headers(self):
        """Get headers for Label Studio API requests"""
        return {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_project(self, name: str, description: str = '', label_config: str = None) -> Dict:
        """Create a new Label Studio project"""
        if not label_config:
            # Default image classification config
            label_config = '''
            <View>
              <Image name="image" value="$image"/>
              <Choices name="choice" toName="image">
                <Choice value="Class A"/>
                <Choice value="Class B"/>
                <Choice value="Class C"/>
              </Choices>
            </View>
            '''
        
        data = {
            'title': name,
            'description': description,
            'label_config': label_config,
            'expert_instruction': 'Please classify the image according to the provided categories.',
            'show_instruction': True,
            'show_skip_button': True,
            'enable_empty_annotation': False,
            'show_annotation_history': True,
            'organization': 1  # Default organization
        }
        
        try:
            response = requests.post(
                f'{self.label_studio_url}/api/projects/',
                headers=self.get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create Label Studio project: {str(e)}")
    
    def get_project(self, project_id: int) -> Dict:
        """Get Label Studio project details"""
        try:
            response = requests.get(
                f'{self.label_studio_url}/api/projects/{project_id}/',
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get Label Studio project: {str(e)}")
    
    def update_project(self, project_id: int, data: Dict) -> Dict:
        """Update Label Studio project"""
        try:
            response = requests.patch(
                f'{self.label_studio_url}/api/projects/{project_id}/',
                headers=self.get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to update Label Studio project: {str(e)}")
    
    def delete_project(self, project_id: int) -> bool:
        """Delete Label Studio project"""
        try:
            response = requests.delete(
                f'{self.label_studio_url}/api/projects/{project_id}/',
                headers=self.get_headers()
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete Label Studio project: {str(e)}")
    
    def import_tasks(self, project_id: int, tasks: List[Dict]) -> Dict:
        """Import tasks to Label Studio project"""
        try:
            response = requests.post(
                f'{self.label_studio_url}/api/projects/{project_id}/import/',
                headers=self.get_headers(),
                json=tasks
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to import tasks: {str(e)}")
    
    def get_tasks(self, project_id: int, page: int = 1, page_size: int = 100) -> Dict:
        """Get tasks from Label Studio project"""
        try:
            params = {
                'page': page,
                'page_size': page_size
            }
            response = requests.get(
                f'{self.label_studio_url}/api/projects/{project_id}/tasks/',
                headers=self.get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get tasks: {str(e)}")
    
    def get_task(self, task_id: int) -> Dict:
        """Get specific task details"""
        try:
            response = requests.get(
                f'{self.label_studio_url}/api/tasks/{task_id}/',
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.requests.RequestException as e:
            raise Exception(f"Failed to get task: {str(e)}")
    
    def get_annotations(self, task_id: int) -> List[Dict]:
        """Get annotations for a task"""
        try:
            response = requests.get(
                f'{self.label_studio_url}/api/tasks/{task_id}/annotations/',
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get annotations: {str(e)}")
    
    def create_annotation(self, task_id: int, result: List[Dict], completed_by: int = None) -> Dict:
        """Create annotation for a task"""
        data = {
            'task': task_id,
            'result': result,
            'completed_by': completed_by or 1,  # Default user ID
            'was_cancelled': False
        }
        
        try:
            response = requests.post(
                f'{self.label_studio_url}/api/tasks/{task_id}/annotations/',
                headers=self.get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create annotation: {str(e)}")
    
    def export_annotations(self, project_id: int, export_type: str = 'JSON') -> Dict:
        """Export annotations from Label Studio project"""
        try:
            params = {
                'exportType': export_type
            }
            response = requests.get(
                f'{self.label_studio_url}/api/projects/{project_id}/export/',
                headers=self.get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to export annotations: {str(e)}")
    
    def create_tasks_from_s3_files(self, project_id: int, s3_file_keys: List[str], 
                                   data_type: str = 'image') -> List[Dict]:
        """Create Label Studio tasks from S3 files"""
        tasks = []
        
        for file_key in s3_file_keys:
            try:
                # Generate presigned URL for the file
                presigned_url = self.s3_service.generate_presigned_url(
                    file_key=file_key,
                    expiration=86400  # 24 hours
                )
                
                # Create task data based on data type
                if data_type == 'image':
                    task_data = {
                        'data': {
                            'image': presigned_url
                        },
                        'meta': {
                            'file_key': file_key,
                            'original_filename': file_key.split('/')[-1],
                            'data_type': data_type
                        }
                    }
                elif data_type == 'text':
                    # For text files, we'd need to read the content
                    task_data = {
                        'data': {
                            'text': presigned_url  # Or actual text content
                        },
                        'meta': {
                            'file_key': file_key,
                            'original_filename': file_key.split('/')[-1],
                            'data_type': data_type
                        }
                    }
                elif data_type == 'audio':
                    task_data = {
                        'data': {
                            'audio': presigned_url
                        },
                        'meta': {
                            'file_key': file_key,
                            'original_filename': file_key.split('/')[-1],
                            'data_type': data_type
                        }
                    }
                elif data_type == 'video':
                    task_data = {
                        'data': {
                            'video': presigned_url
                        },
                        'meta': {
                            'file_key': file_key,
                            'original_filename': file_key.split('/')[-1],
                            'data_type': data_type
                        }
                    }
                else:
                    # Generic data type
                    task_data = {
                        'data': {
                            'url': presigned_url
                        },
                        'meta': {
                            'file_key': file_key,
                            'original_filename': file_key.split('/')[-1],
                            'data_type': data_type
                        }
                    }
                
                tasks.append(task_data)
                
            except Exception as e:
                print(f"Error creating task for file {file_key}: {str(e)}")
                continue
        
        # Import tasks to Label Studio
        if tasks:
            return self.import_tasks(project_id, tasks)
        
        return {'task_count': 0, 'annotation_count': 0, 'prediction_count': 0}
    
    def get_label_config_templates(self) -> Dict[str, str]:
        """Get predefined label configuration templates"""
        templates = {
            'image_classification': '''
            <View>
              <Image name="image" value="$image"/>
              <Choices name="choice" toName="image">
                <Choice value="Class A"/>
                <Choice value="Class B"/>
                <Choice value="Class C"/>
              </Choices>
            </View>
            ''',
            
            'object_detection': '''
            <View>
              <Image name="image" value="$image"/>
              <RectangleLabels name="label" toName="image">
                <Label value="Person"/>
                <Label value="Car"/>
                <Label value="Object"/>
              </RectangleLabels>
            </View>
            ''',
            
            'text_classification': '''
            <View>
              <Text name="text" value="$text"/>
              <Choices name="sentiment" toName="text">
                <Choice value="Positive"/>
                <Choice value="Negative"/>
                <Choice value="Neutral"/>
              </Choices>
            </View>
            ''',
            
            'named_entity_recognition': '''
            <View>
              <Text name="text" value="$text"/>
              <Labels name="label" toName="text">
                <Label value="Person"/>
                <Label value="Organization"/>
                <Label value="Location"/>
              </Labels>
            </View>
            ''',
            
            'audio_classification': '''
            <View>
              <Audio name="audio" value="$audio"/>
              <Choices name="class" toName="audio">
                <Choice value="Speech"/>
                <Choice value="Music"/>
                <Choice value="Noise"/>
              </Choices>
            </View>
            ''',
            
            'video_classification': '''
            <View>
              <Video name="video" value="$video"/>
              <Choices name="category" toName="video">
                <Choice value="Action"/>
                <Choice value="Drama"/>
                <Choice value="Comedy"/>
              </Choices>
            </View>
            '''
        }
        
        return templates
    
    def validate_connection(self) -> bool:
        """Validate connection to Label Studio"""
        try:
            response = requests.get(
                f'{self.label_studio_url}/api/projects/',
                headers=self.get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

# Global Label Studio service instance
labelstudio_service = None

def get_labelstudio_service():
    """Get or create Label Studio service instance"""
    global labelstudio_service
    if labelstudio_service is None:
        labelstudio_service = LabelStudioService()
    return labelstudio_service

