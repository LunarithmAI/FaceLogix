# FaceLogix

Smart, secure face recognition attendance system built with FastAPI, React, and InsightFace.

## Features

- **Face Recognition Check-in/Check-out** - Fast and accurate attendance tracking using AI
- **Multi-tenant Architecture** - Support for multiple organizations
- **Progressive Web App** - Works on desktop, tablet, and mobile devices
- **Real-time Dashboard** - Live attendance statistics and reports
- **Device Management** - Support for dedicated kiosk devices
- **Liveness Detection** - Anti-spoofing protection
- **CSV Export** - Export attendance reports for payroll integration

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (Python 3.11+) |
| Face Recognition | InsightFace (RetinaFace + ArcFace ONNX models) |
| Frontend | React 19 + TypeScript + Tailwind CSS 4 |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis |
| Deployment | Docker + Docker Compose |

## Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2+
- 8GB+ RAM recommended
- 10GB+ free disk space

### Option A: Full Docker Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/FaceLogix.git
cd FaceLogix

# Copy environment template
cp docker/.env.example docker/.env

# Start all services
docker compose -f docker/docker-compose.dev.yml up -d

# Run database migrations
docker compose -f docker/docker-compose.dev.yml exec backend alembic upgrade head
```

### Option B: Hybrid Development Setup

Best for development with hot reload:

```bash
# Start infrastructure (PostgreSQL + Redis)
docker compose -f docker/docker-compose.infra.yml up -d

# Terminal 1: Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 2: Face Service
cd face_service
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
python download_models.py  # First time only (~500MB)
uvicorn app.main:app --reload --port 8001

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

## Default Credentials

| Field | Value |
|-------|-------|
| Email | `admin@facelogix.local` |
| Password | `admin123` |

> **Warning:** Change default credentials before production deployment!

## Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Face Service | http://localhost:8001 |

## Project Structure

```
FaceLogix/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API endpoints
│   │   ├── core/      # Config, security, database
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   └── alembic/       # Database migrations
├── face_service/      # Face recognition microservice
│   ├── app/
│   │   ├── api/       # Detection/embedding endpoints
│   │   ├── pipeline/  # ML pipeline (detector, aligner, embedder)
│   │   └── models/    # Model loader
│   └── models/        # ONNX model files
├── frontend/          # React PWA
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/  # API clients
│   │   ├── stores/    # Zustand state
│   │   └── hooks/
│   └── public/
├── docker/            # Docker configurations
└── llm_docs/          # Development documentation
```

## API Overview

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user profile

### Attendance
- `POST /api/v1/attendance/check-in` - Check in with face image
- `POST /api/v1/attendance/check-out` - Check out with face image
- `GET /api/v1/attendance` - List attendance logs

### Users (Admin)
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `POST /api/v1/users/{id}/enroll-face` - Enroll face embeddings

### Reports (Admin)
- `GET /api/v1/reports/dashboard` - Dashboard statistics
- `GET /api/v1/reports/attendance/csv` - Export CSV

## Configuration

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql+asyncpg://facelogix:devpassword@localhost:5432/facelogix
REDIS_URL=redis://localhost:6379/0
FACE_SERVICE_URL=http://localhost:8001
JWT_SECRET_KEY=change-this-in-production
DEBUG=true
```

### Face Service (`face_service/.env`)

```env
DEBUG=true
MODELS_DIR=./models
FACE_DETECTION_THRESHOLD=0.5
FACE_RECOGNITION_THRESHOLD=0.75
```

## Documentation

Detailed documentation is available in the `llm_docs/` directory:

- [Project Overview](llm_docs/01_PROJECT_OVERVIEW.md)
- [Database Schema](llm_docs/02_DATABASE_SCHEMA.md)
- [Backend API](llm_docs/03_BACKEND_API.md)
- [Face Recognition Service](llm_docs/04_FACE_RECOGNITION_SERVICE.md)
- [Frontend PWA](llm_docs/05_FRONTEND_PWA.md)
- [Authentication](llm_docs/06_AUTHENTICATION.md)
- [Deployment Guide](llm_docs/DEV_DEPLOYMENT_GUIDE.md)

## Troubleshooting

### Face Service Models Not Found
```bash
cd face_service
python download_models.py
```

### Database Connection Failed
Ensure PostgreSQL container is running:
```bash
docker ps | grep postgres
```

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

For more troubleshooting tips, see the [Deployment Guide](llm_docs/DEV_DEPLOYMENT_GUIDE.md).

## License

MIT License - see [LICENSE](LICENSE) for details.
