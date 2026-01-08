"""
ONIX Codelists Mapping for Yakaboo.
"""

from typing import Dict, Optional
from functools import lru_cache

# List 150: Product Form
BINDING_TO_ONIX: Dict[str, str] = {
    "тверда": "BB",
    "твердий": "BB",
    "hardcover": "BB",
    "м'яка": "BC",
    "мягка": "BC",
    "paperback": "BC",
    "електронна": "EB",
    "ebook": "EB",
    "аудіо": "AA",
    "audio": "AA",
}

@lru_cache(maxsize=1000)
def get_binding_code(binding: str) -> str:
    if not binding: return "BA" # Book
    return BINDING_TO_ONIX.get(binding.lower().strip(), "BA")

# List 74: Language Code
LANG_TO_ONIX: Dict[str, str] = {
    "ukr": "ukr",
    "укр": "ukr",
    "українська": "ukr",
    "eng": "eng",
    "англ": "eng",
    "англійська": "eng",
    "rus": "rus",
    "рос": "rus",
    "російська": "rus",
}

@lru_cache(maxsize=1000)
def get_lang_code(lang_name: str) -> Optional[str]:
    if not lang_name: return "ukr"
    name = str(lang_name).lower().strip()
    for k, v in LANG_TO_ONIX.items():
        if k in name: return v
    return "ukr"

PUBLICATION_TYPE_TO_ONIX = {"паперова": "00", "електронна": "ED", "аудіо": "AJ"}
ILLUSTRATION_TYPE_TO_ONIX = {"ч/б": "01", "кольорові": "02"}
AGE_TO_ONIX = {"підліткам": "13-17", "дітям": "3-12"}