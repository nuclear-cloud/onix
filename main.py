"""
FastAPI Application Entry Point
"""
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.prisma_db import prisma
from app.routers import catalog_router


# ===== Structured Logging =====
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


# ===== Config =====
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
VERSION = "1.2.0"
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")


# ===== Rate Limiter =====
limiter = Limiter(key_func=get_remote_address)


# ===== Lifecycle Events =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await prisma.connect()
    logger.info("application_started", database="connected", version=VERSION)
    
    yield
    
    # Shutdown
    await prisma.disconnect()
    logger.info("application_shutdown", database="disconnected")


# ===== Create App =====

app = FastAPI(
    title="ONIX Catalog API",
    description="REST API для каталогу книг з ONIX метаданими",
    version=VERSION,
    lifespan=lifespan,
)


# ===== Rate Limiting =====
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ===== CORS =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Request Logging Middleware =====

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    # Skip logging health checks
    if request.url.path != "/health":
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            client=request.client.host if request.client else "unknown"
        )
    return response


# ===== Include Routers =====

app.include_router(catalog_router, prefix="/api/v1")


# ===== Health Check =====

@app.get("/health", tags=["system"])
async def health_check():
    """Перевірка стану сервісу."""
    try:
        await prisma.query_raw("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


# ===== Root =====

@app.get("/", tags=["system"])
async def root():
    """Інформація про API."""
    return {
        "name": "ONIX Catalog API",
        "version": VERSION,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальна обробка помилок."""
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
