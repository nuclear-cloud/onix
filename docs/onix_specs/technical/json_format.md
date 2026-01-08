# ONIX JSON Format

## Огляд

Хоча ONIX традиційно використовує XML формат, JSON представлення стає все більш популярним завдяки простоті використання в сучасних додатках.

## Перетворення XML → JSON

### Основні правила

1. **Елементи** стають **полями об'єкта**
2. **Атрибути** стають **полями в об'єкті**
3. **Повторювані елементи** стають **масивами**
4. **Текстовий контент** стає **значенням поля**

### Приклад перетворення

#### XML
```xml
<Product>
  <RecordReference>book_123</RecordReference>
  <NotificationType>03</NotificationType>
  <ProductIdentifier>
    <ProductIDType>15</ProductIDType>
    <IDValue>9781234567890</IDValue>
  </ProductIdentifier>
  <Title>
    <TitleType>01</TitleType>
    <TitleText>Назва книги</TitleText>
  </Title>
</Product>
```

#### JSON
```json
{
  "record_reference": "book_123",
  "notification_type": "03",
  "product_identifier": [
    {
      "type": "15",
      "value": "9781234567890"
    }
  ],
  "titles": [
    {
      "type": "01",
      "text": "Назва книги"
    }
  ]
}
```

## Конвенції назв

### Snake_case

У JSON використовується snake_case для полів:
- `record_reference` (замість `RecordReference`)
- `product_identifier` (замість `ProductIdentifier`)
- `notification_type` (замість `NotificationType`)

### Масиви

Повторювані елементи завжди масиви:
- `titles` - масив назв
- `contributors` - масив контриб'юторів
- `prices` - масив цін

## Структура в нашому проекті

### ONIX+ Format

Ми використовуємо розширений формат ONIX+:

```json
{
  // Стандартні ONIX поля
  "record_reference": "...",
  "notification_type": "03",
  "product_identifier": [...],
  "titles": [...],
  
  // Додаткові дані
  "extra": {
    "source_format": "yakaboo",
    "source_id": "12345",
    "processed_at": "2025-01-01T12:00:00"
  }
}
```

## Переваги JSON

1. ✅ Простіший для парсингу
2. ✅ Нативна підтримка в PostgreSQL (JSONB)
3. ✅ Легше працювати в коді
4. ✅ Менший розмір ніж XML
5. ✅ Краща підтримка в сучасних мовах програмування

## Валідація

### JSON Schema

Можна створити JSON Schema для валідації:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["record_reference", "notification_type"],
  "properties": {
    "record_reference": {"type": "string"},
    "notification_type": {"type": "string"},
    "product_identifier": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "value"]
      }
    }
  }
}
```

## Конвертація назад в XML

При необхідності можна конвертувати JSON назад в XML для сумісності з системами, що використовують XML.

## Додаткові ресурси

- [Structure Overview](../structure.md)
- [Best Practices](../best_practices.md)
- [Field Reference](../reference/fields.md)





