from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router.router import api_router
from app.core.database import Base, engine
import app.models.usersModel  # 1. Import model so SQLAlchemy detects the table schema

# 2. Trigger table creation in PostgreSQL
Base.metadata.create_all(bind=engine)

# --------------------------------------------------
# Application
# --------------------------------------------------

app = FastAPI(
    title="AgriAI API",
    description="Intelligent agricultural assistant and smart farm management API",
    version="0.1.0",
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# API Routes
# --------------------------------------------------

app.include_router(
    api_router,
    prefix="/api",
)


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "AgriAI API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
    }