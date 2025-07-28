import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
import hashlib
import mimetypes
from werkzeug.utils import secure_filename

class S3Service:
    def __init__(self):
        self.bucket_name = os.getenv('AWS_S3_BUCKET', 'signaldrop-file-storage')
        self.region = os.getenv('AWS_REGION', 'us-east-2')
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=self.region
            )
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
    
    def generate_file_key(self, project_id, dataset_id, filename):
        """Generate a unique S3 key for a file"""
        secure_name = secure_filename(filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"projects/{project_id}/datasets/{dataset_id}/{timestamp}_{secure_name}"
    
    def upload_file(self, file_obj, project_id, dataset_id, filename, content_type=None):
        """Upload a file to S3 and return file metadata"""
        try:
            # Generate unique key
            file_key = self.generate_file_key(project_id, dataset_id, filename)
            
            # Determine content type
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Calculate file hash
            file_obj.seek(0)
            file_content = file_obj.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            file_size = len(file_content)
            
            # Reset file pointer
            file_obj.seek(0)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                file_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original_filename': filename,
                        'project_id': str(project_id),
                        'dataset_id': str(dataset_id),
                        'file_hash': file_hash,
                        'upload_timestamp': datetime.utcnow().isoformat()
                    }
                }
            )
            
            return {
                'file_key': file_key,
                'file_size': file_size,
                'file_hash': file_hash,
                'content_type': content_type,
                'bucket': self.bucket_name,
                'region': self.region
            }
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    def generate_presigned_url(self, file_key, expiration=3600):
        """Generate a presigned URL for secure file access"""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    def generate_presigned_post(self, file_key, expiration=3600, max_file_size=100*1024*1024):
        """Generate a presigned POST for direct browser uploads"""
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_key,
                ExpiresIn=expiration,
                Conditions=[
                    ['content-length-range', 1, max_file_size]
                ]
            )
            return response
        except ClientError as e:
            raise Exception(f"Failed to generate presigned POST: {str(e)}")
    
    def delete_file(self, file_key):
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete file from S3: {str(e)}")
    
    def list_files(self, prefix):
        """List files with a specific prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"')
                    })
            
            return files
        except ClientError as e:
            raise Exception(f"Failed to list files from S3: {str(e)}")
    
    def get_file_metadata(self, file_key):
        """Get metadata for a specific file"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise Exception(f"Failed to get file metadata: {str(e)}")
    
    def copy_file(self, source_key, destination_key):
        """Copy a file within S3"""
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to copy file in S3: {str(e)}")
    
    def test_connection(self):
        """Test S3 connection by checking bucket access"""
        try:
            # Test bucket access directly (ListBuckets permission not required)
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            print(f"S3 connection test failed: {e}")
            return False
        except Exception as e:
            print(f"S3 connection error: {e}")
            return False

# Global S3 service instance
try:
    s3_service = S3Service()
except Exception as e:
    print(f"Failed to initialize S3 service: {e}")
    s3_service = None

def get_s3_service():
    """Get or create S3 service instance"""
    global s3_service
    if s3_service is None:
        try:
            s3_service = S3Service()
        except Exception as e:
            print(f"Failed to create S3 service: {e}")
            return None
    return s3_service

