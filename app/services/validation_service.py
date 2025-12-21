"""
Concept: Validation Service

This service enforces business rules and ONIX compliance.
It validates input data against ONIX codelists (e.g., Product Form codes)
and cross-field dependencies before data is persisted to the database.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Tuple

class ValidationService:
    """Service for validating ONIX codes against the ingested codelists."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_code(self, list_number: int, code_value: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a code value exists in a specific ONIX codelist.
        Returns (is_valid, error_message).
        """
        query = text("""
            SELECT description FROM codelist_values 
            WHERE list_number = :list_num AND code_value = :code_val AND is_active = TRUE
        """)
        result = await self.db.execute(query, {"list_num": list_number, "code_val": code_value})
        row = result.fetchone()
        
        if row:
            return True, None
        
        # If not found, get the list name for a better error message
        list_query = text("SELECT list_name FROM codelists WHERE list_number = :list_num")
        list_result = await self.db.execute(list_query, {"list_num": list_number})
        list_row = list_result.fetchone()
        list_name = list_row[0] if list_row else f"List {list_number}"
        
        return False, f"Неправильний код '{code_value}' для ONIX {list_name} (Список {list_number})"

    async def validate_product_metadata(self, product_data: dict) -> List[str]:
        """
        Perform cross-field and codelist validation for a product.
        Returns a list of error messages (empty if valid).
        """
        errors = []
        
        # 1. Validate Product Form (List 150)
        if "product_form" in product_data and product_data["product_form"]:
            is_valid, err = await self.validate_code(150, product_data["product_form"])
            if not is_valid:
                errors.append(err)
        
        # 2. Validate Language (List 74)
        if "language" in product_data and product_data["language"]:
            is_valid, err = await self.validate_code(74, product_data["language"])
            if not is_valid:
                errors.append(err)
                
        # 3. Validate Author Roles (List 17)
        if "authors" in product_data and product_data["authors"]:
            for author in product_data["authors"]:
                role = author.get("role_code", "A01")
                is_valid, err = await self.validate_code(17, role)
                if not is_valid:
                    errors.append(err)
        
        # 4. Validate ONIX JSON fields (Prices, Subjects, etc.)
        onix_json = product_data.get("onix_json")
        if onix_json:
            # Prices (List 58 for Price Type, List 96 for Currency)
            prices = onix_json.get("prices") or []
            for price in prices:
                ptype = price.get("price_type")
                if ptype:
                    is_valid, err = await self.validate_code(58, ptype)
                    if not is_valid: errors.append(err)
                
                currency = price.get("currency_code")
                if currency:
                    is_valid, err = await self.validate_code(96, currency)
                    if not is_valid: errors.append(err)
            
            # Text Content (List 153 for Text Type)
            texts = onix_json.get("text_content") or []
            for text_item in texts:
                ttype = text_item.get("text_type")
                if ttype:
                    is_valid, err = await self.validate_code(153, ttype)
                    if not is_valid: errors.append(err)
                    
        return errors
