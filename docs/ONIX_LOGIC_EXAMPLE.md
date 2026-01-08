"""
Приклад перетворення Catalog Model для використання onix_logic.py
"""

# BEFORE (неправильно):
# catalog_products.product_form = Column(SQLEnum(ProductForm), ...)  # 148 enum values!

# AFTER (правильно):
from sqlalchemy import Column, String
from app.models.onix_logic import ProductType, map_onix_form_to_type, map_publishing_status

# В моделі:
class CatalogProduct:
    product_form = Column(String(5), nullable=False)        # Просто ONIX код "BB", "BC" тощо
    publishing_status = Column(String(2), nullable=True)    # ONIX код "04", "07" тощо
    
    # Властивості для бізнес-логіки:
    @property
    def product_type(self) -> ProductType:
        """Визначить тип на основі ONIX кода."""
        return map_onix_form_to_type(self.product_form)
    
    @property
    def is_buyable(self) -> bool:
        """Чи можна купити?"""
        status = map_publishing_status(self.publishing_status)
        return status.is_buyable
    
    @property
    def requires_shipping(self) -> bool:
        """Чи потрібна доставка?"""
        return self.product_type == ProductType.PHYSICAL


# ===== USAGE В БІЗНЕС-ЛОГІЦІ =====

# Отримати всі фізичні книги:
# books = session.query(CatalogProduct).filter(
#     CatalogProduct.product_form.in_(["BB", "BC", "BD"])  # Hardcover, Paperback, Board
# ).all()

# Показати в UI тільки активні:
# active_books = [p for p in books if p.is_buyable]

# Обраховувати вартість доставки:
# shipping = SHIPPING_RATE if product.requires_shipping else 0

# Передзамовлення:
# if product.publishing_status == "02":
#     show_preorder_button = True
