"""
Prisma Database Connection Manager.

Replaces SQLAlchemy AsyncSession with Prisma async client.
"""

from prisma import Prisma
from app.core.config import settings

# Global Prisma instance
_prisma_instance: Prisma | None = None


async def get_prisma() -> Prisma:
    """Get or initialize Prisma client."""
    global _prisma_instance
    
    if _prisma_instance is None:
        _prisma_instance = Prisma()
        await _prisma_instance.connect()
    
    return _prisma_instance


async def close_prisma():
    """Close Prisma connection."""
    global _prisma_instance
    
    if _prisma_instance is not None:
        await _prisma_instance.disconnect()
        _prisma_instance = None


# Dependency injection for FastAPI
async def get_db() -> Prisma:
    """FastAPI dependency for Prisma client."""
    return await get_prisma()
