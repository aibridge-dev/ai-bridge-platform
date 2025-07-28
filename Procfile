web: gunicorn --config gunicorn.conf.py src.main_production:app
worker: celery -A src.main_production.celery worker --loglevel=info
beat: celery -A src.main_production.celery beat --loglevel=info

