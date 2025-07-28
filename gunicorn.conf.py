"""
AI Bridge Platform - Production Gunicorn Configuration
Optimized for Railway deployment with proper worker management
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Preload application for better performance
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'aibridge_platform'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Worker process management
worker_tmp_dir = '/dev/shm'
worker_class = 'sync'

# Application
wsgi_module = 'src.main_production:app'

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("AI Bridge Platform server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

# Environment variables for the application
raw_env = [
    'DATABASE_URL=' + os.environ.get('DATABASE_URL', ''),
    'REDIS_URL=' + os.environ.get('REDIS_URL', ''),
    'SECRET_KEY=' + os.environ.get('SECRET_KEY', 'production-secret-key'),
    'JWT_SECRET_KEY=' + os.environ.get('JWT_SECRET_KEY', 'production-jwt-secret'),
    'AWS_ACCESS_KEY_ID=' + os.environ.get('AWS_ACCESS_KEY_ID', ''),
    'AWS_SECRET_ACCESS_KEY=' + os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
    'AWS_S3_BUCKET=' + os.environ.get('AWS_S3_BUCKET', 'signaldrop-file-storage'),
    'LABEL_STUDIO_URL=' + os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080'),
    'LABEL_STUDIO_USERNAME=' + os.environ.get('LABEL_STUDIO_USERNAME', 'admin@aibridge.com'),
    'LABEL_STUDIO_PASSWORD=' + os.environ.get('LABEL_STUDIO_PASSWORD', 'aibridge123'),
]

