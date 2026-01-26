"""
Metadata cache for loading and storing database metadata in memory.

This module handles loading pickle files and building optimized
data structures for fast lookups - no web framework dependencies.
"""

import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MetadataCache:
    """
    Cache holding database metadata with optimized lookup structures.
    
    Stores both original and normalized (lowercase) versions for:
    - O(1) exact match lookups using sets
    - Fast fuzzy matching using pre-computed lists
    - Original casing preservation using maps
    
    Example:
        cache = MetadataCache()
        cache.load_from_pickle("data/metadata_dev.pkl")
        
        # Check if table exists
        if cache.table_exists("student", schema="public"):
            print("Table found!")
        
        # Get candidates for fuzzy matching
        candidates = cache.get_table_candidates(schema="public")
    """
    
    # Raw hierarchical data (original casing)
    schemas: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    
    # Normalized sets for O(1) exact lookup
    schemas_set: set[str] = field(default_factory=set)
    tables_set: set[str] = field(default_factory=set)
    columns_set: set[str] = field(default_factory=set)
    
    # Normalized lists for fuzzy matching
    schemas_list: list[str] = field(default_factory=list)
    tables_list: list[str] = field(default_factory=list)
    columns_list: list[str] = field(default_factory=list)
    
    # Mapping: normalized -> original (to return original casing)
    schemas_map: dict[str, str] = field(default_factory=dict)
    tables_map: dict[str, str] = field(default_factory=dict)
    columns_map: dict[str, str] = field(default_factory=dict)
    
    # Context-aware lookups
    tables_by_schema: dict[str, set[str]] = field(default_factory=dict)
    tables_list_by_schema: dict[str, list[str]] = field(default_factory=dict)
    columns_by_table: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    columns_list_by_table: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    
    # Qualified names for display
    qualified_tables_list: list[str] = field(default_factory=list)
    qualified_tables_map: dict[str, str] = field(default_factory=dict)
    qualified_columns_list: list[str] = field(default_factory=list)
    qualified_columns_map: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    exported_at: str | None = None
    loaded_at: datetime | None = None
    is_loaded: bool = False
    environment: str = ""
    
    def load_from_pickle(self, pickle_path: str) -> None:
        """Load metadata from a pickle file."""
        path = Path(pickle_path)
        if not path.exists():
            raise FileNotFoundError(f"Pickle file not found: {pickle_path}")
        
        with open(path, "rb") as f:
            data: dict[str, Any] = pickle.load(f)
        
        self._build_from_raw_data(data)
        self.environment = data.get("environment", "")
        self.loaded_at = datetime.now()
        self.is_loaded = True
    
    def load_from_dict(self, data: dict[str, Any]) -> None:
        """Load metadata from a dictionary (same structure as pickle)."""
        self._build_from_raw_data(data)
        self.environment = data.get("environment", "")
        self.loaded_at = datetime.now()
        self.is_loaded = True
    
    def _build_from_raw_data(self, data: dict[str, Any]) -> None:
        """Build optimized data structures from raw data."""
        self.exported_at = data.get("exported_at")
        raw_schemas = data.get("schemas", {})
        
        self._reset_structures()
        self.schemas = raw_schemas
        
        for schema_name, schema_data in raw_schemas.items():
            schema_lower = schema_name.lower()
            
            # Schema level
            self.schemas_set.add(schema_lower)
            self.schemas_list.append(schema_lower)
            self.schemas_map[schema_lower] = schema_name
            
            # Initialize schema-level lookups
            self.tables_by_schema[schema_lower] = set()
            self.tables_list_by_schema[schema_lower] = []
            
            tables_data = schema_data.get("tables", {})
            
            for table_name, columns in tables_data.items():
                table_lower = table_name.lower()
                
                # Table level (global)
                self.tables_set.add(table_lower)
                if table_lower not in self.tables_map:
                    self.tables_list.append(table_lower)
                    self.tables_map[table_lower] = table_name
                
                # Table level (by schema)
                self.tables_by_schema[schema_lower].add(table_lower)
                self.tables_list_by_schema[schema_lower].append(table_lower)
                
                # Initialize table-level column lookups
                table_key = (schema_lower, table_lower)
                self.columns_by_table[table_key] = set()
                self.columns_list_by_table[table_key] = []
                
                # Qualified table name
                qualified_table = f"{schema_name}.{table_name}"
                qualified_table_lower = qualified_table.lower()
                self.qualified_tables_list.append(qualified_table_lower)
                self.qualified_tables_map[qualified_table_lower] = qualified_table
                
                for column_name in columns:
                    column_lower = column_name.lower()
                    
                    # Column level (global)
                    self.columns_set.add(column_lower)
                    if column_lower not in self.columns_map:
                        self.columns_list.append(column_lower)
                        self.columns_map[column_lower] = column_name
                    
                    # Column level (by table)
                    self.columns_by_table[table_key].add(column_lower)
                    self.columns_list_by_table[table_key].append(column_lower)
                    
                    # Qualified column name
                    qualified_column = f"{schema_name}.{table_name}.{column_name}"
                    qualified_column_lower = qualified_column.lower()
                    self.qualified_columns_list.append(qualified_column_lower)
                    self.qualified_columns_map[qualified_column_lower] = qualified_column
    
    def _reset_structures(self) -> None:
        """Reset all data structures."""
        self.schemas = {}
        self.schemas_set = set()
        self.tables_set = set()
        self.columns_set = set()
        self.schemas_list = []
        self.tables_list = []
        self.columns_list = []
        self.schemas_map = {}
        self.tables_map = {}
        self.columns_map = {}
        self.tables_by_schema = {}
        self.tables_list_by_schema = {}
        self.columns_by_table = {}
        self.columns_list_by_table = {}
        self.qualified_tables_list = []
        self.qualified_tables_map = {}
        self.qualified_columns_list = []
        self.qualified_columns_map = {}
    
    # ==================== EXISTS CHECKS (O(1)) ====================
    
    def schema_exists(self, name: str) -> bool:
        """Check if schema exists (case-insensitive)."""
        return name.lower() in self.schemas_set
    
    def table_exists(self, name: str, schema: str | None = None) -> bool:
        """Check if table exists, optionally within a schema."""
        table_lower = name.lower()
        if schema:
            tables = self.tables_by_schema.get(schema.lower(), set())
            return table_lower in tables
        return table_lower in self.tables_set
    
    def column_exists(
        self, name: str, schema: str | None = None, table: str | None = None
    ) -> bool:
        """Check if column exists, optionally within schema/table."""
        column_lower = name.lower()
        if schema and table:
            key = (schema.lower(), table.lower())
            columns = self.columns_by_table.get(key, set())
            return column_lower in columns
        return column_lower in self.columns_set
    
    # ==================== GET ORIGINAL CASING ====================
    
    def get_original_schema(self, normalized: str) -> str | None:
        """Get original casing for a schema name."""
        return self.schemas_map.get(normalized.lower())
    
    def get_original_table(self, normalized: str) -> str | None:
        """Get original casing for a table name."""
        return self.tables_map.get(normalized.lower())
    
    def get_original_column(self, normalized: str) -> str | None:
        """Get original casing for a column name."""
        return self.columns_map.get(normalized.lower())
    
    # ==================== GET CANDIDATES FOR FUZZY MATCHING ====================
    
    def get_schema_candidates(self) -> list[str]:
        """Get all schema names for fuzzy matching."""
        return self.schemas_list
    
    def get_table_candidates(self, schema: str | None = None) -> list[str]:
        """Get table names for fuzzy matching, optionally filtered by schema."""
        if schema:
            return self.tables_list_by_schema.get(schema.lower(), [])
        return self.tables_list
    
    def get_column_candidates(
        self, schema: str | None = None, table: str | None = None
    ) -> list[str]:
        """Get column names for fuzzy matching, optionally filtered."""
        if schema and table:
            key = (schema.lower(), table.lower())
            return self.columns_list_by_table.get(key, [])
        return self.columns_list
    
    # ==================== STATISTICS ====================
    
    def get_stats(self) -> dict:
        """Get statistics about the loaded metadata."""
        return {
            "is_loaded": self.is_loaded,
            "environment": self.environment,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "exported_at": self.exported_at,
            "schemas_count": len(self.schemas_set),
            "tables_count": len(self.tables_set),
            "columns_count": len(self.columns_set),
        }
