"""
Як оновити CatalogProduct модель.

БУЛО (неправильно):
    product_form = Column(SQLEnum(ProductForm), ...)  # 148 enum!

БУДЕ (правильно):
    product_form = Column(String(5), ...)  # Просто ONIX код
    
    @property
    async def product_type(self) -> ProductType:
        from app.models.enums import map_form_to_type
        return map_form_to_type(self.product_form)
    
    async def get_form_label(self, session) -> str:
        from app.services.onix_code_service import OnixCodeService
        label = await OnixCodeService.get_label(session, 150, self.product_form)
        return label or self.product_form
"""

# ПРИКЛАД 1: Отримати тип продукту для UI
async def show_product_card(session, product):
    """Показати картку продукту."""
    from app.models.enums import map_form_to_type, PublishingStatus
    from app.services.onix_code_service import OnixCodeService
    
    product_type = map_form_to_type(product.product_form)
    form_label = await OnixCodeService.get_label(session, 150, product.product_form)
    status = PublishingStatus(product.publishing_status)
    
    return {
        "title": product.titles[0].title_text if product.titles else "—",
        "type": product_type,  # "physical" | "digital" | "audio"
        "format": form_label,  # "Твердопереплет", "PDF" тощо
        "is_buyable": status.is_buyable,  # True/False
        "is_archived": status.is_archived,  # True/False
    }


# ПРИКЛАД 2: Фільтрація в базі (без enum!)
async def get_active_physical_books(session):
    """Отримати активні фізичні книги."""
    from sqlalchemy import select
    from app.models import CatalogProduct
    
    # Обійтись без enum в WHERE
    query = select(CatalogProduct).where(
        CatalogProduct.product_form.in_(["BB", "BC", "BD"]),  # Тільки ONIX коди
        CatalogProduct.publishing_status.in_(["04", "02"]),   # Активна чи передзамовлення
    )
    result = await session.execute(query)
    return result.scalars().all()


# ПРИКЛАД 3: API endpoint
async def get_product_details(session, product_id: str):
    """REST API: GET /products/{id}"""
    from sqlalchemy import select
    from app.models import CatalogProduct, PublishingStatus, map_form_to_type
    from app.services.onix_code_service import OnixCodeService
    
    product = await session.get(CatalogProduct, product_id)
    if not product:
        return None
    
    return {
        "id": str(product.id),
        "isbn": product.isbn_13,
        "title": product.titles[0].title_text if product.titles else "—",
        "description": (product.text_contents[0].text if product.text_contents else ""),
        
        # Логіка через Enum
        "product_type": map_form_to_type(product.product_form),  # "physical" | "digital"
        "is_available": PublishingStatus(product.publishing_status).is_buyable,
        
        # Лабелі з БД
        "format_label": await OnixCodeService.get_label(session, 150, product.product_form),
        "status_label": await OnixCodeService.get_label(session, 64, product.publishing_status),
        
        # Автори
        "authors": [
            {
                "name": link.contributor.name,
                "role": link.role,
                "role_label": await OnixCodeService.get_label(session, 17, link.role),
            }
            for link in product.contributors
        ],
    }
