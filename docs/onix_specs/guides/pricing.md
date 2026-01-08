# Pricing in ONIX 3.0/3.1

## Огляд

ONIX підтримує складні схеми ціноутворення з підтримкою різних валют, регіонів та типів цін.

## Структура ціни

```json
{
  "prices": [
    {
      "type": "02",
      "amount": 299.00,
      "currency": "UAH",
      "tax_included": true,
      "tax_rate": 20.0
    }
  ]
}
```

## Типи цін (List 58)

- **01** - RRP excluding tax (Рекомендована роздрібна ціна без ПДВ)
- **02** - RRP including tax (Рекомендована роздрібна ціна з ПДВ) ⭐ Найпоширеніший
- **05** - Publisher's retail price excluding tax
- **42** - Retail price excluding tax

## Валюта (List 96)

Для України використовуйте:
- **UAH** - Ukrainian Hryvnia

## Податки

### Типи податків (List 62)

- **S** - Standard rate (Стандартна ставка, зазвичай 20% в Україні)
- **Z** - Zero rated
- **E** - Exempt from tax

### Приклад з податком

```json
{
  "prices": [
    {
      "type": "02",
      "amount": 299.00,
      "currency": "UAH",
      "tax_included": true,
      "tax_rate_code": "S",
      "tax_rate_percent": 20.0
    }
  ]
}
```

## Регіональні ціни

Можна вказати різні ціни для різних регіонів:

```json
{
  "prices": [
    {
      "type": "02",
      "amount": 299.00,
      "currency": "UAH",
      "territory": "UA"
    },
    {
      "type": "02",
      "amount": 9.99,
      "currency": "USD",
      "territory": "US"
    }
  ]
}
```

## Best Practices

1. ✅ Завжди вказуйте валюту
2. ✅ Використовуйте тип "02" для роздрібних цін з ПДВ
3. ✅ Вказуйте податок явно
4. ✅ Оновлюйте ціни при змінах

## Приклади

### Мінімальна ціна

```json
{
  "prices": [
    {
      "type": "02",
      "amount": 299.00,
      "currency": "UAH"
    }
  ]
}
```

### Повна ціна з податком

```json
{
  "prices": [
    {
      "type": "02",
      "amount": 299.00,
      "currency": "UAH",
      "tax_included": true,
      "tax_rate_code": "S",
      "tax_rate_percent": 20.0,
      "territory": "UA"
    }
  ]
}
```





