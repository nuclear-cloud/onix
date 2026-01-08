"""Core application modules - Prisma ORM."""

from app.core.prisma_db import get_prisma, close_prisma, get_db

__all__ = ["get_prisma", "close_prisma", "get_db"]
