"""
Application Configuration
Loads settings from environment variables / .env file.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Project Info ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = "FPT Customer Chatbot API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DESCRIPTION: str = (
        "A multi-agent AI chatbot REST API for FPT Software customers, "
        "supporting ticket management, bookings, IT support, and FAQ."
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # Use DATABASE_URL for AWS RDS/production, for example:
    # postgresql+psycopg2://postgres:<password>@<rds-endpoint>:5432/fastapi_prod
    DATABASE_URL: Optional[str] = None

    # SQLite remains the local development fallback.
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./fpt_chatbot.db"
    DATABASE_SSLMODE: Optional[str] = None
    DATABASE_SSLROOTCERT: Optional[str] = None

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL or self.SQLALCHEMY_DATABASE_URL

    @property
    def database_sslrootcert_path(self) -> Optional[str]:
        if not self.DATABASE_SSLROOTCERT:
            return None
        if os.path.isabs(self.DATABASE_SSLROOTCERT):
            return self.DATABASE_SSLROOTCERT
        return os.path.join(os.path.dirname(__file__), self.DATABASE_SSLROOTCERT)

    # ── JWT / Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── AI / LangGraph ────────────────────────────────────────────────────────
    ENABLE_AI_CHAT: bool = True
    OPENAI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # AWS / S3
    AWS_REGION: str = "ap-southeast-1"
    S3_BUCKET_NAME: str = ""
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    # ── Pydantic Configuration ───────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Inject into os.environ immediately so third-party libs can find them during import time
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
