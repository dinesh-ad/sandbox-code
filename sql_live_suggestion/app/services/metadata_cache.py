"""Metadata cache service for loading and storing database metadata in memory."""

import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass
class EnvironmentCache:
    """
    Cache holding database metadata for a single environment.
    
    Stores both original and normalized (lowercase) versions for:
    - O(1) exact match lookups using sets
    - Fast fuzzy matching using pre-computed lists
    - Original casing preservation using maps
    """
    
    environment: str = ""
    
    # Raw hierarchical data (original casing)
    schemas: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    
    # Normalized sets for O(1) exact lookup
    schemas_set: set[str] = field(default_factory=set)
    tables_set: set[str] = field(default_factory=set)
    columns_set: set[str] = field(default_factory=set)
    
    # Normalized lists for fuzzy matching (rapidfuzz needs list/sequence)
    schemas_list: list[str] = field(default_factory=list)
    tables_list: list[str] = field(default_factory=list)
    columns_list: list[str] = field(default_factory=list)
    
    # Mapping: normalized -> original (to return original casing)
    schemas_map: dict[str, str] = field(default_factory=dict)
    tables_map: dict[str, str] = field(default_factory=dict)
    columns_map: dict[str, str] = field(default_factory=dict)
    
    # Context-aware lookups: schema -> tables, (schema, table) -> columns
    tables_by_schema: dict[str, set[str]] = field(default_factory=dict)
    tables_list_by_schema: dict[str, list[str]] = field(default_factory=dict)
    columns_by_table: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    columns_list_by_table: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    
    # Qualified names for suggestions (schema.table, schema.table.column)
    qualified_tables_list: list[str] = field(default_factory=list)
    qualified_tables_map: dict[str, str] = field(default_factory=dict)
    qualified_columns_list: list[str] = field(default_factory=list)
    qualified_columns_map: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    exported_at: str | None = None
    loaded_at: datetime | None = None
    is_loaded: bool = False
    
    def load(self, pickle_path: str, environment: str) -> None:
        """Load metadata from pickle file and build optimized data structures."""
        path = Path(pickle_path)
        if not path.exists():
            raise FileNotFoundError(f"Metadata pickle file not found: {pickle_path}")
        
        with open(path, "rb") as f:
            data: dict[str, Any] = pickle.load(f)
        
        self.environment = environment
        self._build_from_raw_data(data)
        self.loaded_at = datetime.now()
        self.is_loaded = True
    
    def _build_from_raw_data(self, data: dict[str, Any]) -> None:
        """Build optimized data structures from raw pickle data."""
        self.exported_at = data.get("exported_at")
        raw_schemas = data.get("schemas", {})
        
        # Reset all structures
        self._reset_structures()
        
        # Store raw hierarchical data
        self.schemas = raw_schemas
        
        # Build normalized structures
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
                
                # Qualified table name (schema.table)
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
                    
                    # Qualified column name (schema.table.column)
                    qualified_column = f"{schema_name}.{table_name}.{column_name}"
                    qualified_column_lower = qualified_column.lower()
                    self.qualified_columns_list.append(qualified_column_lower)
                    self.qualified_columns_map[qualified_column_lower] = qualified_column
    
    def _reset_structures(self) -> None:
        """Reset all data structures for reload."""
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
    
    def get_original_schema(self, normalized: str) -> str | None:
        """Get original casing for a schema name."""
        return self.schemas_map.get(normalized)
    
    def get_original_table(self, normalized: str) -> str | None:
        """Get original casing for a table name."""
        return self.tables_map.get(normalized)
    
    def get_original_column(self, normalized: str) -> str | None:
        """Get original casing for a column name."""
        return self.columns_map.get(normalized)
    
    def schema_exists(self, name: str) -> bool:
        """Check if schema exists (case-insensitive)."""
        return name.lower() in self.schemas_set
    
    def table_exists(self, name: str, schema: str | None = None) -> bool:
        """Check if table exists (case-insensitive), optionally within a schema."""
        table_lower = name.lower()
        if schema:
            schema_lower = schema.lower()
            tables = self.tables_by_schema.get(schema_lower, set())
            return table_lower in tables
        return table_lower in self.tables_set
    
    def column_exists(
        self, name: str, schema: str | None = None, table: str | None = None
    ) -> bool:
        """Check if column exists (case-insensitive), optionally within schema/table."""
        column_lower = name.lower()
        if schema and table:
            key = (schema.lower(), table.lower())
            columns = self.columns_by_table.get(key, set())
            return column_lower in columns
        return column_lower in self.columns_set
    
    def get_candidates_for_scope(
        self,
        scope: str,
        schema: str | None = None,
        table: str | None = None,
    ) -> list[str]:
        """Get the list of candidates for fuzzy matching based on scope and context."""
        if scope == "schema":
            return self.schemas_list
        
        if scope == "table":
            if schema:
                return self.tables_list_by_schema.get(schema.lower(), [])
            return self.tables_list
        
        if scope == "column":
            if schema and table:
                key = (schema.lower(), table.lower())
                return self.columns_list_by_table.get(key, [])
            return self.columns_list
        
        return []
    
    def get_original_for_scope(self, scope: str, normalized: str) -> str | None:
        """Get original casing for a normalized name based on scope."""
        if scope == "schema":
            return self.get_original_schema(normalized)
        if scope == "table":
            return self.get_original_table(normalized)
        if scope == "column":
            return self.get_original_column(normalized)
        return None
    
    def get_qualified_candidates_for_scope(
        self,
        scope: str,
        schema: str | None = None,
        table: str | None = None,
    ) -> list[str]:
        """Get qualified candidates for fuzzy matching."""
        if scope == "schema":
            return self.schemas_list
        
        if scope == "table":
            if schema:
                schema_lower = schema.lower()
                return [
                    q for q in self.qualified_tables_list 
                    if q.startswith(f"{schema_lower}.")
                ]
            return self.qualified_tables_list
        
        if scope == "column":
            if schema and table:
                prefix = f"{schema.lower()}.{table.lower()}."
                return [
                    q for q in self.qualified_columns_list 
                    if q.startswith(prefix)
                ]
            if schema:
                return [
                    q for q in self.qualified_columns_list 
                    if q.startswith(f"{schema.lower()}.")
                ]
            return self.qualified_columns_list
        
        return []
    
    def get_searchable_candidates_for_scope(
        self,
        scope: str,
        schema: str | None = None,
        table: str | None = None,
    ) -> list[tuple[str, str]]:
        """
        Get candidates for fuzzy matching with separate search key and display value.
        
        Returns list of (search_key, qualified_name) tuples where:
        - search_key: the name to match against (just the object name, not full path)
        - qualified_name: the full qualified name to display (schema.table.column)
        
        This ensures fuzzy matching is done on the actual name, not the path.
        """
        if scope == "schema":
            return [(name, name) for name in self.schemas_list]
        
        if scope == "table":
            # Match on table name only, return schema.table
            results = []
            for schema_name, tables in self.tables_by_schema.items():
                if schema and schema.lower() != schema_name:
                    continue
                for table_name in tables:
                    qualified = f"{schema_name}.{table_name}"
                    results.append((table_name, qualified))
            return results
        
        if scope == "column":
            # Match on column name only, return schema.table.column
            results = []
            for (schema_name, table_name), columns in self.columns_by_table.items():
                if schema and schema.lower() != schema_name:
                    continue
                if table and table.lower() != table_name:
                    continue
                for column_name in columns:
                    qualified = f"{schema_name}.{table_name}.{column_name}"
                    results.append((column_name, qualified))
            return results
        
        return []
    
    def get_original_qualified(self, scope: str, normalized: str) -> str | None:
        """Get original casing for a qualified normalized name."""
        if scope == "schema":
            return self.schemas_map.get(normalized)
        if scope == "table":
            return self.qualified_tables_map.get(normalized)
        if scope == "column":
            return self.qualified_columns_map.get(normalized)
        return None


class MetadataCacheManager:
    """
    Manager for multiple environment caches.
    
    Loads and manages separate pickle files for each environment:
    - data/metadata_prod.pkl
    - data/metadata_dev.pkl
    - data/metadata_stage.pkl
    - data/metadata_qa.pkl
    """
    
    def __init__(self) -> None:
        self._caches: dict[str, EnvironmentCache] = {}
        self._available_environments: list[str] = []
    
    def load_all_environments(self) -> dict[str, str]:
        """
        Load all available environment pickle files.
        
        Returns dict of {env: status} for each environment.
        """
        results = {}
        base_dir = Path(settings.pickle_base_dir)
        
        # Resolve relative path
        if not base_dir.is_absolute():
            app_dir = Path(__file__).parent.parent.parent
            base_dir = app_dir / settings.pickle_base_dir
        
        for env in settings.available_environments:
            pickle_path = base_dir / f"metadata_{env}.pkl"
            
            if pickle_path.exists():
                try:
                    cache = EnvironmentCache()
                    cache.load(str(pickle_path), env)
                    self._caches[env] = cache
                    self._available_environments.append(env)
                    results[env] = f"loaded ({len(cache.schemas_set)} schemas, {len(cache.tables_set)} tables)"
                except Exception as e:
                    results[env] = f"error: {str(e)}"
            else:
                results[env] = "file not found"
        
        return results
    
    def get_cache(self, environment: str) -> EnvironmentCache | None:
        """Get cache for a specific environment."""
        return self._caches.get(environment)
    
    def is_environment_loaded(self, environment: str) -> bool:
        """Check if an environment's cache is loaded."""
        cache = self._caches.get(environment)
        return cache is not None and cache.is_loaded
    
    @property
    def available_environments(self) -> list[str]:
        """Get list of environments with loaded caches."""
        return self._available_environments
    
    @property
    def is_any_loaded(self) -> bool:
        """Check if at least one environment cache is loaded."""
        return len(self._caches) > 0
    
    def get_all_stats(self) -> dict[str, dict]:
        """Get statistics for all loaded caches."""
        stats = {}
        for env, cache in self._caches.items():
            stats[env] = {
                "is_loaded": cache.is_loaded,
                "loaded_at": cache.loaded_at.isoformat() if cache.loaded_at else None,
                "exported_at": cache.exported_at,
                "schemas_count": len(cache.schemas_set),
                "tables_count": len(cache.tables_set),
                "columns_count": len(cache.columns_set),
            }
        return stats


# Singleton instance
metadata_cache_manager = MetadataCacheManager()
