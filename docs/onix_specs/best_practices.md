# ONIX 3.0/3.1 Best Practices

## Загальні принципи

### 1. Якість даних

- ✅ Використовуйте повні та точні дані
- ✅ Перевіряйте правильність ISBN
- ✅ Забезпечуйте консистентність даних
- ✅ Використовуйте стандартні коди ONIX

### 2. Обов'язкові поля

Мінімальний набір для валідного запису:
- `record_reference` - унікальний ID
- `notification_type` - тип повідомлення
- `product_identifier` - принаймні ISBN-13
- `titles` - принаймні основна назва
- `contributors` - принаймні один автор
- `languages` - мова тексту
- `publishers` - видавництво

### 3. Notification Types

**03** (Notification confirmed on publication) - використовуйте для:
- Підтверджених даних про опубліковану книгу
- Оновлень існуючих записів
- Найпоширеніший тип

**04** (Update partial) - для:
- Оновлення окремих блоків даних
- Не потребує повного запису

## Рекомендації по полях

### Product Identifiers

```json
{
  "product_identifier": [
    {"type": "15", "value": "9781234567890"},  // ISBN-13 (обов'язково)
    {"type": "01", "value": "internal_id"}      // Внутрішній ID (опціонально)
  ]
}
```

### Titles

```json
{
  "titles": [
    {"type": "01", "text": "Основна назва", "language": "ukr"},
    {"type": "05", "text": "Підзаголовок", "language": "ukr"},
    {"type": "03", "text": "Original Title", "language": "eng"}
  ]
}
```

### Contributors

```json
{
  "contributors": [
    {"role": "A01", "name": "Автор", "sequence": 1},
    {"role": "B06", "name": "Перекладач", "sequence": 2},
    {"role": "A12", "name": "Ілюстратор", "sequence": 3}
  ]
}
```

### Languages

```json
{
  "languages": [
    {"role": "01", "code": "ukr"}  // Мова тексту
  ]
}
```

### Text Content

```json
{
  "text_content": [
    {"type": "03", "text": "Повний опис книги"},
    {"type": "02", "text": "Короткий опис"},
    {"type": "04", "text": "Зміст"}
  ]
}
```

## Типові помилки

### ❌ Неправильно

```json
{
  "product_identifier": [{"type": "15", "value": "978-123-456-789-0"}],  // ISBN з дефісами
  "titles": [{"text": "Назва"}],  // Без типу
  "contributors": [{"name": "Автор"}]  // Без ролі
}
```

### ✅ Правильно

```json
{
  "product_identifier": [{"type": "15", "value": "9781234567890"}],  // ISBN без дефісів
  "titles": [{"type": "01", "text": "Назва"}],
  "contributors": [{"role": "A01", "name": "Автор"}]
}
```

## Рекомендації для українського ринку

1. **Мова**: Завжди вказуйте `language: "ukr"` для українських книжок
2. **Видавництва**: Використовуйте повні назви видавництв
3. **Ціни**: Вказуйте ціни в UAH (гривня)
4. **ISBN**: Перевіряйте правильність ISBN-13 перед збереженням

## Додаткові ресурси

- [ONIX Structure](structure.md)
- [Code Lists](code_lists.md)
- [Field Reference](reference/fields.md)





