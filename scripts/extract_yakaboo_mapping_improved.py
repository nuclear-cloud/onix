#!/usr/bin/env python3
"""
Improved Yakaboo to THEMA mapping with intelligent inheritance.
Analyzes full category paths to assign codes intelligently.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

# Enhanced keyword patterns with better matching
THEMA_PATTERNS = {
    # Direct keywords
    r'\bхуд(ож|ожна|ожна|)ня.*літ|художн\b': 'F',     # Fiction
    r'\bлітератур\b': 'F',
    r'\bроман\b': 'FR',
    r'\bповід\b': 'FC',
    r'\bтрилер\b': 'FF',
    r'\bбойов\b': 'FJ',
    r'\bжах\b': 'FK',
    r'\bфанта\b': 'FM',
    r'\bулюблен\b': 'FR',
    r'\bкриміналь\b': 'FF',
    
    # Author/biography
    r'\bавтобіограф|мемуа|біограф\b': 'DN',
    r'\bісторія\b': 'NH',
    r'\bалександр|тарас|іван|михайло\b': 'DC',  # Known authors
    
    # Children
    r'\bдит(яч|иних|яч)\b': 'Y',
    r'\bнасільк\b': 'Y',
    r'\bколисков\b': 'Y',
    r'\bдля діт\b': 'Y',
    
    # Education
    r'\bнавчальн|підручник|задачн\b': 'JN',
    r'\bсамонавчання\b': 'VS',
    
    # Art/Music/Film
    r'\bмистец|мистец|мусіки|музик|композит\b': 'AV',
    r'\bмальюван|живопис|дизайн\b': 'AB',
    r'\bкіно|фільм|кінемато\b': 'AP',
    r'\bскульптур|архітект\b': 'AB',
    
    # Non-fiction categories
    r'\bбізнес|бізнес-лі\b': 'KJJ',
    r'\bекономі\b': 'KC',
    r'\bфінанс\b': 'KFF',
    r'\bпсихолог\b': 'VFX',
    r'\bздоров|фітнес|спорт\b': 'WS',
    r'\bкулінар|рецепт|гастроном\b': 'WB',
    r'\bподоро|путівни|туризм\b': 'WH',
    r'\bрелігі\b': 'QR',
    r'\bфілософі\b': 'QD',
    r'\bнаук|фізик|хім|біолог|матем\b': 'P',
    r'\bкомп\'ютер|програм|програм\b': 'UM',
    
    # Comics/Graphic
    r'\bкомікс|графічн|манга\b': 'X',
    
    # Language learning
    r'\bмова|мовозн|граматик\b': 'CJ',
}

class ImprovedYakabooThemaMapper:
    def __init__(self):
        self.yakaboo_path = Path('data/yakaboo_categories_tree.json')
        self.config_path = Path('config/yakaboo_to_thema_mapping_improved.yaml')
        self.categories = []
        self.category_map = {}
        
    def load_categories(self):
        """Load Yakaboo categories"""
        with open(self.yakaboo_path, 'r', encoding='utf-8') as f:
            self.categories = json.load(f)
        
        for cat in self.categories:
            self.category_map[cat['id']] = cat
        
        print(f"✓ Loaded {len(self.categories)} categories")
    
    def extract_codes_from_name(self, name: str) -> Set[str]:
        """Extract THEMA codes from category name using pattern matching"""
        codes = set()
        name_lower = name.lower()
        
        for pattern, code in THEMA_PATTERNS.items():
            try:
                if re.search(pattern, name_lower):
                    codes.add(code)
            except re.error:
                pass
        
        return codes
    
    def get_category_path(self, cat_id: int) -> List[Dict]:
        """Get full path from root to this category"""
        path = []
        current = self.category_map.get(cat_id)
        
        while current:
            path.insert(0, current)
            parent_id = current.get('parent_id')
            current = self.category_map.get(parent_id) if parent_id else None
        
        return path
    
    def get_primary_thema_code(self, cat_id: int) -> List[str]:
        """Get THEMA code(s) for a category using path analysis"""
        path = self.get_category_path(cat_id)
        
        # Collect codes from entire path with priority to lower levels
        codes_by_level = defaultdict(set)
        for level_idx, cat in enumerate(path):
            extracted = self.extract_codes_from_name(cat['name'])
            for code in extracted:
                codes_by_level[level_idx].add(code)
        
        # Return codes prioritized by level (deepest level has highest priority)
        result = []
        for level in reversed(sorted(codes_by_level.keys())):
            result.extend(sorted(codes_by_level[level]))
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for code in result:
            if code not in seen:
                seen.add(code)
                unique.append(code)
        
        return unique[:3]  # Return top 3 codes max
    
    def is_book_category(self, cat_id: int) -> bool:
        """Check if category is book-related"""
        path = self.get_category_path(cat_id)
        
        book_keywords = ['книг', 'літератур', 'роман', 'повід', 'комікс', 'манга', 'вірш', 'поезі', 'басни']
        
        for cat in path:
            name_lower = cat['name'].lower()
            if any(kw in name_lower for kw in book_keywords):
                return True
        
        return False
    
    def generate_yaml(self) -> str:
        """Generate improved YAML mapping"""
        yaml = f"""# Yakaboo to THEMA Mapping (Improved)
# Uses intelligent path analysis for better classification
# Generated: {Path('data/yakaboo_categories_tree.json').stat().st_mtime}

version: "2.1"
description: "Yakaboo to THEMA mapping with hierarchical intelligence"
total_categories: {len(self.categories)}

# Mapping methodology:
#   - Analyzes full category path from root to leaf
#   - Matches keywords against pattern database
#   - Prioritizes codes from deepest levels
#   - Marks book-related categories for filtering

categories:
"""
        
        # Group by level
        by_level = defaultdict(list)
        for cat in self.categories:
            level = cat.get('level', 0)
            by_level[level].append(cat)
        
        # Generate entries
        for level in sorted(by_level.keys()):
            cats_at_level = sorted(by_level[level], key=lambda x: x['name'])
            yaml += f"\n  # ========== Level {level} ({len(cats_at_level)} categories) ==========\n"
            
            for cat in cats_at_level:
                codes = self.get_primary_thema_code(cat['id'])
                is_book = self.is_book_category(cat['id'])
                
                yaml += f"\n  '{cat['id']}':\n"
                yaml += f"    name: \"{cat['name'].replace(chr(34), chr(92)+chr(34))}\"\n"
                yaml += f"    level: {level}\n"
                yaml += f"    parent_id: {cat.get('parent_id', 'null')}\n"
                yaml += f"    thema_codes: {codes}\n"
                
                if is_book:
                    yaml += f"    is_book: true\n"
        
        return yaml
    
    def run(self):
        """Main execution"""
        print("\n🔄 Improved Yakaboo to THEMA Mapper\n")
        
        self.load_categories()
        
        print("🔄 Analyzing categories and extracting THEMA codes...")
        
        # Sample analysis
        categorized = 0
        total_codes = defaultdict(int)
        
        for cat in self.categories[:100]:  # Sample first 100
            codes = self.get_primary_thema_code(cat['id'])
            if codes:
                categorized += 1
                for code in codes:
                    total_codes[code] += 1
        
        print(f"✓ Sample: {categorized}/100 categories have codes")
        print(f"   Top codes: {sorted(total_codes.items(), key=lambda x: -x[1])[:10]}")
        
        print("\n🔄 Generating full YAML...")
        yaml = self.generate_yaml()
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml, encoding='utf-8')
        
        print(f"✅ Saved to: {self.config_path}")
        print(f"   File size: {len(yaml):,} bytes")

if __name__ == '__main__':
    mapper = ImprovedYakabooThemaMapper()
    mapper.run()
