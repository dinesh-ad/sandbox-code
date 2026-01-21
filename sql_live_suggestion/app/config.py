"""Configuration settings using pydantic-settings for type-safe environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Base directory for pickle files
    pickle_base_dir: str = "data"
    
    # Pickle file naming pattern: {base_dir}/metadata_{env}.pkl
    # e.g., data/metadata_prod.pkl, data/metadata_dev.pkl
    
    # Fuzzy matching configuration
    fuzzy_threshold: int = 50  # Minimum similarity score (0-100)
    max_suggestions: int = 5   # Maximum number of suggestions to return
    
    # API configuration
    api_prefix: str = "/api/v1"
    
    # Available environments
    available_environments: list[str] = ["prod", "stage", "qa", "dev"]
    
    model_config = SettingsConfigDict(
        env_prefix="SQL_SUGGESTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    def get_pickle_path(self, environment: str) -> str:
        """Get pickle file path for a specific environment."""
        return f"{self.pickle_base_dir}/metadata_{environment}.pkl"


# Singleton instance
settings = Settings()
