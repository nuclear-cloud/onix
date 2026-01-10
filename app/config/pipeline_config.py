"""
PHASE 3: PLUGGABLE CONFIGURATION & DEPENDENCY INJECTION
========================================================

Configuration system for dynamically selecting and configuring adapters.
Supports runtime adapter switching without modifying business logic.

Design Patterns:
- Factory Pattern: AdapterFactory creates adapters by name
- Registry Pattern: AdapterRegistry manages available adapters
- Dependency Injection: Settings injected at startup
"""
from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Type, List, Callable
from dataclasses import dataclass, field
from functools import lru_cache

import yaml
import json
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================

class AdapterType(str, Enum):
    """Supported adapter types."""
    YAKABOO = "yakaboo"
    KSD = "ksd"
    VIVAT = "vivat"
    LEGACY_API = "legacy_api"
    PARTNER_X = "partner_x"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0)
    pool_timeout: int = Field(default=30, ge=5)
    echo: bool = Field(default=False)


class AdapterConfig(BaseModel):
    """Configuration for a single adapter."""
    name: str = Field(..., description="Adapter display name")
    adapter_type: AdapterType
    enabled: bool = Field(default=True)
    priority: int = Field(default=100, ge=1)
    
    # Source-specific settings
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    batch_size: int = Field(default=1000, ge=1, le=10000)
    timeout_seconds: int = Field(default=30, ge=5)
    
    # Mapping overrides
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    
    # Feature flags
    features: Dict[str, bool] = Field(default_factory=lambda: {
        'validate_isbn_checksum': False,
        'skip_missing_isbn': True,
        'extract_all_images': True,
        'parse_description_html': True,
    })


class ImportConfig(BaseModel):
    """Batch import configuration."""
    batch_size: int = Field(default=1000, ge=1, le=10000)
    max_concurrent_batches: int = Field(default=4, ge=1, le=20)
    commit_every_n_batches: int = Field(default=5, ge=1)
    skip_on_error: bool = Field(default=True)
    log_every_n_records: int = Field(default=1000, ge=100)
    
    # Retry settings
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1)
    
    # Validation
    strict_mode: bool = Field(default=False)
    fail_fast: bool = Field(default=False)


class PipelineSettings(BaseSettings):
    """
    Main configuration for the data pipeline.
    
    Loads from:
    1. Environment variables (highest priority)
    2. YAML config file
    3. Default values
    """
    
    # Database
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(
        url=os.getenv('DATABASE_URL', 'postgresql+asyncpg://localhost/onix_db')
    ))
    
    # Active adapter
    active_adapter: AdapterType = Field(
        default=AdapterType.YAKABOO,
        description="Currently active data source adapter"
    )
    
    # Import settings
    import_config: ImportConfig = Field(default_factory=ImportConfig)
    
    # Adapter configurations
    adapters: Dict[str, AdapterConfig] = Field(default_factory=dict)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = None
    
    # Feature flags
    enable_embeddings: bool = Field(default=False)
    enable_price_history: bool = Field(default=True)
    enable_audit_log: bool = Field(default=True)
    
    model_config = {
        'env_prefix': 'PIPELINE_',
        'env_nested_delimiter': '__',
    }
    
    @classmethod
    def from_yaml(cls, path: str) -> 'PipelineSettings':
        """Load settings from YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, path: str) -> 'PipelineSettings':
        """Load settings from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(**data)
    
    def get_adapter_config(self, adapter_type: AdapterType = None) -> AdapterConfig:
        """Get configuration for specific or active adapter."""
        adapter_type = adapter_type or self.active_adapter
        
        if adapter_type.value in self.adapters:
            return self.adapters[adapter_type.value]
        
        # Return default config
        return AdapterConfig(
            name=adapter_type.value.title(),
            adapter_type=adapter_type
        )


# ============================================================================
# ADAPTER REGISTRY & FACTORY
# ============================================================================

class AdapterRegistry:
    """
    Registry for available adapters.
    
    Allows runtime registration and lookup of adapter classes.
    """
    
    _adapters: Dict[AdapterType, Type] = {}
    _instances: Dict[AdapterType, Any] = {}
    
    @classmethod
    def register(cls, adapter_type: AdapterType):
        """Decorator to register an adapter class."""
        def decorator(adapter_class: Type):
            cls._adapters[adapter_type] = adapter_class
            logger.info(f"Registered adapter: {adapter_type.value} -> {adapter_class.__name__}")
            return adapter_class
        return decorator
    
    @classmethod
    def get_class(cls, adapter_type: AdapterType) -> Optional[Type]:
        """Get adapter class by type."""
        return cls._adapters.get(adapter_type)
    
    @classmethod
    def get_instance(cls, adapter_type: AdapterType, **kwargs) -> Any:
        """Get or create adapter instance (singleton per type)."""
        if adapter_type not in cls._instances:
            adapter_class = cls.get_class(adapter_type)
            if adapter_class is None:
                raise ValueError(f"No adapter registered for type: {adapter_type}")
            cls._instances[adapter_type] = adapter_class(**kwargs)
        return cls._instances[adapter_type]
    
    @classmethod
    def clear_instances(cls):
        """Clear cached instances (for testing)."""
        cls._instances.clear()
    
    @classmethod
    def list_available(cls) -> List[AdapterType]:
        """List all registered adapter types."""
        return list(cls._adapters.keys())


class AdapterFactory:
    """
    Factory for creating adapters with configuration.
    
    Uses registry to find adapter classes and injects configuration.
    """
    
    def __init__(self, settings: PipelineSettings):
        self.settings = settings
    
    def create(self, adapter_type: AdapterType = None) -> Any:
        """
        Create an adapter instance with configuration.
        
        Args:
            adapter_type: Type of adapter to create. Uses active adapter if None.
            
        Returns:
            Configured adapter instance
        """
        adapter_type = adapter_type or self.settings.active_adapter
        config = self.settings.get_adapter_config(adapter_type)
        
        adapter_class = AdapterRegistry.get_class(adapter_type)
        if adapter_class is None:
            raise ValueError(f"No adapter registered for type: {adapter_type}")
        
        # Create instance with config
        return adapter_class()
    
    def create_all_enabled(self) -> Dict[AdapterType, Any]:
        """Create instances of all enabled adapters."""
        adapters = {}
        
        for adapter_type in AdapterRegistry.list_available():
            config = self.settings.get_adapter_config(adapter_type)
            if config.enabled:
                adapters[adapter_type] = self.create(adapter_type)
        
        return adapters


# ============================================================================
# REGISTER DEFAULT ADAPTERS
# ============================================================================

# Import and register adapters
from app.adapters.data_adapter import YakabooDataAdapter

AdapterRegistry.register(AdapterType.YAKABOO)(YakabooDataAdapter)


# ============================================================================
# GLOBAL SETTINGS LOADER
# ============================================================================

_settings: Optional[PipelineSettings] = None


def get_settings() -> PipelineSettings:
    """Get global pipeline settings (lazy loaded)."""
    global _settings
    if _settings is None:
        # Try to load from config file
        config_paths = [
            os.getenv('PIPELINE_CONFIG', ''),
            'config/pipeline.yaml',
            'config/pipeline.json',
            'pipeline.yaml',
            'pipeline.json',
        ]
        
        for path in config_paths:
            if path and Path(path).exists():
                if path.endswith('.yaml') or path.endswith('.yml'):
                    _settings = PipelineSettings.from_yaml(path)
                else:
                    _settings = PipelineSettings.from_json(path)
                logger.info(f"Loaded settings from: {path}")
                break
        
        if _settings is None:
            _settings = PipelineSettings()
            logger.info("Using default pipeline settings")
    
    return _settings


def configure_settings(settings: PipelineSettings):
    """Override global settings (for testing)."""
    global _settings
    _settings = settings


# ============================================================================
# EXAMPLE YAML CONFIG
# ============================================================================

EXAMPLE_CONFIG_YAML = """
# Pipeline Configuration
# Save as config/pipeline.yaml

# Active data source
active_adapter: yakaboo

# Database settings
database:
  url: ${DATABASE_URL}
  pool_size: 20
  max_overflow: 40
  pool_timeout: 30

# Import settings
import_config:
  batch_size: 2000
  max_concurrent_batches: 4
  commit_every_n_batches: 5
  skip_on_error: true
  log_every_n_records: 5000
  strict_mode: false

# Adapter configurations
adapters:
  yakaboo:
    name: "Yakaboo Catalog"
    adapter_type: yakaboo
    enabled: true
    priority: 1
    batch_size: 2000
    features:
      validate_isbn_checksum: false
      skip_missing_isbn: true
      extract_all_images: true
      parse_description_html: true
  
  ksd:
    name: "KSD Books"
    adapter_type: ksd
    enabled: false
    priority: 2
    base_url: "https://api.ksd.ua"
    api_key: ${KSD_API_KEY}
  
  vivat:
    name: "Vivat Publishing"
    adapter_type: vivat
    enabled: false
    priority: 3

# Logging
log_level: INFO
log_file: logs/pipeline.log

# Feature flags
enable_embeddings: false
enable_price_history: true
enable_audit_log: true
"""


def generate_example_config(output_path: str = "config/pipeline.yaml"):
    """Generate example configuration file."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(EXAMPLE_CONFIG_YAML)
    
    logger.info(f"Generated example config: {output_path}")
    return output_path
