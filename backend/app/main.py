from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.db.base import engine, Base
import app.models  # noqa: F401 - ensure all models are registered on Base.metadata

from app.db.init_db import ensure_initial_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_initial_data()
    yield

app = FastAPI(title="ODIPKS Construction OS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under both /api/v1 (standard) and /api (convenience)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

@app.get("/")
@app.get("/api")
@app.get("/api/")
@app.get("/api/v1")
@app.get("/api/v1/")
async def root():
    return {
        "message": "Welcome to ODIPKS Construction OS API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
    }

@app.get("/health")
@app.get("/health/")
@app.get("/healthz")
@app.get("/healthz/")
@app.get("/api/health")
@app.get("/api/health/")
@app.get("/api/v1/health")
@app.get("/api/v1/health/")
async def health_check():
    return {
        "status": "healthy",
        "service": "ODIPKS Construction OS API",
        "version": "1.0.0",
    }
