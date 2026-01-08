# Структура ONIX 3.0/3.1

## Огляд

ONIX (Online Information Exchange) - це XML-формат для обміну метаданими про книги між видавцями, дистриб'юторами, книгарнями та іншими учасниками книжкового ринку.

## Основні компоненти

### 1. ONIX Message (Повідомлення)

Повідомлення ONIX складається з двох основних частин:

```
<ONIXMessage>
  <Header>...</Header>      <!-- Заголовок повідомлення -->
  <Product>...</Product>    <!-- Дані про продукт (може бути багато) -->
  <Product>...</Product>
  ...
</ONIXMessage>
```

### 2. Header (Заголовок)

Містить метадані про саме повідомлення:

- **Sender** - відправник даних
- **Addressee** - одержувач (опціонально)
- **MessageNumber** - номер повідомлення
- **SentDateTime** - дата та час відправки
- **MessageNote** - примітки до повідомлення
- **DefaultLanguageOfText** - мова за замовчуванням
- **DefaultPriceType** - тип ціни за замовчуванням
- **DefaultCurrencyCode** - валюта за замовчуванням

### 3. Product (Продукт)

Основна частина, що містить метадані про книгу. Структура складається з блоків:

#### Блок 1: Product Identifiers (Ідентифікатори)
- ISBN-13, ISBN-10
- EAN/UPC
- Proprietary identifiers
- DOI

#### Блок 2: Descriptive Detail (Опис)
- **Titles** - назви книги
- **Contributors** - автори, перекладачі, ілюстратори
- **Languages** - мови тексту
- **Subjects** - тематика, категорії
- **Audience** - цільова аудиторія
- **Text Content** - описи, анотації
- **Supporting Resources** - зображення, відео

#### Блок 3: Collateral Detail (Додаткові матеріали)
- **Text Content** - додаткові тексти
- **Supporting Resources** - додаткові ресурси
- **Cited Content** - цитування

#### Блок 4: Content Detail (Деталі контенту)
- **Extent** - обсяг (кількість сторінок)
- **Illustrations** - ілюстрації
- **Audience** - деталі аудиторії
- **Audience Range** - вікові діапазони

#### Блок 5: Publishing Detail (Деталі видавництва)
- **Publishers** - видавництва
- **Imprints** - імпринти
- **PublishingDates** - дати публікації
- **PublishingStatus** - статус публікації
- **PublishingStatusNote** - примітки до статусу

#### Блок 6: Related Material (Пов'язані матеріали)
- **RelatedProducts** - пов'язані продукти
- **RelatedWorks** - пов'язані твори

#### Блок 7: Product Supply (Постачання)
- **SupplyDetail** - деталі постачання
- **Price** - ціни
- **Supplier** - постачальники
- **Stock** - наявність на складі
- **Packaging** - упаковка

#### Блок 8: Promotion (Промоція)
- **PromotionDetail** - деталі промоції
- **PromotionCampaign** - кампанії

## JSON представлення

У нашому проекті використовується JSON-представлення ONIX:

```json
{
  "record_reference": "unique_id",
  "notification_type": "03",
  "product_identifier": [...],
  "titles": [...],
  "contributors": [...],
  "languages": [...],
  "subjects": [...],
  "text_content": [...],
  "supporting_resources": [...],
  "extents": [...],
  "measures": [...],
  "publishers": [...],
  "publishing_dates": [...],
  "prices": [...],
  "supply_detail": {...}
}
```

## Notification Types (Типи повідомлень)

- **01** - Early notification (раннє повідомлення)
- **02** - Advance notification (попереднє повідомлення)
- **03** - Notification confirmed on publication (підтверджено при публікації)
- **04** - Update (partial) (часткове оновлення)
- **05** - Delete (видалення)

## Важливі концепції

### 1. Обов'язкові поля

Мінімальний набір полів для валідного ONIX:
- `record_reference` - унікальний ідентифікатор запису
- `notification_type` - тип повідомлення
- Принаймні один `product_identifier` (найкраще ISBN-13)
- Принаймні один `title`
- Принаймні один `contributor` (автор)

### 2. Повторювані елементи

Багато елементів можуть повторюватися:
- Кілька назв (основна, підзаголовок, оригінальна)
- Кілька авторів
- Кілька мов
- Кілька цін (для різних регіонів)

### 3. Коди та списки

ONIX використовує стандартизовані коди:
- **List 15** - Типи назв
- **List 17** - Ролі контриб'юторів
- **List 23** - Типи обсягу
- **List 48** - Типи вимірів
- **List 58** - Типи цін
- **List 65** - Статуси наявності

Повний список кодів дивіться в [Code Lists Reference](code_lists.md).

## Приклад мінімального запису

```json
{
  "record_reference": "book_12345",
  "notification_type": "03",
  "product_identifier": [
    {"type": "15", "value": "9781234567890"}
  ],
  "titles": [
    {"type": "01", "text": "Назва книги"}
  ],
  "contributors": [
    {"role": "A01", "name": "Ім'я Автора"}
  ],
  "languages": [
    {"role": "01", "code": "ukr"}
  ],
  "publishers": [
    {"role": "01", "name": "Видавництво"}
  ]
}
```

## Додаткові ресурси

- [ONIX 3.1.2 Specification](specification.md)
- [Best Practices](best_practices.md)
- [Field Reference](reference/fields.md)





