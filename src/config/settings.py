"""Application configuration settings using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration parameters for Demand & Risk Intelligence Engine."""

    # Project metadata
    app_name: str = "Real-Time Demand & Risk Intelligence Engine"
    app_version: str = "1.0.0"
    environment: Literal["development", "testing", "production"] = "development"
    log_level: str = Field(default="INFO", description="Logging level")

    # Security & Authentication
    auth_enabled: bool = Field(
        default=False,
        description="Whether to enforce API key authentication on protected endpoints",
    )
    api_key: str = Field(
        default="dr-prod-secret-key-42",
        description="Static API key for service-to-service authentication",
    )
    allowed_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origin domains",
    )

    # Reproducibility & Random Seed
    random_seed: int = 42

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./demand_risk_engine.db",
        description="SQLAlchemy database connection string",
    )

    # Base Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data"
    )

    # Business Scenario Baseline Constants
    default_service_level: float = Field(
        default=0.95,
        ge=0.50,
        le=0.999,
        description="Target cycle service level for safety stock computation",
    )
    default_lead_time_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Default supplier lead time in days",
    )
    forecast_horizon_days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Short-term planning and demand forecast horizon in days",
    )

    model_config = SettingsConfigDict(
        env_prefix="DEMAND_RISK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
