"""
Configuration management for CyberScore.
Production: set DATABASE_URL and SECRET_KEY via env or Streamlit secrets.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings. Reads from .env and environment."""

    # Database (use DATABASE_URL env; on Streamlit Cloud set via Secrets)
    database_url: str = "sqlite:///./cyberscore.db"

    # Security (use SECRET_KEY env; must be 32+ chars in production)
    secret_key: str = "cyberscore-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"

    # Frontend Configuration
    frontend_port: int = 8501
    frontend_host: str = "127.0.0.1"

    # Security Settings
    password_min_length: int = 8
    password_require_special_chars: bool = True
    password_require_numbers: bool = True
    password_require_uppercase: bool = True

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "cyberscore.log"

    # Development
    debug: bool = False
    reload: bool = True

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @validator("password_min_length")
    def validate_password_min_length(cls, v):
        if v < 6:
            raise ValueError("Password minimum length must be at least 6")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
