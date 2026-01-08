# Digital Products in ONIX 3.0/3.1

## Огляд

ONIX 3.0/3.1 надає гнучкі можливості для опису цифрових продуктів (електронних книг, аудіокниг тощо).

## Product Form (Форма продукту)

### Цифрові форми

- **E101** - EPUB
- **E102** - PDF
- **E107** - Microsoft Reader
- **E108** - Mobipocket
- **E109** - Palm
- **E110** - NetLibrary
- **E111** - Rocketbook
- **E112** - Softbook
- **E113** - Glassbook
- **E114** - Adobe Digital Editions
- **E115** - Mobipocket (Kindle)
- **E116** - iBook
- **E117** - ePIB
- **E118** - Android
- **E119** - Other

## Product Form Detail (Деталі форми)

### EPUB деталі

- **E200** - EPUB 2.0.1
- **E201** - EPUB 3.0
- **E202** - EPUB 3.0.1
- **E203** - EPUB 3.1

### PDF деталі

- **E210** - PDF
- **E211** - PDF 1.4
- **E212** - PDF 1.5
- **E213** - PDF 1.6
- **E214** - PDF 1.7

## Product Form Features (Особливості)

- **01** - DRM protected
- **02** - Digital watermarking
- **03** - Adobe DRM
- **04** - Apple DRM
- **05** - OMA DRM
- **06** - Readable on dedicated e-reader device
- **07** - Readable on any device

## Приклад електронної книги

```json
{
  "product_form": "E101",
  "product_form_detail": "E203",
  "product_form_feature": [
    {"type": "01", "value": "01"},
    {"type": "07", "value": "07"}
  ],
  "epub_type": "01",
  "epub_type_version": "3.1"
}
```

## Аудіокниги

### Форми

- **A101** - CD-Audio
- **A102** - CD-ROM
- **A103** - DVD Audio
- **A104** - DVD Video
- **A105** - Downloadable audio file
- **A106** - Pre-recorded digital audio player

### Формати аудіо

- **MP3**
- **WAV**
- **AAC**
- **FLAC**

## Best Practices

1. ✅ Завжди вказуйте `product_form` для цифрових продуктів
2. ✅ Вказуйте версію формату (`product_form_detail`)
3. ✅ Описуйте DRM та обмеження
4. ✅ Вказуйте сумісність з пристроями





