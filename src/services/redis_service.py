"""
Redis service for caching and session management
"""
import redis
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
from src.config import get_config

class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis server"""
        try:
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def set(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Set a key-value pair with optional expiration"""
        if not self.is_connected():
            return False
        
        try:
            # Serialize complex objects
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = value
            else:
                serialized_value = pickle.dumps(value)
            
            result = self.redis_client.set(key, serialized_value, ex=expire)
            return bool(result)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        if not self.is_connected():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Try pickle deserialization
            try:
                return pickle.loads(value)
            except:
                pass
            
            # Return as string if all else fails
            return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key"""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.expire(key, seconds))
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value"""
        if not self.is_connected():
            return None
        
        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            print(f"Redis INCR error: {e}")
            return None
    
    def set_hash(self, key: str, mapping: dict, expire: Optional[int] = None) -> bool:
        """Set hash fields"""
        if not self.is_connected():
            return False
        
        try:
            # Serialize values in the hash
            serialized_mapping = {}
            for field, value in mapping.items():
                if isinstance(value, (dict, list, tuple)):
                    serialized_mapping[field] = json.dumps(value)
                else:
                    serialized_mapping[field] = str(value)
            
            result = self.redis_client.hset(key, mapping=serialized_mapping)
            if expire:
                self.redis_client.expire(key, expire)
            return True
        except Exception as e:
            print(f"Redis HSET error: {e}")
            return False
    
    def get_hash(self, key: str, field: Optional[str] = None) -> Optional[Union[dict, str]]:
        """Get hash field(s)"""
        if not self.is_connected():
            return None
        
        try:
            if field:
                value = self.redis_client.hget(key, field)
                if value is None:
                    return None
                
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except:
                    return value.decode('utf-8') if isinstance(value, bytes) else value
            else:
                hash_data = self.redis_client.hgetall(key)
                if not hash_data:
                    return None
                
                # Deserialize all values
                result = {}
                for field, value in hash_data.items():
                    field_name = field.decode('utf-8') if isinstance(field, bytes) else field
                    try:
                        result[field_name] = json.loads(value)
                    except:
                        result[field_name] = value.decode('utf-8') if isinstance(value, bytes) else value
                
                return result
        except Exception as e:
            print(f"Redis HGET error: {e}")
            return None
    
    def cache_user_session(self, user_id: int, session_data: dict, expire: int = 3600) -> bool:
        """Cache user session data"""
        key = f"user_session:{user_id}"
        return self.set_hash(key, session_data, expire)
    
    def get_user_session(self, user_id: int) -> Optional[dict]:
        """Get user session data"""
        key = f"user_session:{user_id}"
        return self.get_hash(key)
    
    def invalidate_user_session(self, user_id: int) -> bool:
        """Invalidate user session"""
        key = f"user_session:{user_id}"
        return self.delete(key)
    
    def cache_project_stats(self, project_id: int, stats: dict, expire: int = 300) -> bool:
        """Cache project statistics"""
        key = f"project_stats:{project_id}"
        return self.set(key, stats, expire)
    
    def get_project_stats(self, project_id: int) -> Optional[dict]:
        """Get cached project statistics"""
        key = f"project_stats:{project_id}"
        return self.get(key)
    
    def cache_annotation_progress(self, project_id: int, progress: dict, expire: int = 60) -> bool:
        """Cache annotation progress"""
        key = f"annotation_progress:{project_id}"
        return self.set(key, progress, expire)
    
    def get_annotation_progress(self, project_id: int) -> Optional[dict]:
        """Get cached annotation progress"""
        key = f"annotation_progress:{project_id}"
        return self.get(key)
    
    def rate_limit_check(self, identifier: str, limit: int, window: int) -> bool:
        """Check rate limiting"""
        key = f"rate_limit:{identifier}"
        current = self.increment(key)
        
        if current == 1:
            self.expire(key, window)
        
        return current <= limit
    
    def flush_cache(self, pattern: Optional[str] = None) -> bool:
        """Flush cache (use with caution)"""
        if not self.is_connected():
            return False
        
        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                self.redis_client.flushdb()
            return True
        except Exception as e:
            print(f"Redis FLUSH error: {e}")
            return False

# Global Redis service instance
redis_service = RedisService()

