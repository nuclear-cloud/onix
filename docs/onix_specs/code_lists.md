# ONIX Code Lists Reference

## Огляд

ONIX використовує стандартизовані списки кодів для різних атрибутів. Повний список доступний в [ONIX Code Lists Issue 71](https://www.editeur.org/files/ONIX%203/ONIX_BookProduct_Codelists_Issue_71.xml).

## Найважливіші списки

### List 15: Title Types (Типи назв)

- **01** - Distinctive title (book title as it appears on the cover)
- **03** - Original title
- **05** - Translated title
- **06** - Title in original language

### List 17: Contributor Roles (Ролі контриб'юторів)

- **A01** - Author (Автор)
- **A03** - Text author
- **A06** - By (author)
- **A12** - Illustrated by (Ілюстратор)
- **B01** - Edited by (Редактор)
- **B06** - Translated by (Перекладач)
- **B20** - Preface by
- **B21** - Prologue by
- **B22** - Afterword by

### List 23: Extent Types (Типи обсягу)

- **00** - Main content page count (Кількість сторінок основного тексту)
- **02** - Total numbered pages
- **03** - Production page count
- **04** - Absolute page count

### List 24: Extent Units (Одиниці обсягу)

- **03** - Pages (Сторінки)
- **04** - Words
- **05** - Characters

### List 27: Subject Scheme Identifiers (Схеми тематики)

- **10** - BISAC Subject Heading
- **12** - BIC subject category
- **20** - Keywords
- **24** - Thema subject category
- **79** - ONIX Books audience code

### List 48: Measure Types (Типи вимірів)

- **01** - Height (Висота)
- **02** - Width (Ширина)
- **03** - Thickness (Товщина)
- **08** - Weight (Вага)

### List 50: Measure Units (Одиниці виміру)

- **mm** - Millimeters (Міліметри)
- **cm** - Centimeters
- **gr** - Grams (Грами)
- **kg** - Kilograms

### List 58: Price Types (Типи цін)

- **01** - RRP excluding tax (Рекомендована роздрібна ціна без ПДВ)
- **02** - RRP including tax (Рекомендована роздрібна ціна з ПДВ)
- **05** - Publisher's retail price excluding tax
- **42** - Retail price excluding tax

### List 62: Tax Rate Types (Типи податків)

- **S** - Standard rate (Стандартна ставка)
- **Z** - Zero rated
- **E** - Exempt from tax

### List 65: Product Availability (Наявність продукту)

- **20** - Available (В наявності)
- **21** - Not available (Немає в наявності)
- **22** - Not yet available (Ще не доступно)
- **23** - Withdrawn (Знято з продажу)

### List 96: Currency Codes (Коди валют)

- **UAH** - Ukrainian Hryvnia (Українська гривня)
- **USD** - US Dollar
- **EUR** - Euro
- **GBP** - British Pound

### List 153: Text Content Types (Типи текстового контенту)

- **01** - Text on back cover
- **02** - Short description/annotation (Короткий опис)
- **03** - Description (Опис)
- **04** - Table of contents (Зміст)
- **10** - Review quote (Цитата з рецензії)
- **11** - Review text
- **12** - Promotional headline

### List 158: Resource Content Types (Типи ресурсів)

- **01** - Front cover (Обкладинка)
- **02** - Back cover
- **03** - Cover / pack
- **04** - Contributor picture
- **11** - Video

### List 159: Resource Modes (Режими ресурсів)

- **03** - Image (Зображення)
- **04** - Audio
- **05** - Video

## Використання в коді

У нашому проекті коди зберігаються в `app/scraper/yakaboo/codelists.py`:

```python
# Приклад маппінгу
BINDING_TO_ONIX = {
    "тверда": "BC",
    "м'яка": "BB",
    # ...
}

LANG_TO_ONIX = {
    "українська": "ukr",
    "англійська": "eng",
    # ...
}
```

## Повний список кодів

Повний список всіх кодів ONIX доступний в файлі:
`data/ONIX_BookProduct_Codelists_Issue_71.json`

## Додаткові ресурси

- [ONIX Code Lists Issue 71 (XML)](https://www.editeur.org/files/ONIX%203/ONIX_BookProduct_Codelists_Issue_71.xml)
- [Structure Overview](structure.md)
- [Best Practices](best_practices.md)





