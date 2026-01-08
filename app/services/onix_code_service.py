"""
Сервіс для роботи з ONIX кодами через БД.

Замість Enum на все, ми витягуємо labels з ref_onix_codelists.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import RefOnixCodelist


class OnixCodeService:
    """Глобальний кеш ONIX кодів в пам'яті."""
    
    # Кеш: {list_number: {code: label_uk}}
    _cache = {}
    
    @classmethod
    async def get_label(
        cls,
        session: AsyncSession,
        list_number: int,
        code: str,
        language: str = "uk"
    ) -> Optional[str]:
        """
        Отримати ONIX лабель українською.
        
        Приклад:
            label = await OnixCodeService.get_label(session, 150, "BB")
            # → "Твердопереплет"
        """
        
        # Спробувати кеш
        if list_number in cls._cache and code in cls._cache[list_number]:
            return cls._cache[list_number][code]
        
        # Витягнути з БД
        result = await session.execute(
            select(RefOnixCodelist).where(
                RefOnixCodelist.list_number == list_number,
                RefOnixCodelist.code == code,
            )
        )
        codelist = result.scalar_one_or_none()
        
        if not codelist:
            return None
        
        # Вибрати лабель
        label = getattr(codelist, f"label_{language}", None) or codelist.description
        
        # Закешувати
        if list_number not in cls._cache:
            cls._cache[list_number] = {}
        cls._cache[list_number][code] = label
        
        return label
    
    @classmethod
    async def get_all_for_list(
        cls,
        session: AsyncSession,
        list_number: int,
        language: str = "uk"
    ) -> dict:
        """
        Витягнути всі коди для списку.
        
        Приклад:
            statuses = await OnixCodeService.get_all_for_list(session, 64)
            # → {"04": "Активна", "07": "Розпродана", ...}
        """
        
        # Спробувати кеш
        if list_number in cls._cache:
            return cls._cache[list_number]
        
        # Витягнути з БД
        result = await session.execute(
            select(RefOnixCodelist).where(
                RefOnixCodelist.list_number == list_number,
                RefOnixCodelist.is_active == True,
            )
        )
        codelists = result.scalars().all()
        
        # Побудувати словник
        labels = {}
        for codelist in codelists:
            label = getattr(codelist, f"label_{language}", None) or codelist.description
            labels[codelist.code] = label
        
        # Закешувати
        cls._cache[list_number] = labels
        
        return labels


# ===== ONIX LISTS (для референції) =====

ONIX_LISTS = {
    1: "Notification or update type",
    15: "Title type",
    17: "Contributor role",  # ← KeyContributorRole
    22: "Language role",
    42: "Text content type",
    48: "Measure type",
    50: "Measure unit of length or height",
    64: "Publishing status",  # ← PublishingStatus
    128: "Language code",
    150: "Product form",  # ← OnixProductForm
    163: "Publishing date role",
    175: "Product form detail",  # ← Все інші 365 форматів
}
