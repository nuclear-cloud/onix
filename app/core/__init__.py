"""Core application modules - Prisma ORM."""

from app.core.prisma_db import prisma, get_db

__all__ = ["prisma", "get_db"]
