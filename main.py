"""
FastAPI Application Entry Point

Основний app з інтеграцією всіх шарів.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import engine, Base
from app.routers import catalog_router


# ===== Lifecycle Events =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управління життєвим циклом додатку."""
    # Startup
    async with engine.begin() as conn:
        # При потребі можна виконати міграції тут
        pass
    
    print("✅ Application started")
    
    yield
    
    # Shutdown
    print("🛑 Application shutdown")


# ===== Create App =====

app = FastAPI(
    title="ONIX Catalog API",
    description="REST API для каталогу книг з ONIX метаданими",
    version="1.0.0",
    lifespan=lifespan,
)


# ===== CORS =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Замінити на конкретні домени в production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Include Routers =====

app.include_router(catalog_router, prefix="/api/v1")


# ===== Health Check =====

@app.get("/health", tags=["system"])
async def health_check():
    """Перевірка стану сервісу."""
    return {"status": "ok"}


# ===== Root =====

@app.get("/", tags=["system"])
async def root():
    """Інформація про API."""
    return {
        "name": "ONIX Catalog API",
        "version": "1.0.0",
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
