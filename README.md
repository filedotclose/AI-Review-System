# AI-Review-System

An AI-powered operational review and construction management system designed to track daily progress reports (DPR), fuel logistics, worker attendance, petty cash disbursements, and generate automated executive briefs with anomaly detection.

## Architecture

- **Backend**: FastAPI, SQLAlchemy (Async), Celery, Pydantic, Alembic
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, Service Workers (Offline PWA)
- **Services**: Docker Compose (FastAPI, Celery Worker, Celery Beat, Redis, MinIO)

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### Local Development

1. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```

2. **Run Services with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Run Backend Manually:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

4. **Run Frontend Manually:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
