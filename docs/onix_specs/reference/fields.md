# ONIX Fields Reference

## Основні поля

### Product Identifiers

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `product_identifier` | Array | ✅ | Масив ідентифікаторів |
| `product_identifier[].type` | String | ✅ | Тип ID (15=ISBN-13, 01=Proprietary) |
| `product_identifier[].value` | String | ✅ | Значення ID |

### Titles

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `titles` | Array | ✅ | Масив назв |
| `titles[].type` | String | ✅ | Тип назви (01=Distinctive, 05=Subtitle) |
| `titles[].text` | String | ✅ | Текст назви |
| `titles[].language` | String | ⚪ | Код мови |

### Contributors

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `contributors` | Array | ✅ | Масив контриб'юторів |
| `contributors[].role` | String | ✅ | Роль (A01=Author, B06=Translator) |
| `contributors[].name` | String | ✅ | Ім'я |
| `contributors[].sequence` | Integer | ⚪ | Порядковий номер |

### Languages

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `languages` | Array | ✅ | Масив мов |
| `languages[].role` | String | ✅ | Роль (01=Language of text) |
| `languages[].code` | String | ✅ | Код мови (ukr, eng) |

### Publishers

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `publishers` | Array | ✅ | Масив видавництв |
| `publishers[].role` | String | ✅ | Роль (01=Publisher) |
| `publishers[].name` | String | ✅ | Назва видавництва |

### Text Content

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `text_content` | Array | ⚪ | Масив текстів |
| `text_content[].type` | String | ✅ | Тип (02=Short desc, 03=Description) |
| `text_content[].text` | String | ✅ | Текст |

### Prices

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `prices` | Array | ⚪ | Масив цін |
| `prices[].type` | String | ✅ | Тип ціни (02=RRP including tax) |
| `prices[].amount` | Float | ✅ | Сума |
| `prices[].currency` | String | ✅ | Валюта (UAH) |

### Measures

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `measures` | Array | ⚪ | Масив вимірів |
| `measures[].type` | String | ✅ | Тип (01=Height, 02=Width, 08=Weight) |
| `measures[].value` | Float | ✅ | Значення |
| `measures[].unit` | String | ✅ | Одиниця (mm, gr) |

### Extents

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `extents` | Array | ⚪ | Масив обсягів |
| `extents[].type` | String | ✅ | Тип (00=Main content page count) |
| `extents[].value` | Integer | ✅ | Значення |
| `extents[].unit` | String | ✅ | Одиниця (03=Pages) |

## Спеціальні поля

### Record Reference

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `record_reference` | String | ✅ | Унікальний ID запису |

### Notification Type

| Поле | Тип | Обов'язкове | Опис |
|------|-----|-------------|------|
| `notification_type` | String | ✅ | Тип повідомлення (03=Confirmed) |

## Додаткові ресурси

- [Code Lists](code_lists.md)
- [Best Practices](best_practices.md)
- [Structure Overview](structure.md)





