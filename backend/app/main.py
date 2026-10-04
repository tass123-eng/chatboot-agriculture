from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router


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