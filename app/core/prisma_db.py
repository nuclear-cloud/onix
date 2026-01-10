"""
Prisma Database Connection Manager.
"""

from prisma import Prisma

# Global Prisma client instance
prisma = Prisma()


async def get_db() -> Prisma:
    """FastAPI dependency for Prisma client."""
    if not prisma.is_connected():
        await prisma.connect()
    return prisma
