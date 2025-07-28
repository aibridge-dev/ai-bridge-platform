# AI Bridge Backend

Professional data labeling platform backend with PostgreSQL, Redis, and Label Studio integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Redis instance
- AWS S3 bucket

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-bridge-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your actual values
```

5. **Initialize database**
```bash
python -c "from src.main_production import app, db; app.app_context().push(); db.create_all()"
```

6. **Run the application**
```bash
# Development
python src/main_production.py

# Production
gunicorn --config gunicorn.conf.py src.main_production:app
```

## 📁 Project Structure

```
ai-bridge-backend/
├── src/
│   ├── config/
│   │   └── production.py          # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── production_models.py   # Database models
│   ├── main_production.py         # Main Flask application
│   └── labelstudio_session_api.py # Label Studio integration
├── gunicorn.conf.py               # Production server config
├── requirements.txt               # Python dependencies
├── Procfile                       # Railway deployment
├── railway.json                   # Railway configuration
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://username:password@host:port/database

# Redis (Railway Redis)
REDIS_URL=redis://username:password@host:port/0

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=your-s3-bucket-name

# Label Studio
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_USERNAME=admin@aibridge.com
LABEL_STUDIO_PASSWORD=your-password
```

## 🗄️ Database Schema

The application uses PostgreSQL with the following main tables:

- **users** - User accounts and authentication
- **organizations** - Client organizations
- **projects** - Data labeling projects
- **datasets** - File collections within projects
- **annotations** - Individual labeling tasks
- **activity_logs** - Audit trail

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics

### Health Check
- `GET /api/health` - Service health status

## 🚀 Deployment

### Railway Deployment

1. **Connect GitHub repository** to Railway
2. **Add environment variables** in Railway dashboard
3. **Deploy automatically** on git push

### Manual Deployment

1. **Set environment variables**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run with Gunicorn**: `gunicorn --config gunicorn.conf.py src.main_production:app`

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

### Code Quality
```bash
# Format code
black src/

# Lint code
flake8 src/
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5000/api/health
```

### Logs
- Application logs: stdout/stderr
- Access logs: Gunicorn access log format
- Error logs: Python logging module

## 🔒 Security

- JWT authentication with role-based access
- Rate limiting (1000 requests/hour per IP)
- CORS configuration for allowed origins
- SQL injection protection via SQLAlchemy ORM
- Password hashing with bcrypt

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://user:pass@host:port/db
```

**Redis Connection Error**
```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping
```

**Import Errors**
```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## 📞 Support

- Check logs for error details
- Verify environment variables
- Ensure database and Redis are accessible
- Review Railway deployment logs

## 🔄 Version History

- **v1.0.0** - Initial production release
  - PostgreSQL integration
  - Redis caching
  - Label Studio API integration
  - JWT authentication
  - Role-based access control

