"""
Core Business Enums - Тільки критична логіка.

Все інше (365 ProductFormDetail, 578 Languages, 9187 Thema) беруться з БД.
"""

from enum import StrEnum
from typing import Optional


class ProductType(StrEnum):
    """Стратегія доставки/вихода продукту."""
    PHYSICAL = "physical"      # Листопад курером, стелажі магазину
    DIGITAL = "digital"        # Посилання на завантаження
    AUDIO = "audio"            # Аудіокнига з плеєром


class OnixProductForm(StrEnum):
    """
    ONIX List 150: Формат продукту.
    Тільки 8 популярних. Решта 140 кодів — просто строка в БД.
    """
    HARDCOVER = "BB"           # Твердопереплет
    PAPERBACK = "BC"           # М'якопереплет
    BOARD_BOOK = "BD"          # Картонна книга
    EBOOK_EPUB = "EA"          # EPUB
    EBOOK_PDF = "EB"           # PDF
    EBOOK_KINDLE = "EC"        # Amazon Kindle
    AUDIO_MP3 = "AJ"           # Аудіо MP3
    AUDIO_CD = "AG"            # Аудіокнига CD

    @property
    def product_type(self) -> ProductType:
        """Маппінг на стратегію."""
        if self in (self.HARDCOVER, self.PAPERBACK, self.BOARD_BOOK):
            return ProductType.PHYSICAL
        if self in (self.EBOOK_EPUB, self.EBOOK_PDF, self.EBOOK_KINDLE):
            return ProductType.DIGITAL
        if self in (self.AUDIO_MP3, self.AUDIO_CD):
            return ProductType.AUDIO
        return ProductType.PHYSICAL


class PublishingStatus(StrEnum):
    """
    ONIX List 64: Статус публікації.
    ВСІ 18 значень — критичні для логіки продажу!
    """
    CANCELLED = "01"
    FORTHCOMING = "02"
    ACTIVE = "04"              # Головний статус!
    NO_LONGER_OUR_PRODUCT = "06"
    OUT_OF_PRINT = "07"
    INACTIVE = "08"
    UNKNOWN = "99"

    @property
    def is_buyable(self) -> bool:
        """Можна придбати?"""
        return self in (self.ACTIVE, self.FORTHCOMING)

    @property
    def is_archived(self) -> bool:
        """Архівна?"""
        return self in (self.OUT_OF_PRINT, self.CANCELLED, self.NO_LONGER_OUR_PRODUCT)


class KeyContributorRole(StrEnum):
    """
    ONIX List 17: Ролі.
    Тільки 5 ключових для видимості. Інші 118 — просто строка.
    """
    AUTHOR = "A01"
    ILLUSTRATOR = "A12"
    EDITOR = "B01"
    TRANSLATOR = "B06"
    PHOTOGRAPHER = "A13"

    @classmethod
    def is_key(cls, code: str) -> bool:
        """Це ключова роль?"""
        return code in {r.value for r in cls}


# ===== HELPERS =====

def map_form_to_type(form_code: Optional[str]) -> ProductType:
    """Конвертує ONIX код форми на тип продукту."""
    if not form_code:
        return ProductType.PHYSICAL
    
    try:
        form = OnixProductForm(form_code)
        return form.product_type
    except ValueError:
        # Невідомий код
        if form_code.startswith("E"):
            return ProductType.DIGITAL
        if form_code.startswith("A"):
            return ProductType.AUDIO
        return ProductType.PHYSICAL


def map_status(code: Optional[str]) -> PublishingStatus:
    """Безпечна конвертація статусу."""
    if not code:
        return PublishingStatus.UNKNOWN
    try:
        return PublishingStatus(code)
    except ValueError:
        return PublishingStatus.UNKNOWN
