"""
Core Models Package.
Exports enums and code mappings. 
ORM models are handled by Prisma (see prisma/schema.prisma).
"""

from app.models.enums import (
    ProductType,
    OnixProductForm,
    PublishingStatus,
    KeyContributorRole,
    map_form_to_type,
    map_status,
)
from app.models.codes_v71 import *

# Use Prisma client for database operations:
# from prisma import Prisma
# from prisma.models import CatalogProduct, etc.
