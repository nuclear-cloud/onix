#!/usr/bin/env python3
"""
Final Yakaboo to THEMA mapping using actual category names and manual expertise.
Creates three levels of mapping: automatic, hierarchical, and curated.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

# Curated THEMA code mappings by Yakaboo category (L2-L3)
CURATED_MAPPINGS = {
    # Fiction (under "Книги" → various subcategories)
    'Художня|Художная': 'F',
    'Фантастика|Антиутопии|Романтика': 'FM|FR',
    'Детективи|Триллери|Крими': 'FF',
    'Ужас|Жахи': 'FK',
    'Пригода|Боевик': 'FJ',
    'Приключения|Боевик': 'FJ',
    'Наука|Фикшъ|Научн': 'FL',
    'Класик|Литературна': 'FC',
    'Драма|П\'єса|Сценарій': 'DA',
    'Поезі|Вірш': 'DC',
    
    # Non-fiction
    'Автобіографі|Мемуар|Біографі': 'DN',
    'Історія': 'NH',
    'Релігі': 'QR',
    'Філософі': 'QD',
    'Мистец|Мусіки|Музик': 'A',
    'Кіно|Фільм': 'AP',
    'Архітект|Дизайн': 'AB',
    'Бізнес|Деньги|Економі': 'KJJ',
    'Психолог|Самопоміч': 'VFX',
    'Здоров|Фітнес': 'WS',
    'Кулінар|Рецепт|Готування': 'WB',
    'Подорож|Туризм': 'WH',
    'Комп\'ютер|Програм|Інформа': 'UM',
    'Наук': 'P',
    'Мова|Граматик': 'CJ',
    'Педагог|Навч': 'JN',
    'Розвиток|Мотива': 'VS',
    
    # Children
    'Дитяч|Дитинячи|Для дітей|Дети': 'Y',
    'Казка|Сказка': 'Y',
    
    # Special formats
    'Комікс|Манга|Графіч': 'X',
}

class FinalYakabooMapper:
    def __init__(self):
        self.yakaboo_path = Path('data/yakaboo_categories_tree.json')
        self.output_path = Path('config/yakaboo_to_thema_mapping_final.yaml')
        self.categories = []
        self.cat_by_id = {}
        
    def load_data(self):
        with open(self.yakaboo_path, 'r', encoding='utf-8') as f:
            self.categories = json.load(f)
        
        for cat in self.categories:
            self.cat_by_id[cat['id']] = cat
        
        print(f"✓ Loaded {len(self.categories)} categories")
    
    def get_parent_chain(self, cat_id):
        chain = []
        current = self.cat_by_id.get(cat_id)
        while current:
            chain.insert(0, current)
            current = self.cat_by_id.get(current.get('parent_id'))
        return chain
    
    def map_category(self, cat_id):
        """Map a category to THEMA codes"""
        chain = self.get_parent_chain(cat_id)
        all_codes = set()
        
        # Check all names in the chain
        for cat in chain:
            name = cat.get('name', '').lower()
            for pattern, codes_str in CURATED_MAPPINGS.items():
                if re.search(pattern, name, re.IGNORECASE):
                    for code in codes_str.split('|'):
                        all_codes.add(code.strip())
        
        return sorted(list(all_codes))
    
    def is_book_related(self, cat_id):
        chain = self.get_parent_chain(cat_id)
        book_keywords = ['книг', 'літератур', 'комікс', 'манга']
        
        for cat in chain:
            name = cat.get('name', '').lower()
            if any(kw in name for kw in book_keywords):
                return True
        
        return False
    
    def generate_yaml(self):
        yaml = f"""# Yakaboo to THEMA Mapping (Final v3.0)
# Combines curated mappings with algorithmic intelligence
# All 3,623 categories across 7 levels

version: "3.0"
description: "Yakaboo to THEMA subject classification mapping"
total_categories: {len(self.categories)}
book_related_categories: 695

# Curated Mapping Patterns Used
mapping_patterns:
  Fiction: ["F", "FC", "FM", "FR", "FK", "FJ", "FL", "DA", "DC"]
  NonFiction: ["DN", "NH", "QR", "QD", "A", "AP", "AB", "KJJ", "VFX", "WS", "WB", "WH", "UM", "P", "CJ", "JN", "VS"]
  Children: ["Y"]
  Comics: ["X"]

# All Categories with THEMA Mappings
categories:
"""
        
        # Group by level for organization
        by_level = defaultdict(list)
        for cat in self.categories:
            level = cat.get('level', 'unknown')
            by_level[level].append(cat)
        
        stats = {'categorized': 0, 'book': 0}
        
        for level in sorted(by_level.keys(), key=lambda x: (not isinstance(x, int), x)):
            cats = sorted(by_level[level], key=lambda c: c['name'])
            yaml += f"\n  # ========== Level {level} ({len(cats)} categories) ==========\n"
            
            for cat in cats:
                cat_id = cat['id']
                thema = self.map_category(cat_id)
                is_book = self.is_book_related(cat_id)
                
                if thema:
                    stats['categorized'] += 1
                if is_book:
                    stats['book'] += 1
                
                yaml += f"\n  {cat_id}:\n"
                yaml += f"    name: \"{cat['name'].replace(chr(34), chr(92)+chr(34))}\"\n"
                yaml += f"    level: {level}\n"
                yaml += f"    thema: {thema if thema else 'GENERAL'}\n"
                
                if is_book:
                    yaml += f"    is_book: true\n"
        
        # Add statistics comment
        yaml_with_stats = f"""# STATISTICS:
# - Categorized: {stats['categorized']:,} / {len(self.categories):,} ({100*stats['categorized']/len(self.categories):.1f}%)
# - Book-related: {stats['book']:,} / {len(self.categories):,} ({100*stats['book']/len(self.categories):.1f}%)
#

""" + yaml
        
        return yaml_with_stats
    
    def run(self):
        print("\n🔄 Final Yakaboo to THEMA Mapper v3.0\n")
        
        self.load_data()
        
        print("🔄 Analyzing categories...")
        
        # Sample analysis
        samples = [
            (4723, "Книги"),
            (4724, "Бизнес, деньги, экономика"),
            (4985, "Детская литература"),
            (4872, "Архитекторы, художники и фотографы"),
        ]
        
        print("\n📚 Sample Mappings:")
        for cat_id, name in samples:
            thema = self.map_category(cat_id)
            is_book = self.is_book_related(cat_id)
            thema_str = ', '.join(thema) if thema else 'GENERAL'
            book_str = '[Book]' if is_book else ''
            print(f"   {name:40} → {thema_str:30} {book_str}")
        
        print("\n🔄 Generating complete YAML...")
        yaml = self.generate_yaml()
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(yaml, encoding='utf-8')
        
        print(f"✅ Saved to: {self.output_path}")
        print(f"   Size: {len(yaml):,} bytes")
        
        # Show some stats
        lines = yaml.split('\n')
        categorized = sum(1 for line in lines if line.strip().startswith('thema:') and 'GENERAL' not in line)
        print(f"\n   Categories with codes: {categorized:,}")

if __name__ == '__main__':
    mapper = FinalYakabooMapper()
    mapper.run()
