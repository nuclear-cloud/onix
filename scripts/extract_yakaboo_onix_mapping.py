#!/usr/bin/env python3
"""
Extract and map Yakaboo categories to ONIX code lists.
Analyzes ONIX structure and creates intelligent mappings.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

class YakabooOnixMapper:
    def __init__(self):
        self.yakaboo_path = Path('data/yakaboo_categories_tree.json')
        self.onix_path = Path('data/ONIX_BookProduct_Codelists_Issue_71.json')
        self.config_path = Path('config/yakaboo_to_onix_mapping.yaml')
        self.categories = []
        self.onix_data = {}
        self.category_map = {}
        
    def load_data(self):
        """Load Yakaboo and ONIX data"""
        with open(self.yakaboo_path, 'r', encoding='utf-8') as f:
            self.categories = json.load(f)
        
        with open(self.onix_path, 'r', encoding='utf-8') as f:
            raw_onix = json.load(f)
        
        # Extract CodeLists from ONIX structure
        if 'ONIXCodeTable' in raw_onix:
            onix_table = raw_onix['ONIXCodeTable']
            for code_list in onix_table.get('CodeList', []):
                list_num = code_list.get('CodeListNumber')
                self.onix_data[list_num] = {
                    'description': code_list.get('CodeListDescription'),
                    'codes': code_list.get('Code', [])
                }
        
        # Build category map
        for cat in self.categories:
            self.category_map[cat['id']] = cat
        
        print(f"✓ Loaded {len(self.categories)} Yakaboo categories")
        print(f"✓ Loaded ONIX data with {len(self.onix_data)} code lists")
    
    def analyze_onix_structure(self) -> Dict:
        """Analyze ONIX structure"""
        analysis = {}
        
        for list_num, list_data in self.onix_data.items():
            codes = list_data.get('codes', [])
            analysis[list_num] = {
                'name': list_data.get('description', list_num),
                'total_codes': len(codes),
                'samples': [c.get('code') for c in codes[:5]]
            }
        
        return analysis
    
    def map_category_to_onix_lists(self, category_name: str) -> Dict[str, List[str]]:
        """Map a category to relevant ONIX code lists"""
        mappings = {}
        name_lower = category_name.lower()
        
        # List 83: Product Form mappings (hardcover, paperback, ebook, etc.)
        form_keywords = ['твердий', 'твёрдая', 'обкладинка', 'тверда', 'paperback', 'pocket', 'ebook', 'audiobook', 'аудіо']
        if any(kw in name_lower for kw in form_keywords):
            mappings['83'] = ['Product Form']
        
        # List 21: Product Type mappings
        type_keywords = ['book', 'журнал', 'comic', 'comic', 'manga', 'графічн', 'дитяч', 'підручник']
        if any(kw in name_lower for kw in type_keywords):
            mappings['21'] = ['Product Type']
        
        # List 93: Thema Subject Classification
        mappings['93'] = ['Thema Classification (same as THEMA)']
        
        # List 68: Language of Text
        lang_keywords = ['англійськ', 'русск', 'франц', 'німецьк', 'іспан', 'поль', 'японськ', 'китай']
        if any(kw in name_lower for kw in lang_keywords):
            mappings['68'] = ['Language']
        
        return mappings
    
    def generate_yaml(self) -> str:
        """Generate YAML mapping for ONIX"""
        yaml = f"""# Yakaboo to ONIX Code Mapping (Auto-generated)
# Maps Yakaboo e-commerce categories to ONIX standard code lists
# Date: {Path('data/ONIX_BookProduct_Codelists_Issue_71.json').stat().st_mtime}
#
# ONIX Code Lists:
#   21  = Product Type (book, journal, etc.)
#   68  = Language of Text (eng, ukr, rus, etc.)
#   83  = Product Form (hardcover, paperback, ebook, audiobook, etc.)
#   93  = Thema Subject Classification
#   96  = Digital Product Type
#   49  = Product Form Detail (PDF, EPUB, etc.)
#
# See: http://www.editeur.org/14/Code-Lists/

version: "2.0"
description: "Yakaboo category to ONIX code list mapping"
total_categories: {len(self.categories)}

# Primary Code Lists for Book Categorization
onix_code_lists:
  '21':
    name: "Product Type"
    description: "Distinguishes between books, journals, other publications"
    relevant_categories: ["Художня література", "Навчальна література", "Комікси", "Журнали"]
  
  '68':
    name: "Language of Text"
    description: "ISO 639 language codes for book content"
    relevant_categories: ["Українська літератури", "Англійська мова", "Французька мова"]
  
  '83':
    name: "Product Form"
    description: "Physical format: Hardcover, Paperback, Ebook, Audio, etc."
    codes:
      - "BC: Hardback"
      - "BB: Paperback"
      - "EA: Ebook"
      - "AF: Audiobook (downloadable)"
      - "BL: Colouring / Activity book"
  
  '93':
    name: "Thema Subject Classification"
    description: "Subject classification - same as THEMA codes"
    note: "Use mapping from yakaboo_to_thema_mapping_full.yaml"

# ONIX Codes Applicable to Yakaboo Categories
mappings_by_level:

  level_1:
    "1":  # Books root
      default_product_type: "02"  # Book
      applicable_lists: ["21", "68", "83", "93"]

  level_2:
    "fiction":
      product_type: "02"
      onix_codes:
        list_21: ["02"]  # Book
        list_93: ["F", "FC", "FF", "FM", "FR", "FK", "FJ", "FL", "FD", "DA", "DC"]
    
    "non_fiction":
      product_type: "02"
      onix_codes:
        list_21: ["02"]  # Book
        list_93: ["DNC", "NH", "L", "P", "KJJ", "VS", "JN"]
    
    "children":
      product_type: "02"
      onix_codes:
        list_21: ["02"]  # Book
        list_93: ["Y", "5A", "5AF", "5AH", "5AK", "YX"]
    
    "comics":
      product_type: "02"
      onix_codes:
        list_21: ["02"]  # Book (some systems use 10 for comics)
        list_83: ["BC", "BB"]  # Hardcover, Paperback
        list_93: ["X"]

  level_3_to_7:
    description: "Detailed subcategories inherit parent ONIX codes"
    mapping_strategy: |
      1. Inherit parent's list_21 (Product Type)
      2. Match category name against keyword patterns
      3. Add specific list_83 (Product Form) if applicable
      4. Assign list_93 (Thema) based on category content
      5. Assign list_68 (Language) if language-specific

# Sample Mappings by Yakaboo Category Type
category_templates:
  
  "Художня література":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["BC", "BB"]  # Can be hardcover or paperback
    list_93: ["F"]  # Fiction
    language_default: "68:ukr"

  "Навчальна література":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["BC", "BB"]
    list_93: ["JN"]  # Educational materials
    language_default: "68:ukr"

  "Комікси":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["BC", "BB", "BL"]  # Can be hardcover, paperback, or special format
    list_93: ["X"]  # Comics/Graphic novels

  "Комп'ютерні книги":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["BC", "BB", "EA"]  # Physical + digital
    list_93: ["U"]  # Information technology/Computers

  "Дитячі книги":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["BC", "BB"]
    list_93: ["Y"]  # Children's/Young adult

  "Електронні книги":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["EA"]  # Ebook/Digital
    list_93: ["F", "DNC", "Y"]  # Can be any subject

  "Аудіокниги":
    product_type: "02"  # Book
    list_21: "02"
    list_83: ["AF"]  # Audio download
    list_93: ["F", "DNC", "Y"]  # Can be any subject

# Notes on Implementation
notes: |
  - ONIX Product Type (21) will be determined by database table structure
  - Language (68) should be extracted from book metadata, default to 'ukr'
  - Product Form (83) depends on inventory/edition data in Yakaboo
  - Thema (93) should use values from yakaboo_to_thema_mapping_full.yaml
  - Some categories map to multiple ONIX lists depending on product variant
"""
        
        return yaml
    
    def run(self):
        """Main execution"""
        print("\n🔄 Yakaboo to ONIX Mapping Generator\n")
        
        self.load_data()
        
        print("\n📊 ONIX Structure Analysis:")
        analysis = self.analyze_onix_structure()
        for list_num, info in sorted(analysis.items()):
            print(f"   List {list_num}: {info['name']} ({info['total_codes']} codes)")
        
        print("\n🔄 Generating YAML mapping...")
        yaml = self.generate_yaml()
        
        # Save to file
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml, encoding='utf-8')
        
        print(f"✅ Saved to: {self.config_path}")
        print(f"   File size: {len(yaml):,} bytes")

if __name__ == '__main__':
    mapper = YakabooOnixMapper()
    mapper.run()
