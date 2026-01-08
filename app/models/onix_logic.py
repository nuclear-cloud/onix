"""
ONIX Business Logic Enums.

Це контроль-енями для логіки.
Всі 148 форматів не потрібні як enum — залишаємо в базі як строка.
Ми тільки маппимо важливі коди в логіку.
"""

from enum import StrEnum
from typing import Optional


# ===== PRODUCT TYPES (Стратегія доставки/вихода) =====

class ProductType(StrEnum):
    """Широкі категорії продуктів для бізнес-логіки."""
    PHYSICAL = "physical"      # Треба доставка, схема: Амазон + курер
    DIGITAL = "digital"        # Посилання на скачування EPUB/PDF
    AUDIO = "audio"            # Аудіокнига з плеєром
    UNKNOWN = "unknown"        # Невідомий тип


class OnixProductForm(StrEnum):
    """
    Тільки найпопулярніші коди ONIX List 150.
    Решту зберігаємо як рядок в CatalogProduct.product_form.
    """
    # Фізичні
    HARDCOVER = "BB"           # Твердопереплет
    PAPERBACK = "BC"           # М'якопереплет
    BOARD_BOOK = "BD"          # Картонна книга (для дітей)
    
    # Цифрові
    EBOOK_EPUB = "EA"          # EPUB
    EBOOK_PDF = "EB"           # PDF
    EBOOK_AMAZON_KINDLE = "EC" # Kindle
    
    # Аудіо
    AUDIO_DOWNLOAD = "AJ"      # Аудіо MP3
    AUDIO_CD = "AG"            # Аудіокнига на CD

    @property
    def broad_type(self) -> ProductType:
        """Маппінг на широку категорію для логіки."""
        if self in (self.HARDCOVER, self.PAPERBACK, self.BOARD_BOOK):
            return ProductType.PHYSICAL
        if self in (self.EBOOK_EPUB, self.EBOOK_PDF, self.EBOOK_AMAZON_KINDLE):
            return ProductType.DIGITAL
        if self in (self.AUDIO_DOWNLOAD, self.AUDIO_CD):
            return ProductType.AUDIO
        return ProductType.PHYSICAL  # Fallback

    @property
    def requires_shipping(self) -> bool:
        """Чи потрібна доставка?"""
        return self.broad_type == ProductType.PHYSICAL

    @property
    def requires_link(self) -> bool:
        """Чи потрібне посилання на завантаження?"""
        return self.broad_type in (ProductType.DIGITAL, ProductType.AUDIO)


# ===== PUBLISHING STATUS (Керує продажами) =====

class PublishingStatusCode(StrEnum):
    """ONIX List 64: Критичні статуси для операцій."""
    CANCELLED = "01"           # Скасовано
    FORTHCOMING = "02"         # Передзамовлення можливе
    ACTIVE = "04"              # АКТИВНИЙ — основний статус продажу
    NO_LONGER_OUR_PRODUCT = "06"  # Більше не продаємо
    OUT_OF_PRINT = "07"        # Архівовано
    INACTIVE = "08"            # Тимчасово недоступно
    UNKNOWN = "99"             # Невідомий

    @property
    def is_buyable(self) -> bool:
        """Можна купити?"""
        return self in (self.ACTIVE, self.FORTHCOMING)

    @property
    def allow_preorder(self) -> bool:
        """Дозволити передзамовлення?"""
        return self == self.FORTHCOMING

    @property
    def is_archived(self) -> bool:
        """Архівна позиція?"""
        return self in (self.OUT_OF_PRINT, self.NO_LONGER_OUR_PRODUCT, self.CANCELLED)


# ===== CONTRIBUTOR ROLES (Сценарії поділу доходу) =====

class KeyContributorRole(StrEnum):
    """ONIX List 17: Основні ролі для видимості в UX."""
    AUTHOR = "A01"
    EDITOR = "B01"
    TRANSLATOR = "B06"
    ILLUSTRATOR = "A12"
    PHOTOGRAPHER = "A13"
    
    @classmethod
    def is_key(cls, onix_code: str) -> bool:
        """Чи це ключова роль?"""
        return onix_code in [role.value for role in cls]


# ===== LANGUAGE (Ніякої логіки, чиста БД) =====
# Використовуємо pycountry або таблицю

class LanguageRole(StrEnum):
    """ONIX List 22: Роль мови в продукті."""
    LANGUAGE_OF_TEXT = "01"
    LANGUAGE_OF_ORIGINAL_TEXT = "02"
    LANGUAGE_OF_ABSTRACT = "03"
    # Інші коди тримаємо як строки в БД


# ===== TITLE TYPE (Варіанти назв) =====

class TitleTypeCode(StrEnum):
    """ONIX List 15: Види назв."""
    DISTINCTIVE_TITLE = "01"   # Основна назва
    ABBREVIATED_TITLE = "03"   # Скорочена
    ALTERNATIVE_TITLE = "02"   # Альтернативна
    EXPANDED_TITLE = "04"      # Розширена


# ===== TEXT CONTENT TYPE (Для блогів/рецензій) =====

class TextContentTypeCode(StrEnum):
    """ONIX List 42: Тип текстового контенту."""
    DESCRIPTION = "03"         # Опис від видавця
    REVIEW_QUOTE = "04"        # Цитата з рецензії
    AUTHOR_BIOGRAPHY = "18"    # Біографія автора
    PROMOTIONAL_TEXT = "08"    # Маркетинговий текст


# ===== DATE ROLES (Хронологія продукту) =====

class PublishingDateRole(StrEnum):
    """ONIX List 163: Події датування."""
    PUBLICATION_DATE = "01"    # Дата видання
    EMBARGO_DATE = "02"        # До якої дати утримувати від продажу
    ANNOUNCEMENT_DATE = "09"   # Анонс
    LAST_DATE_FOR_ORDERS = "19"  # Остання дата замовлення


# ===== MARKET / REGION (Глобальна логіка) =====

class MarketRestriction(StrEnum):
    """Де дозволено/заборонено продавати."""
    UNRESTRICTED = "unrestricted"  # Скрізь
    UKRAINE_ONLY = "ua"            # Лише Україна
    EUROPE_ONLY = "eu"             # Лише Європа
    EXCLUDE_UKRAINE = "exclude_ua"  # Всюди крім України


# ===== HELPERS / MAPPERS =====

def map_onix_form_to_type(onix_form_code: Optional[str]) -> ProductType:
    """
    Конвертує ONIX List 150 код на тип продукту.
    Якщо код невідомий — fallback на PHYSICAL.
    """
    if not onix_form_code:
        return ProductType.UNKNOWN
    
    try:
        form = OnixProductForm(onix_form_code)
        return form.broad_type
    except ValueError:
        # Невідомий код — спробуємо здогадатися за префіксом
        if onix_form_code.startswith("E"):
            return ProductType.DIGITAL
        if onix_form_code.startswith("A"):
            return ProductType.AUDIO
        return ProductType.PHYSICAL  # Fallback


def map_publishing_status(status_code: Optional[str]) -> PublishingStatusCode:
    """
    Безпечна конвертація статусу.
    """
    if not status_code:
        return PublishingStatusCode.UNKNOWN
    
    try:
        return PublishingStatusCode(status_code)
    except ValueError:
        return PublishingStatusCode.UNKNOWN
