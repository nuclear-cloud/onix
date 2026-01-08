"""
Schemas/DTOs package.
"""

from app.schemas.catalog_dto import (
    PriceDTO,
    ContributorDTO,
    TitleDTO,
    SubjectDTO,
    ProductCardDTO,
    ProductDetailDTO,
    PriceDetailDTO,
    CatalogSearchRequestDTO,
    CatalogSearchResponseDTO,
    ErrorDTO,
)

# Import adapters DTOs
from app.schemas.product_full import ProductFullDTO, ProductCreateDTO
from app.schemas.product_market import (
    ProductMarketDTO,
    ProductPriceUpdateDTO,
    MarketUpdateResult,
)

__all__ = [
    # Catalog DTOs
    "PriceDTO",
    "ContributorDTO",
    "TitleDTO",
    "SubjectDTO",
    "ProductCardDTO",
    "ProductDetailDTO",
    "PriceDetailDTO",
    "CatalogSearchRequestDTO",
    "CatalogSearchResponseDTO",
    "ErrorDTO",
    # Adapter DTOs
    "ProductFullDTO",
    "ProductCreateDTO",
    "ProductMarketDTO",
    "ProductPriceUpdateDTO",
    "MarketUpdateResult",
]
