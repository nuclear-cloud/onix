#!/usr/bin/env python3
"""
Extract and map all Yakaboo categories (levels 1-7) to THEMA subject codes.
Intelligently assigns THEMA codes based on category names and hierarchy.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# THEMA keyword-to-code mappings
THEMA_KEYWORD_MAP = {
    # Fiction genres
    r'fantast|fantasy': ['FM'],
    r'sci[- ]?fi|научн|science.fiction': ['FL'],
    r'thriller|трилер': ['FF'],
    r'suspens': ['FF'],
    r'detective|детектив|крим': ['FF'],
    r'crime|криміналь': ['FF'],
    r'mystery|таємниц': ['FF'],
    r'horror|жах|хорор': ['FK'],
    r'romance|любов|любовн|romance': ['FR'],
    r'adventure|пригоди|приключ': ['FJ'],
    r'action|боевик': ['FJ'],
    r'biography|біографі|биография': ['DN', 'DNBF'],
    r'autobiography|автобіографі|автобиография': ['DN'],
    r'memoir|мемуар': ['DN'],
    r'classic|класик': ['FC'],
    r'poetry|поезі|поэзи': ['DC'],
    r'verse|вірш': ['DC'],
    r'drama|драма': ['DA'],
    r'play|п\'єса': ['DA'],
    r'script|сценарій': ['DA'],
    
    # Non-fiction
    r'business|бізнес|бизнес': ['KJ', 'KFF'],
    r'economics|економі|экономи': ['KC'],
    r'finance|фінанс|финанс': ['KFF'],
    r'psycholog|психолог': ['JM', 'VFX'],
    r'health|здоров|здоровье': ['VFM', 'MK'],
    r'fitness|фітнес|фитнес': ['WB'],
    r'nutrition|харчув|питани': ['WB'],
    r'cook|рецепт|кулінар|кулинар': ['WB'],
    r'culinary|кулінар': ['WB'],
    r'art|мистец|искусст': ['A', 'AB'],
    r'music|музик': ['AV'],
    r'cinema|синем|кино': ['AP'],
    r'film|фільм|фильм': ['AP'],
    r'history|історі|история': ['NH', 'NHD'],
    r'religion|релігі|религи': ['QR'],
    r'philosophy|філософі|философ': ['QD'],
    r'politics|політик|политик': ['JP'],
    r'law|закон|право': ['L', 'LA'],
    r'computer|комп\'ютер|компьютер': ['U', 'UM'],
    r'program|програм': ['UM'],
    r'technolog|технолог': ['T'],
    r'science|наук': ['P', 'PD'],
    r'physics|фізик|физик': ['PH'],
    r'chemistry|хімі|хими': ['PN'],
    r'biology|біолог|биолог': ['PS'],
    r'astronomy|астроном': ['PG'],
    r'math|математ': ['PB'],
    r'travel|подорож|путешеств': ['WH'],
    r'education|освіт|образова': ['J', 'JN'],
    r'language|мова|язык': ['CJ'],
    r'hobby|хоббі|хобби': ['W'],
    r'craft|ремесл': ['WF'],
    r'garden|садовництво|садоводств': ['WM'],
    r'sport|спорт': ['WS'],
    r'self.help|самопоміч|самопомощь': ['VS'],
    r'development|розвит|развит': ['VS'],
    r'personal|особист|личн': ['VS'],
    r'motivat|мотива': ['VS'],
    r'children|дитяч|детск': ['Y', 'YF'],
    r'kids|для дітей|для детей': ['Y'],
    r'teen|підліт|подросток': ['Y'],
    r'young.adult|молоді|молодой': ['Y'],
    r'comic|комікс|комикс': ['X'],
    r'graphic|графічн|графическ': ['X'],
    r'manga|манга': ['X'],
    r'esoter|езотер': ['VXW'],
    r'occult|окультн': ['VXW'],
    r'fiction': ['F'],
    r'literary': ['F', 'FC'],
}

class YakabooThemaMapper:
    def __init__(self):
        self.yakaboo_path = Path('data/yakaboo_categories_tree.json')
        self.config_path = Path('config/yakaboo_to_thema_mapping_full.yaml')
        self.categories = []
        self.category_map = {}
        
    def load_categories(self):
        """Load Yakaboo categories"""
        with open(self.yakaboo_path, 'r', encoding='utf-8') as f:
            self.categories = json.load(f)
        
        # Build fast lookup map
        for cat in self.categories:
            self.category_map[cat['id']] = cat
        
        print(f"✓ Loaded {len(self.categories)} categories")
    
    def extract_thema_codes(self, name: str, parent_codes: Set[str] = None) -> List[str]:
        """Extract THEMA codes from category name"""
        if parent_codes is None:
            parent_codes = set()
        
        codes = parent_codes.copy()
        name_lower = name.lower()
        
        for pattern, thema_codes in THEMA_KEYWORD_MAP.items():
            try:
                if re.search(pattern, name_lower):
                    codes.update(thema_codes)
            except re.error:
                pass
        
        return sorted(list(codes))
    
    def get_parent_chain(self, cat_id: int) -> List[Dict]:
        """Get parent category chain"""
        chain = []
        current = self.category_map.get(cat_id)
        
        while current:
            chain.insert(0, current)
            parent_id = current.get('parent_id')
            if parent_id:
                current = self.category_map.get(parent_id)
            else:
                break
        
        return chain
    
    def consolidate_thema_codes(self, parent_chain: List[Dict]) -> List[str]:
        """Consolidate THEMA codes from parent chain"""
        codes_weight = defaultdict(int)
        
        for idx, cat in enumerate(parent_chain):
            # Earlier levels (closer to root) get higher weight
            weight = len(parent_chain) - idx
            codes = self.extract_thema_codes(cat['name'])
            
            for code in codes:
                codes_weight[code] += weight
        
        # Sort by weight (descending), then alphabetically
        return sorted(codes_weight.keys(), key=lambda x: (-codes_weight[x], x))
    
    def is_book_related(self, cat_id: int, visited: Set[int] = None) -> bool:
        """Check if category is book-related"""
        if visited is None:
            visited = set()
        
        if cat_id in visited:
            return False
        visited.add(cat_id)
        
        cat = self.category_map.get(cat_id)
        if not cat:
            return False
        
        # Book keywords
        book_keywords = ['kniga', 'книг', 'literatur', 'литератур', 'роман', 'повід', 'сказка', 'басни', 'вірш', 'поезі', 'худож']
        name_lower = cat['name'].lower()
        
        # Check current name
        if any(kw in name_lower for kw in book_keywords):
            return True
        
        # Check parent (one level up)
        parent_id = cat.get('parent_id')
        if parent_id and parent_id != cat_id:
            parent = self.category_map.get(parent_id)
            if parent:
                parent_lower = parent['name'].lower()
                if any(kw in parent_lower for kw in book_keywords):
                    return True
        
        return False
    
    def generate_yaml(self) -> str:
        """Generate YAML mapping"""
        yaml = f"""# Yakaboo to THEMA Code Mapping (Auto-generated)
# Generated from complete category hierarchy with 7 levels
# Date: {Path('data/yakaboo_categories_tree.json').stat().st_mtime}
#
# Structure:
#   categories:
#     id:
#       name: Category name
#       level: Hierarchical level (1-7)
#       parent_id: Parent category ID
#       thema_codes: [List of mapped THEMA codes]
#       hierarchy: Category path from root

version: "2.0"
description: "Complete Yakaboo category to THEMA mapping (all 7 levels)"
total_categories: {len(self.categories)}

categories:
"""
        
        # Group categories by level for organization
        by_level = defaultdict(list)
        for cat in self.categories:
            level = cat.get('level', 0)
            by_level[level].append(cat)
        
        level_order = sorted(by_level.keys(), key=lambda x: (isinstance(x, str), x))
        
        for level in level_order:
            cats_at_level = sorted(by_level[level], key=lambda x: x['name'])
            yaml += f"\n  # ========== Level {level} ({len(cats_at_level)} categories) ==========\n"
            
            for cat in cats_at_level:
                parent_chain = self.get_parent_chain(cat['id'])
                thema_codes = self.consolidate_thema_codes(parent_chain)
                
                # Build hierarchy path
                hierarchy = ' > '.join([c['name'] for c in parent_chain])
                
                # Format YAML entry
                yaml += f"""
  '{cat['id']}':
    name: {self._quote_yaml(cat['name'])}
    level: {level}
    parent_id: {cat.get('parent_id', 'null')}
    thema_codes: [{', '.join(thema_codes) if thema_codes else 'UNCATEGORIZED'}]
"""
                if self.is_book_related(cat['id']):
                    yaml += f"    is_book: true\n"
        
        return yaml
    
    @staticmethod
    def _quote_yaml(text: str) -> str:
        """Quote text for YAML if needed"""
        escaped = text.replace('"', '\\"')
        if any(c in text for c in [':', '#', '"', "'"]):
            return f'"{escaped}"'
        return f'"{text}"'
    
    def run(self):
        """Main execution"""
        print("\n🔄 Yakaboo to THEMA Mapping Generator\n")
        
        self.load_categories()
        
        print("📊 Statistics:")
        by_level = defaultdict(int)
        for cat in self.categories:
            by_level[cat.get('level', 'unknown')] += 1
        
        for level in sorted(by_level.keys()):
            print(f"   Level {level}: {by_level[level]:,} categories")
        
        # Count book-related
        book_count = sum(1 for cat in self.categories if self.is_book_related(cat['id']))
        print(f"   Book-related: {book_count:,} categories")
        
        print("\n🔄 Generating YAML mapping...")
        yaml = self.generate_yaml()
        
        print(f"✓ Generated mapping with {len(self.categories)} categories")
        
        # Save to file
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml, encoding='utf-8')
        
        print(f"✅ Saved to: {self.config_path}")
        print(f"   File size: {len(yaml):,} bytes")

if __name__ == '__main__':
    mapper = YakabooThemaMapper()
    mapper.run()
