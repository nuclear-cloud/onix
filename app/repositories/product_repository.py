"""
Repository Layer - Чистий доступ до БД через SQLAlchemy.

Тільки запити, повертає ORM-моделі.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.models import CatalogProduct, CatalogTitle, RefOnixCodelist


class ProductRepository:
    """Все про витягування книг з БД."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[CatalogProduct], int]:
        """
        Отримати всі активні товари з пагінацією.
        
        Returns:
            (список товарів, загальна кількість)
        """
        # Загальна кількість
        count_result = await self.session.execute(
            select(func.count(CatalogProduct.id)).where(
                CatalogProduct.publishing_status.in_(["04", "02"])  # Active or Forthcoming
            )
        )
        total = count_result.scalar()
        
        # Список з пагінацією та eager loading
        result = await self.session.execute(
            select(CatalogProduct)
            .where(
                CatalogProduct.publishing_status.in_(["04", "02"])
            )
            .options(
                selectinload(CatalogProduct.titles),
                selectinload(CatalogProduct.subjects),
                selectinload(CatalogProduct.contributors),
                selectinload(CatalogProduct.extents),
                selectinload(CatalogProduct.measures),
                selectinload(CatalogProduct.languages),
                selectinload(CatalogProduct.text_contents),
                selectinload(CatalogProduct.publishing_dates),
                selectinload(CatalogProduct.publisher),
            )
            .order_by(CatalogProduct.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        products = result.scalars().all()
        
        return products, total
    
    async def get_by_id(self, product_id: str) -> Optional[CatalogProduct]:
        """Отримати товар по ID."""
        result = await self.session.execute(
            select(CatalogProduct)
            .where(CatalogProduct.id == product_id)
            .options(
                selectinload(CatalogProduct.titles),
                selectinload(CatalogProduct.subjects),
                selectinload(CatalogProduct.contributors),
                selectinload(CatalogProduct.extents),
                selectinload(CatalogProduct.measures),
                selectinload(CatalogProduct.languages),
                selectinload(CatalogProduct.text_contents),
                selectinload(CatalogProduct.publishing_dates),
                selectinload(CatalogProduct.publisher),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_isbn(self, isbn: str) -> Optional[CatalogProduct]:
        """Отримати товар по ISBN."""
        result = await self.session.execute(
            select(CatalogProduct)
            .where(CatalogProduct.isbn_13 == isbn)
            .options(
                selectinload(CatalogProduct.titles),
                selectinload(CatalogProduct.subjects),
                selectinload(CatalogProduct.contributors),
                selectinload(CatalogProduct.extents),
                selectinload(CatalogProduct.measures),
                selectinload(CatalogProduct.languages),
                selectinload(CatalogProduct.text_contents),
                selectinload(CatalogProduct.publishing_dates),
                selectinload(CatalogProduct.publisher),
            )
        )
        return result.scalar_one_or_none()
    
    async def search(
        self,
        query: Optional[str] = None,
        thema_code: Optional[str] = None,
        product_form: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[CatalogProduct], int]:
        """
        Пошук товарів з фільтрацією.
        
        Args:
            query: Текстовий пошук (заголовок, автор)
            thema_code: Фільтр по THEMA коду
            product_form: Фільтр по форматі (BB, BC, EA)
            limit: Сторінка
            offset: Зміщення
        
        Returns:
            (список товарів, загальна кількість)
        """
        # Base query
        stmt = select(CatalogProduct).where(
            CatalogProduct.publishing_status.in_(["04", "02"])
        )
        
        # Текстовий пошук
        if query:
            # Пошук в заголовках
            stmt = stmt.join(
                CatalogTitle,
                CatalogProduct.id == CatalogTitle.product_id
            ).where(
                CatalogTitle.title_text.ilike(f"%{query}%")
            )
        
        # Фільтр по THEMA
        if thema_code:
            from app.models import CatalogSubject
            stmt = stmt.join(
                CatalogSubject,
                CatalogProduct.id == CatalogSubject.product_id
            ).where(
                CatalogSubject.subject_code.like(f"{thema_code}%")
            )
        
        # Фільтр по форматі
        if product_form:
            stmt = stmt.where(CatalogProduct.product_form == product_form)
        
        # Eager loading для результатів
        stmt = stmt.options(
            selectinload(CatalogProduct.titles),
            selectinload(CatalogProduct.subjects),
            selectinload(CatalogProduct.contributors),
            selectinload(CatalogProduct.extents),
            selectinload(CatalogProduct.measures),
            selectinload(CatalogProduct.languages),
            selectinload(CatalogProduct.text_contents),
            selectinload(CatalogProduct.publishing_dates),
            selectinload(CatalogProduct.publisher),
        )
        
        # Загальна кількість
        count_stmt = select(func.count(CatalogProduct.id)).select_from(
            stmt.subquery()
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Результати з пагінацією
        stmt = stmt.order_by(CatalogProduct.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        products = result.scalars().all()
        
        return products, total
    
    async def get_onix_label(
        self,
        list_number: int,
        code: str
    ) -> Optional[str]:
        """Витягнути лабель ONIX коду українською."""
        result = await self.session.execute(
            select(RefOnixCodelist).where(
                RefOnixCodelist.list_number == list_number,
                RefOnixCodelist.code == code,
                RefOnixCodelist.is_active == True,
            )
        )
        codelist = result.scalar_one_or_none()
        return codelist.description if codelist else None
