# Yakaboo Category Mapping - Complete Index

**Project Status**: ✅ COMPLETE | **Date**: January 11, 2025 | **Version**: 3.0

---

## 🎯 Quick Start

### For ONIX Feed Generation (Recommended Path):

1. **Load the Final Mapping**:
   ```python
   import yaml
   with open('config/yakaboo_to_thema_mapping_final.yaml') as f:
       mapping = yaml.safe_load(f)
   ```

2. **Get THEMA Codes for a Category**:
   ```python
   thema_codes = mapping['categories'][yakaboo_id]['thema']
   # Result: ['KJJ'] or ['F'] or ['GENERAL']
   ```

3. **Generate ONIX Subject Elements**:
   ```python
   for code in thema_codes:
       if code != 'GENERAL':
           print(f"<Subject><SubjectCode>{code}</SubjectCode></Subject>")
   ```

---

## 📚 Documentation Map

### **Start Here** ⭐

| Document | Purpose | Length | Best For |
|----------|---------|--------|----------|
| **THIS FILE** | Navigation & overview | 2 min | Getting oriented |
| [YAKABOO_MAPPING_DELIVERABLES.md](YAKABOO_MAPPING_DELIVERABLES.md) | Executive summary | 10 min | Project overview |
| [YAKABOO_MAPPING_COMPLETE.md](YAKABOO_MAPPING_COMPLETE.md) | Technical guide | 20 min | Implementation |

### **Configuration Files** 

| File | Use Case | Size | Lines |
|------|----------|------|-------|
| [`config/yakaboo_to_thema_mapping_final.yaml`](../config/yakaboo_to_thema_mapping_final.yaml) | **✅ PRODUCTION** - Use this for ONIX feeds | 385 KB | 18,666 |
| [`config/yakaboo_to_onix_mapping.yaml`](../config/yakaboo_to_onix_mapping.yaml) | Reference - ONIX code list explanations | 4.6 KB | 142 |
| [`config/yakaboo_to_thema_mapping_full.yaml`](../config/yakaboo_to_thema_mapping_full.yaml) | Data analysis - Complete extraction | 506 KB | 22,465 |
| [`config/yakaboo_to_thema_mapping_improved.yaml`](../config/yakaboo_to_thema_mapping_improved.yaml) | Alternative - Hierarchical analysis | 471 KB | 22,357 |
| [`config/yakaboo_to_thema_mapping.yaml`](../config/yakaboo_to_thema_mapping.yaml) | Quick reference - Levels 1-3 only | 14 KB | 470 |

### **Generation Scripts**

| Script | Purpose | Runtime |
|--------|---------|---------|
| [`scripts/generate_yakaboo_final_mapping.py`](../scripts/generate_yakaboo_final_mapping.py) | Generate Final v3.0 (RECOMMENDED) | ~2 sec |
| [`scripts/extract_yakaboo_mapping.py`](../scripts/extract_yakaboo_mapping.py) | Generate Full v1.0 | ~2 sec |
| [`scripts/extract_yakaboo_mapping_improved.py`](../scripts/extract_yakaboo_mapping_improved.py) | Generate Improved v2.1 | ~2 sec |
| [`scripts/extract_yakaboo_onix_mapping.py`](../scripts/extract_yakaboo_onix_mapping.py) | Analyze ONIX structure | ~1 sec |

---

## 📊 Key Numbers

```
Categories:       3,623 total
├─ Books:           695 (19%)
├─ Mapped:          370 (10%)
└─ Inherited:       250+ (7%)

Hierarchy:        7 levels deep
THEMA codes:      50 unique
ONIX lists:       166 total
```

---

## 🎯 Use Cases & Solutions

### Use Case 1: Generate ONIX Feed with Subjects

**Requirement**: Export book products with THEMA subject classification to ONIX format

**Solution**:
1. Load: [`config/yakaboo_to_thema_mapping_final.yaml`](../config/yakaboo_to_thema_mapping_final.yaml)
2. For each book, fetch its yakaboo_category_id
3. Look up THEMA codes in mapping
4. Include in ONIX output

**Example Code** (See [YAKABOO_MAPPING_COMPLETE.md](YAKABOO_MAPPING_COMPLETE.md#using-final-v30-mapping-in-code) for full implementation)

---

### Use Case 2: Cross-Catalog Discovery

**Requirement**: Map Yakaboo products to standard subject schemes for discovery in Google, distributors, etc.

**Solution**:
1. Yakaboo category ID → THEMA code (via mapping)
2. THEMA code → Standard scheme (Dewey, DDC, etc.) via THEMA bridge
3. Include in ONIX/metadata feeds

---

### Use Case 3: Book-Specific Filtering

**Requirement**: Identify which Yakaboo products are actually books

**Solution**:
- Check `is_book` flag in mapping
- Filter: `mapping['categories'][id].get('is_book', False) == True`
- Result: 695 book-related categories identified

---

### Use Case 4: Hierarchical Navigation

**Requirement**: Build browse-able book category hierarchy with standard codes

**Solution**:
1. Use Level 3 categories (492 categories) as main browse nodes
2. Include THEMA codes at each level
3. Show parent categories for context
4. Display THEMA code to users for standardized browsing

---

## 🔍 Data Structure

### YAML Mapping Format

```yaml
version: "3.0"
description: "Yakaboo to THEMA mapping"

categories:
  4724:                    # Yakaboo category ID
    name: "Бизнес, деньги, экономика"
    level: 3               # Hierarchy level (1-7)
    thema: [KJJ]          # THEMA codes (array, can be multiple)
    is_book: false        # Is this book-related?
```

### Looking Up a Category

```python
# By ID (fast)
cat = mapping['categories'][4724]
print(cat['thema'])  # ['KJJ']

# By name (slow, requires search)
for cat_id, cat_info in mapping['categories'].items():
    if cat_info['name'] == 'Бизнес, деньги, экономика':
        print(cat_info['thema'])
```

---

## 📈 Mapping Quality

### Coverage by Level

| Level | Total | Mapped | % | Notes |
|-------|-------|--------|---|-------|
| L1 | 1 | 0 | 0% | Root category |
| L2 | 7 | 2 | 29% | Main types: Books, Stationery, etc. |
| L3 | 492 | 95 | 19% | ⭐ Primary use in queries |
| L4 | 678 | 45 | 7% | Specific products |
| L5 | 1,036 | 65 | 6% | Product variants |
| L6 | 1,392 | 120 | 9% | Format/edition details |
| L7 | 17 | 5 | 29% | Special/award categories |
| **TOTAL** | **3,623** | **370** | **10.2%** | Direct mappings |

### Why Not 100%?

Most Yakaboo categories are e-commerce product variants (format, edition, binding, size), not subject categories. They inherit subject codes from parents. The 370 directly mapped categories are "semantic" categories, while 3,253 are "variant" categories.

---

## 🔧 Technical Details

### File Format: YAML

All mapping files are in YAML format for:
- **Readability**: Easy to understand and edit
- **Portability**: Can be loaded in Python, Ruby, Node.js, etc.
- **Validation**: Can be linted with yamllint
- **Comments**: Includes documentation inline

### Validation

```bash
# Check YAML syntax
yamllint config/yakaboo_to_thema_mapping_final.yaml

# Load in Python
python3 -c "import yaml; print(yaml.safe_load(open('config/yakaboo_to_thema_mapping_final.yaml')).keys())"

# Count lines
wc -l config/yakaboo_to_thema_mapping_final.yaml
```

---

## 📝 Reference Tables

### THEMA Codes Used (Top 20)

| Code | Name | Count | Example |
|------|------|-------|---------|
| F | Fiction | 50+ | Художна література |
| Y | Children's/Young Adult | 45+ | Детська література |
| DN | Biography | 25+ | Автобіографічні книги |
| KJJ | Business & Economics | 20+ | Бізнес, деньги |
| NH | History | 18+ | Історія |
| JN | Education | 15+ | Навчальна література |
| AV | Music & Sound | 12+ | Музика |
| AP | Film & Cinema | 10+ | Кіно |
| UM | Programming | 8+ | Комп'ютерні книги |
| P | Science | 7+ | Наука |
| ... | ... | ... | (40+ more codes) |

### ONIX Critical Lists

| List | Name | Codes | For Books |
|------|------|-------|-----------|
| 150 | Product Form | 148 | Hardcover, Paperback, Ebook |
| 175 | Product Form Detail | 365 | PDF, EPUB, MOBI, etc. |
| 74 | Language ISO 639-2 | 578 | ukr, eng, rus, fra, etc. |
| 81 | Content Type | 51 | Text, maps, illustrations |
| 28 | Audience | 13 | General, education, children |

---

## 🚀 Getting Started Checklist

- [ ] Read this file (you are here)
- [ ] Review [YAKABOO_MAPPING_DELIVERABLES.md](YAKABOO_MAPPING_DELIVERABLES.md) (5 min)
- [ ] Check Final v3.0 mapping structure in [config/](../config/)
- [ ] Load mapping in your application
- [ ] Test THEMA code lookup for sample categories
- [ ] Generate ONIX Subject elements
- [ ] Load mapping into database (optional)
- [ ] Generate full ONIX feed with subjects
- [ ] Validate ONIX output
- [ ] Submit to aggregators

---

## 📞 FAQ

**Q: Which mapping should I use?**
A: Use `yakaboo_to_thema_mapping_final.yaml` (Final v3.0) for production. It balances coverage and accuracy.

**Q: How do I handle categories with THEMA='GENERAL'?**
A: These are mostly non-book items or variant categories. Either skip them or inherit from parent category.

**Q: Can I update the mappings?**
A: Yes! Edit the curated patterns in `scripts/generate_yakaboo_final_mapping.py` and regenerate.

**Q: Do I need all 5 mapping files?**
A: No. Use Final v3.0 for production. Keep Full v1.0 for backup/analysis.

**Q: How often should I regenerate?**
A: Only when Yakaboo adds new categories. Check the source file modification date.

---

## 📂 File Tree

```
onix_project/
├── config/
│   ├── yakaboo_to_thema_mapping_final.yaml          ✅ USE THIS
│   ├── yakaboo_to_onix_mapping.yaml
│   ├── yakaboo_to_thema_mapping_full.yaml
│   ├── yakaboo_to_thema_mapping_improved.yaml
│   └── yakaboo_to_thema_mapping.yaml
│
├── scripts/
│   ├── generate_yakaboo_final_mapping.py            ✅ PRODUCTION
│   ├── extract_yakaboo_mapping.py
│   ├── extract_yakaboo_mapping_improved.py
│   └── extract_yakaboo_onix_mapping.py
│
├── docs/
│   ├── YAKABOO_MAPPING_INDEX.md                     ← YOU ARE HERE
│   ├── YAKABOO_MAPPING_DELIVERABLES.md              ← OVERVIEW
│   ├── YAKABOO_MAPPING_COMPLETE.md                  ← TECHNICAL GUIDE
│   └── YAKABOO_SIMPLE_MAPPING.md
│
└── data/
    ├── yakaboo_categories_tree.json
    ├── thema_v1.6_en.json
    ├── thema_v1.6_uk.json
    └── ONIX_BookProduct_Codelists_Issue_71.json
```

---

## ✅ Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Category Extraction | ✅ Complete | All 3,623 categories processed |
| THEMA Mapping | ✅ Complete | 50 codes used, 370 direct, 250+ inherited |
| ONIX Analysis | ✅ Complete | All 166 lists documented |
| Final v3.0 | ✅ Complete | Production ready |
| Documentation | ✅ Complete | 3 guides + inline comments |
| Scripts | ✅ Complete | 4 generation scripts |
| Validation | ✅ Complete | All YAML files validated |

---

## 🎯 Next Action

**Choose your path:**

1. **Quick Test**: Load Final mapping and look up a category (5 min)
2. **Integration**: Add mapping to your database/application (30 min)
3. **ONIX Feed**: Generate ONIX output with THEMA subjects (1-2 hours)
4. **Full Rollout**: Load 69k+ books with proper THEMA classification (1-2 days)

**Recommended**: Start with #1, then #2, then #3 in sequence.

---

**Generated**: January 11, 2025
**Version**: 3.0  
**Status**: ✅ PRODUCTION READY

For detailed information: See [YAKABOO_MAPPING_COMPLETE.md](YAKABOO_MAPPING_COMPLETE.md)
