# Sets and Series in ONIX 3.0/3.1

## Огляд

ONIX 3.0/3.1 надає гнучкі можливості для опису наборів книг та серій.

## Collections (Колекції/Серії)

### Структура

```json
{
  "collections": [
    {
      "type": "10",
      "title": "Назва серії",
      "number": "1",
      "issn": "1234-5678"
    }
  ]
}
```

### Типи колекцій (List 148)

- **10** - Publisher collection (Видавнича серія) ⭐ Найпоширеніший
- **11** - Collection edited by
- **20** - Ascribed collection

### Нумерація

```json
{
  "collections": [
    {
      "type": "10",
      "title": "Серія книг",
      "number": "3",
      "number_type": "01"  // 01=Sequence number
    }
  ]
}
```

## Sets (Набори)

### Product Form для наборів

- **00** - Undefined
- **BA** - Hardback
- **BB** - Paperback
- **BC** - Hardback (підходить для наборів)

### Опис набору

```json
{
  "product_form": "BC",
  "product_packaging": "00",  // 00=No outer packaging
  "number_of_pieces": 3,
  "trade_category": "01"  // 01=Book
}
```

## Best Practices

1. ✅ Використовуйте тип "10" для видавничих серій
2. ✅ Вказуйте номер в серії якщо відомий
3. ✅ Використовуйте ISSN для серій якщо є
4. ✅ Для наборів вказуйте кількість книг

## Приклади

### Проста серія

```json
{
  "collections": [
    {
      "type": "10",
      "title": "Українська класика"
    }
  ]
}
```

### Серія з номером

```json
{
  "collections": [
    {
      "type": "10",
      "title": "Пригоди",
      "number": "5",
      "number_type": "01"
    }
  ]
}
```

### Набір книг

```json
{
  "product_form": "BC",
  "number_of_pieces": 3,
  "collections": [
    {
      "type": "10",
      "title": "Трилогія"
    }
  ]
}
```





