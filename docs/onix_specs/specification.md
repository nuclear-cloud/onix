# ONIX 3.1.2 Specification Summary

## Офіційна специфікація

**Версія:** ONIX for Books 3.1.2  
**Дата випуску:** Березень 2023  
**Оновлено для:** Code Lists Issue 71

**Джерело:** [EDItEUR ONIX 3.1.2 Specification](https://www.editeur.org/files/ONIX%203/ONIX%20for%20Books%20-%20Format%20Specification%20-%203.1.2.pdf)

## Основні зміни в 3.1.2

### Зміни з 3.1.1 до 3.1.2

- Оновлення Code Lists до Issue 71
- Виправлення помилок та уточнення

### Зміни з 3.0.8 до 3.1

Основні нововведення:
- Покращена підтримка цифрових продуктів
- Розширені можливості для опису серій
- Покращена підтримка багатомовних метаданих
- Нові типи контенту та ресурсів

## Структура специфікації

### Частина 1: Header

Містить метадані про повідомлення:
- Відправник та одержувач
- Дата та час відправки
- Налаштування за замовчуванням

### Частина 2: Product Record

Основна частина з метаданими про продукт, організована в блоки:

1. **Product Identifiers** - ідентифікатори
2. **Descriptive Detail** - опис
3. **Collateral Detail** - додаткові матеріали
4. **Content Detail** - деталі контенту
5. **Publishing Detail** - деталі видавництва
6. **Related Material** - пов'язані матеріали
7. **Product Supply** - постачання
8. **Promotion** - промоція

## Формати

ONIX підтримує три формати:

1. **XML** - стандартний формат
2. **JSON** - альтернативний формат (використовується в нашому проекті)
3. **Binary** - бінарний формат

## Валідація

### Схеми валідації

- **XSD** (XML Schema Definition)
- **DTD** (Document Type Definition)
- **RNG** (RelaxNG)

### Обов'язкові поля

Мінімальний набір для валідного запису:
- Record reference
- Notification type
- Product identifier (ISBN-13)
- Title
- Contributor (Author)
- Language
- Publisher

## Сумісність

### Backward Compatibility

ONIX 3.1 майже повністю сумісний з ONIX 3.0.8:
- Більшість полів залишилися незмінними
- Додані нові опціональні поля
- Деякі поля застаріли (deprecated)

### Migration from 2.1

Для міграції з ONIX 2.1:
- Використовуйте офіційний конвертер
- Перевіряйте маппінг полів
- Тестуйте на прикладах

## Додаткові ресурси

- [Implementation Guide](best_practices.md)
- [Code Lists](code_lists.md)
- [Structure Overview](structure.md)
- [EDItEUR Official Site](https://www.editeur.org/)

## Завантаження

Офіційні файли доступні на:
https://www.editeur.org/93/Release-3.0-and-3.1-Downloads/

- Specification PDF
- Implementation Guide PDF
- Schemas (XSD, DTD, RNG)
- Sample files





