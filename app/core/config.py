from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import field_validator
import logging
import os

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application
    app_name: str = "PC Recommendation System"
    debug: bool = False
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # Database - Production ready for MongoDB Atlas
    mongodb_uri: str = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
    database_name: str = "pc_recommendation_prod"

    # Security
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # CORS
    allowed_origins: list[str] = []
    allowed_origin_regex: Optional[str] = None

    # API
    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env.local", case_sensitive=False, extra="ignore")

    def validate_on_startup(self):
        """Validate configuration on application startup"""
        validation_errors = []

        # Validate MongoDB URL
        if not self.mongodb_uri or not self.mongodb_uri.startswith(('mongodb://', 'mongodb+srv://')):
            validation_errors.append("Invalid MongoDB URL format")

        # In production, ensure no localhost
        if not self.debug:
            if "localhost" in self.mongodb_uri or "127.0.0.1" in self.mongodb_uri:
                validation_errors.append("Cannot use localhost MongoDB in production")
            for origin in self.allowed_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    validation_errors.append(f"Cannot allow localhost origins in production: {origin}")

        # Validate JWT secrets
        if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
            validation_errors.append("JWT secret key must be at least 32 characters long")

        if not self.secret_key or len(self.secret_key) < 32:
            validation_errors.append("Secret key must be at least 32 characters long")

        # Validate JWT timing
        if self.access_token_expire_minutes <= 0 or self.access_token_expire_minutes > 1440:
            validation_errors.append("JWT access token expiry must be between 1 and 1440 minutes")

        if self.jwt_refresh_token_expire_days <= 0 or self.jwt_refresh_token_expire_days > 365:
            validation_errors.append("JWT refresh token expiry must be between 1 and 365 days")

        # Validate CORS origins
        for origin in self.allowed_origins:
            if not origin.startswith(('http://', 'https://')):
                validation_errors.append(f"Invalid CORS origin format: {origin}")

        # Validate CORS origin regex if provided
        if self.allowed_origin_regex:
            if not isinstance(self.allowed_origin_regex, str):
                validation_errors.append("Allowed origin regex must be a string if provided")

        # Validate API prefix
        if not self.api_prefix.startswith('/'):
            validation_errors.append("API prefix must start with '/'")

        # Log validation results
        if validation_errors:
            logger.error("Configuration validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            raise ValueError("Configuration validation failed. Please check your environment variables.")

        logger.info("Configuration validation passed")

        # Warn about development defaults
        if self.debug:
            logger.warning("Running in DEBUG mode - not suitable for production")
        if self.jwt_secret_key == "super-secret-jwt-key-change-in-production-for-security":
            logger.warning("Using default JWT secret key - change in production!")
        if self.secret_key == "your-secret-key-change-in-production":
            logger.warning("Using default secret key - change in production!")

    def get_security_warnings(self) -> list:
        """Get list of security-related configuration warnings"""
        warnings = []

        if self.debug:
            warnings.append("Debug mode is enabled")

        if self.jwt_secret_key == "super-secret-jwt-key-change-in-production-for-security":
            warnings.append("Using default JWT secret key")

        if self.secret_key == "your-secret-key-change-in-production":
            warnings.append("Using default secret key")

        if "localhost" in self.mongodb_uri or "127.0.0.1" in self.mongodb_uri:
            warnings.append("Using localhost MongoDB - ensure it's secured in production")

        return warnings

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse JSON array for ALLOWED_ORIGINS env var"""
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("ALLOWED_ORIGINS must be a JSON array")
                return parsed
            except json.JSONDecodeError:
                raise ValueError("ALLOWED_ORIGINS must be valid JSON")
        return v


# Create settings instance and validate
settings = Settings()

# Validate configuration on import
try:
    settings.validate_on_startup()
except Exception as e:
    logger.error(f"Failed to validate configuration: {e}")
    raise
