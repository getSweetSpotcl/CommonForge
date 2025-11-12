"""
Configuration management for CommonForge.

Uses Pydantic Settings to load and validate environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str

    # OpenAI/LLM Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 1000

    # Web Scraping Configuration
    SCRAPER_TIMEOUT: int = 10
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_USER_AGENT: str = "CommonForge Lead Scorer/1.0"

    # Processing Configuration
    MAX_WEBSITE_TEXT_LENGTH: int = 3000
    CONCURRENT_LLM_CALLS: int = 3

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only load settings once.
    """
    return Settings()


# Global settings instance
settings = get_settings()


# Quick test to verify configuration loads
if __name__ == "__main__":
    print("Configuration loaded successfully!")
    print(f"Database URL: {settings.DATABASE_URL[:20]}...")
    print(f"OpenAI Model: {settings.OPENAI_MODEL}")
    print(f"Log Level: {settings.LOG_LEVEL}")
