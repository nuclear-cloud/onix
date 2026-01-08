"""
Helper Functions for Yakaboo Transformer.
"""

import re
from typing import Any, Dict, List, Optional, Union

def safe_get(data: dict, *keys, default=None):
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data

def to_list(val: Any) -> List[Any]:
    if val is None: return []
    if isinstance(val, list): return val
    return [val]

def extract_label_value(data: dict, field_base: str, index: int = 0) -> Optional[Any]:
    label_field = f"{field_base}_label"
    label_data = data.get(label_field)
    
    # Normalize to list
    if isinstance(label_data, dict):
        label_data = [label_data]
        
    try:
        if label_data and isinstance(label_data, list) and len(label_data) > index:
            label_obj = label_data[index]
            if isinstance(label_obj, dict):
                val = label_obj.get("label")
                if val: return val
    except:
        pass
        
    fallback = data.get(field_base)
    if fallback is not None:
        if isinstance(fallback, list):
            return fallback[0] if fallback else None
        return fallback
    return None

def parse_dimensions(binding_label: str) -> Dict[str, Optional[float]]:
    if not binding_label:
        return {"height": None, "width": None, "thickness": None}
    pattern = r'(\d+(?:[.,]\d+)?)\s*[хx]\s*(\d+(?:[.,]\d+)?)\s*(?:х|x)?\s*(\d+(?:[.,]\d+)?)?\s*(?:мм|mm)?'
    match = re.search(pattern, str(binding_label).lower())
    if match:
        try:
            h = float(match.group(1).replace(',', '.'))
            w = float(match.group(2).replace(',', '.'))
            t = float(match.group(3).replace(',', '.')) if match.group(3) else None
            return {"height": h, "width": w, "thickness": t}
        except: pass
    return {"height": None, "width": None, "thickness": None}

def normalize_string(value: Any) -> str:
    if value is None: return ""
    return str(value).strip()

def safe_int(value: Any, default: int = 0) -> int:
    try: return int(value)
    except: return default

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str):
            value = value.replace("г", "").replace("g", "").replace("мм", "").replace("mm", "").strip()
        return float(value)
    except: return default