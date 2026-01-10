"""
Universal Mapper Service
========================

Applies field mappings from configuration files to transform raw source data
into normalized catalog format.

Usage:
    mapper = UniversalMapper(YAKABOO_TO_CATALOG)
    catalog_data = mapper.apply(raw_yakaboo_data)
"""
from typing import Dict, Any, Optional, Callable, List


class MappingError(Exception):
    """Raised when required field mapping fails."""
    pass


class UniversalMapper:
    """
    Applies a mapping configuration to transform raw data.
    
    Features:
    - Validates required fields
    - Tracks missing/failed mappings
    - Provides detailed error messages
    """
    
    def __init__(self, mapping_config: Dict[str, Dict[str, Any]]):
        """
        Initialize mapper with a configuration.
        
        Args:
            mapping_config: Dict of {target_field: config_dict}
                Each config_dict has:
                    - source_fields: List[str]
                    - transform: Callable
                    - required: bool
                    - description: str
        """
        self.config = mapping_config
        self.stats = {
            'total_fields': len(mapping_config),
            'mapped': 0,
            'failed': 0,
            'missing_required': [],
            'missing_optional': [],
        }
    
    def apply(self, raw_data: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
        """
        Apply all mappings to raw data.
        
        Args:
            raw_data: Source data (e.g., Yakaboo JSON)
            strict: If True, raise error on missing required fields
        
        Returns:
            Transformed data ready for database
        
        Raises:
            MappingError: If strict=True and required field missing
        """
        result = {}
        self._reset_stats()
        
        for target_field, config in self.config.items():
            try:
                # Apply transform function
                value = config['transform'](raw_data)
                
                # Check if required field is missing
                if value is None and config.get('required', False):
                    self.stats['missing_required'].append(target_field)
                    if strict:
                        raise MappingError(
                            f"Required field '{target_field}' could not be mapped. "
                            f"Source fields: {config['source_fields']}"
                        )
                elif value is None:
                    self.stats['missing_optional'].append(target_field)
                else:
                    result[target_field] = value
                    self.stats['mapped'] += 1
                    
            except Exception as e:
                self.stats['failed'] += 1
                if config.get('required', False):
                    if strict:
                        raise MappingError(
                            f"Failed to map required field '{target_field}': {str(e)}"
                        ) from e
                # Log error but continue for optional fields
                # print(f"⚠️  Failed to map optional field '{target_field}': {str(e)}")
        
        return result
    
    def apply_single(
        self, 
        raw_data: Dict[str, Any], 
        target_field: str
    ) -> Optional[Any]:
        """
        Apply mapping for a single field.
        
        Args:
            raw_data: Source data
            target_field: Which field to map
        
        Returns:
            Mapped value or None
        """
        if target_field not in self.config:
            raise ValueError(f"Unknown target field: {target_field}")
        
        config = self.config[target_field]
        try:
            return config['transform'](raw_data)
        except Exception as e:
            # print(f"⚠️  Failed to map '{target_field}': {str(e)}")
            return None
    
    def validate(self, raw_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that all required fields can be mapped.
        
        Args:
            raw_data: Source data to validate
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        for target_field, config in self.config.items():
            if not config.get('required', False):
                continue
            
            try:
                value = config['transform'](raw_data)
                if value is None:
                    errors.append(
                        f"Required field '{target_field}' is None. "
                        f"Source: {config['source_fields']}"
                    )
            except Exception as e:
                errors.append(
                    f"Required field '{target_field}' failed: {str(e)}"
                )
        
        return len(errors) == 0, errors
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mapping statistics from last apply() call."""
        return self.stats.copy()
    
    def _reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            'total_fields': len(self.config),
            'mapped': 0,
            'failed': 0,
            'missing_required': [],
            'missing_optional': [],
        }
    
    def get_field_info(self, target_field: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration info for a specific field.
        
        Args:
            target_field: Field name to query
        
        Returns:
            Config dict or None if not found
        """
        return self.config.get(target_field)
    
    def list_required_fields(self) -> List[str]:
        """Get list of all required field names."""
        return [
            field for field, config in self.config.items()
            if config.get('required', False)
        ]
    
    def list_optional_fields(self) -> List[str]:
        """Get list of all optional field names."""
        return [
            field for field, config in self.config.items()
            if not config.get('required', False)
        ]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def explain_mapping(mapping_config: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate human-readable explanation of mappings.
    
    Args:
        mapping_config: Mapping configuration dict
    
    Returns:
        Formatted string explaining all mappings
    """
    lines = [
        "Field Mapping Summary",
        "=" * 60,
        ""
    ]
    
    # Group by required/optional
    required = []
    optional = []
    
    for field, config in mapping_config.items():
        info = {
            'field': field,
            'sources': ', '.join(config['source_fields']) if config['source_fields'] else '(computed)',
            'description': config['description'],
        }
        
        if config.get('required', False):
            required.append(info)
        else:
            optional.append(info)
    
    # Required fields
    lines.append(f"Required Fields ({len(required)}):")
    lines.append("-" * 60)
    for info in required:
        lines.append(f"  • {info['field']}")
        lines.append(f"    Source: {info['sources']}")
        lines.append(f"    {info['description']}")
        lines.append("")
    
    # Optional fields
    lines.append(f"Optional Fields ({len(optional)}):")
    lines.append("-" * 60)
    for info in optional:
        lines.append(f"  • {info['field']}")
        lines.append(f"    Source: {info['sources']}")
        lines.append(f"    {info['description']}")
        lines.append("")
    
    return "\n".join(lines)
