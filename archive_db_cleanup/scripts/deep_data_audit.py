import json
import sys
import re
from collections import Counter, defaultdict
import statistics

def clean_isbn(isbn_raw):
    """Removes hyphens and spaces to check raw digits."""
    if not isbn_raw:
        return None
    return re.sub(r'[^0-9X]', '', str(isbn_raw).upper())

def is_valid_isbn13(isbn):
    """Basic check for 13-digit ISBN length."""
    return len(isbn) == 13 and isbn.isdigit()

def audit_file(filepath):
    print(f"Deep auditing {filepath}...")
    
    stats = {
        'total': 0,
        'books_detected': 0,
        'non_books_detected': 0,
        'isbn_valid_13': 0,
        'isbn_valid_10': 0,
        'isbn_invalid': 0,
        'isbn_missing': 0,
        'price_zero': 0,
        'price_missing': 0,
        'author_messy': 0, # contains comma, &, etc
        'lang_mismatch': 0, # english lang but ua category
    }
    
    prices = []
    lang_category_map = Counter()
    author_samples = []
    non_book_types = Counter()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stats['total'] += 1
                    
                    # 1. Classification (Book vs Non-Book)
                    # Heuristic: Has ISBN or Author usually means Book. 
                    # Has "boardgame_*" fields means Non-Book.
                    is_book = False
                    
                    # Check specific non-book markers
                    non_book_markers = [k for k in record.keys() if k.startswith('boardgame_') or k.startswith('gift_') or k.startswith('pen_') or 'notebook' in k]
                    
                    if non_book_markers:
                         stats['non_books_detected'] += 1
                         for m in non_book_markers:
                             # record the type of non-book item roughly
                             non_book_types[m.split('_')[0]] += 1
                    elif 'book_isbn' in record or 'author' in record:
                         is_book = True
                         stats['books_detected'] += 1
                    else:
                         # Ambiguous
                         pass

                    # 2. ISBN Audit
                    isbn_raw = record.get('book_isbn')
                    if isbn_raw:
                        clean = clean_isbn(isbn_raw)
                        if not clean:
                            stats['isbn_invalid'] += 1
                        elif len(clean) == 13:
                            stats['isbn_valid_13'] += 1
                        elif len(clean) == 10:
                            stats['isbn_valid_10'] += 1
                        else:
                            stats['isbn_invalid'] += 1
                    else:
                        stats['isbn_missing'] += 1

                    # 3. Price Audit
                    price = record.get('price')
                    if price is None:
                        stats['price_missing'] += 1
                    else:
                        try:
                            p_val = float(price)
                            if p_val == 0:
                                stats['price_zero'] += 1
                            else:
                                prices.append(p_val)
                        except ValueError:
                            stats['price_missing'] += 1

                    # 4. Author Quality
                    author_val = record.get('author')
                    # If author is a list of IDs, we can't check for "messy string", 
                    # but we can check if we have the corresponding labels
                    if isinstance(author_val, list):
                        # It's a list of IDs. Let's look at author_label
                        auth_labels = record.get('author_label')
                        if isinstance(auth_labels, list):
                            # It's a list of dicts
                            names = [a.get('label', '') for a in auth_labels]
                            full_auth_str = ", ".join(names)
                            if re.search(r'[,&/]|( and )|( et )', full_auth_str):
                                # Comma is natural for joining multiple authors, so maybe ignore it in this context
                                # But we want to know if INDIVIDUAL names are messy
                                pass 
                        else:
                            # Unexpected structure
                            pass
                    elif isinstance(author_val, str):
                         if re.search(r'[,&/]|( and )|( et )', author_val):
                            stats['author_messy'] += 1
                            if len(author_samples) < 10:
                                author_samples.append(author_val)

                    # 5. Language Mystery
                    # Check top category name vs language
                    lang_code = None
                    lang_label_obj = record.get('book_lang_label')
                    
                    if isinstance(lang_label_obj, list) and len(lang_label_obj) > 0:
                        lang_code = lang_label_obj[0].get('option_code')
                    elif isinstance(lang_label_obj, dict):
                        lang_code = lang_label_obj.get('option_code')
                    
                    if lang_code == 'Anglijskij':
                        cats = record.get('category', [])
                        if cats and isinstance(cats, list):
                            # Find category with level 3 (usually specific genre) or 2 (Root 'Books')
                            # Let's grab Level 2 and Level 3 to see where they sit
                            cat_l2 = next((c.get('name') for c in cats if str(c.get('level')) == '2'), None)
                            cat_l3 = next((c.get('name') for c in cats if str(c.get('level')) == '3'), None)
                            
                            key = f"L2: {cat_l2} / L3: {cat_l3}"
                            lang_category_map[key] += 1

                    if stats['total'] % 100000 == 0:
                        print(f"Audited {stats['total']} records...", file=sys.stderr)

                except json.JSONDecodeError:
                    continue
                    
    except FileNotFoundError:
        print(f"File not found.")
        return

    # Report
    print(f"\n# Deep Data Audit Report\n")
    print(f"**Date**: 2026-01-05")
    print(f"**Total Records**: {stats['total']}\n")
    
    print("## 1. Classification")
    print(f"- **Books (heuristic)**: {stats['books_detected']} ({stats['books_detected']/stats['total']*100:.1f}%)")
    print(f"- **Non-Books**: {stats['non_books_detected']} ({stats['non_books_detected']/stats['total']*100:.1f}%)")
    print(f"- *Non-Book Types detected*: {', '.join([f'{k}: {v}' for k,v in non_book_types.most_common(5)])}")
    
    print("\n## 2. ISBN Quality")
    print(f"- **Valid ISBN-13**: {stats['isbn_valid_13']} ({stats['isbn_valid_13']/stats['total']*100:.1f}%)")
    print(f"- **Valid ISBN-10**: {stats['isbn_valid_10']} (Need conversion)")
    print(f"- **Invalid/Garbage**: {stats['isbn_invalid']}")
    print(f"- **Missing**: {stats['isbn_missing']} ({stats['isbn_missing']/stats['total']*100:.1f}%)")
    
    print("\n## 3. Price Analysis")
    if prices:
        print(f"- **Zero Prices**: {stats['price_zero']}")
        print(f"- **Min**: {min(prices)}")
        print(f"- **Max**: {max(prices)}")
        print(f"- **Avg**: {statistics.mean(prices):.2f}")
        print(f"- **Median**: {statistics.median(prices):.2f}")
    
    print("\n## 4. Author Data Quality")
    print(f"- **Messy Authors (contain separators)**: {stats['author_messy']}")
    print(f"- *Samples*: {author_samples[:5]}")
    
    print("\n## 5. The 'English Language' Anomaly")
    print("Top categories for items marked as 'English':")
    for cat, count in lang_category_map.most_common(10):
        print(f"- {cat}: {count}")

if __name__ == "__main__":
    audit_file("data/yakaboo_complete_final.jsonl")
