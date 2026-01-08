"""
Архітектурні правила: Enum vs Data
Для запобігання  кодбейсу
"""

## 🎯 ПРАВИЛО 1: Enum тільки для критичної логіки

### ❌ НЕПРАВИЛЬНО:
```python
class ProductFormDetail(Enum):
    # 365 значень!
    WITH_DUST_JACKET = "01"
    LAMINATED_COVER = "02"
    EMBOSSED_COVER = "03"
    ... # ще 362 значення
```
Навіщо? Це просто текст для відображення. Немає логіки!

### ✅ ПРАВИЛЬНО:
```python
# У БД:
catalog_products.product_form_detail = Column(String(10))  # Просто текст "01", "02"...

# Якщо потрібна логіка:
@property
def display_name(self) -> str:
    # Маппінг на лабель з БД ref_onix_codelists
    label = session.query(RefOnixCodelist).filter_by(
        list_number=175, 
        code=self.product_form_detail
    ).first()
    return label.label_uk if label else "Невідомо"
```

---

## 🎯 ПРАВИЛО 2: Enum для 3-20 значень (критичних для логіки)

### ✅ ENUM (правильно):
```python
class PublishingStatus(StrEnum):
    ACTIVE = "04"        # ← Логіка: кнопка "Купити"
    FORTHCOMING = "02"   # ← Логіка: кнопка "Передзамовити"
    OUT_OF_PRINT = "07"  # ← Логіка: повідомлення "Невже"
    ARCHIVED = "08"      # ← Логіка: приховати зі списку
```
Всі 18 статусів ONIX мають логічне значення!

### 🗄️ DATABASE (правильно):
```python
class Language(StrEnum):
    # Не робіть enum для 578 мов!
    # Замість цього: таблиця ref_languages
    pass

# У моделі:
language_code = Column(String(3))  # "uk", "en", "de"...
```

---

## 🎯 ПРАВИЛО 3: Маппінг для великих наборів

### ✅ SMART ENUM + MAPPING:
```python
class OnixProductForm(StrEnum):
    """Тільки 8 популярних форматів"""
    HARDCOVER = "BB"
    PAPERBACK = "BC"
    EBOOK_EPUB = "EA"
    # ... ще 5

    @property
    def is_physical(self) -> bool:
        """Логіка: потрібна ли доставка?"""
        return self in (self.HARDCOVER, self.PAPERBACK)

# Для всіх інших 140 кодів:
# CatalogProduct.product_form = Column(String(5))  # Просто зберігаємо ONIX код
```

---

## 📊 ВЕРДИКТ ПО ТАБЛИЦІ

| Список | К-сть | Enum? | Причина | Де зберігати |
|--------|-------|-------|---------|------|
| ProductForm | 148 | 🟡 Часткове | Популярні (8) у коді, Решта — БД | Column(String) + Enum(8) |
| ProductFormDetail | 365 | 🔴 НІ | Це просто текст для UI | ref_onix_codelists |
| PublishingStatus | 18 | 🟢 ДА | Критично для логіки продажу | Column(Enum) |
| ContributorRole | 123 | 🟡 Часткове | Важливі (4): A01, B06, A12 | Column(String) + Enum(4) |
| Language | 578 | 🔴 НІ | Використайте pycountry | pycountry |
| Region | ~250 | 🔴 НІ | ISO 3166 | pycountry |
| Thema | ~9187 | 🔴 НІ | Ієрархія в БД | ref_thema_subjects |

---

## ⚙️ РЕКОМЕНДОВАНА АРХІТЕКТУРА

```
/app/models/
├── onix_logic.py           ← Критичні Enum (публично API)
│   ├── ProductType         ← 3 значення
│   ├── PublishingStatusCode ← 7 значень
│   ├── KeyContributorRole  ← 5 значень
│   └── map_onix_form_to_type() ← Маппінг 148 -> 3
│
├── codes_v71.py            ← Reference Enum (для генерації БД)
│   └── Всі 193 enum (не використовуються в бізнес-логіці!)
│
└── catalog.py              ← Models
    ├── CatalogProduct(product_form = Column(String))
    ├── @property product_type → map_onix_form_to_type()
    └── @property is_buyable → map_publishing_status()

/scripts/
├── load_reference_codes.py ← INSERT в ref_onix_codelists
└── ... (сидячі дані)
```

---

## 💡 ГОЛОВНА ІДЕЯ

> **Enum в коді — тільки для логіки, що отримує питання "Як це впливає на користувача?"**
> **Всі коди ONIX живуть у таблицях, які отримуються через JOIN.**

Приклад:
```sql
-- У коді:
if product.is_buyable:
    show_button("Купити")

-- У БД:
SELECT ... FROM catalog_products
WHERE publishing_status IN ('04', '02')  # ACTIVE або FORTHCOMING
```

---

## 🚀 ПЕРЕМІГРАЦІЯ

1. **Зберегти** codes_v71.py як генеровану еталон
2. **Створити** onix_logic.py з критичними Enum (готово ✅)
3. **Оновити** CatalogProduct моделі (колона String замість Enum)
4. **Додати** @property для маппінгу
5. **Видалити** Enum з catalog.py (LineType 108-135 в app/models/catalog.py)
6. **Мігрувати** коди в БД за ONIX list (готово через ref_onix_codelists ✅)

---

**Версія**: 1.0  
**Дата**: 2026-01-06
