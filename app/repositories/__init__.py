"""Data access layer - Prisma ORM repositories."""

from app.repositories.prisma_repositories import (
    PrismaProductRepository,
    PrismaPublisherRepository,
)

__all__ = [
    "PrismaProductRepository",
    "PrismaPublisherRepository",
]
