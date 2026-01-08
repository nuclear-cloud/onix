"""
FastAPI Application Entry Point

ONIX Catalog API with Prisma ORM
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.prisma_db import get_prisma, close_prisma
from app.routers import catalog_router


# ===== Lifecycle Events =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup - Initialize Prisma
    db = await get_prisma()
    print("✅ Prisma connected")
    
    yield
    
    # Shutdown - Close Prisma
    await close_prisma()
    print("🛑 Prisma disconnected")


# ===== Create App =====

app = FastAPI(
    title="ONIX Catalog API",
    description="REST API for book catalog with ONIX metadata (Prisma ORM)",
    version="2.0.0",
    lifespan=lifespan,
)


# ===== CORS =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Include Routers =====

app.include_router(catalog_router, prefix="/api/v1")


# ===== Health Check =====

@app.get("/health", tags=["system"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "orm": "prisma"}


# ===== Root =====

@app.get("/", tags=["system"])
async def root():
    """API information."""
    return {
        "name": "ONIX Catalog API",
        "version": "2.0.0",
        "orm": "Prisma",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global error handling."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
