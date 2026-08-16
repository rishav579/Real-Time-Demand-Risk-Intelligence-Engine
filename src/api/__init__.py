"""Decision intelligence API package."""

from src.api.main import app, create_app
from src.api.routes import router
from src.api.schemas import (
    ExecutiveSummaryResponse,
    ForecastItemResponse,
    ForecastResponse,
    HealthResponse,
    InventoryItemResponse,
    InventoryResponse,
    RecommendationItemResponse,
    RecommendationResponse,
    RiskItemResponse,
    RiskResponse,
)
from src.api.service import IntelligenceService, get_intelligence_service

__all__ = [
    "app",
    "create_app",
    "router",
    "IntelligenceService",
    "get_intelligence_service",
    # Schemas
    "HealthResponse",
    "ExecutiveSummaryResponse",
    "ForecastItemResponse",
    "ForecastResponse",
    "RiskItemResponse",
    "RiskResponse",
    "InventoryItemResponse",
    "InventoryResponse",
    "RecommendationItemResponse",
    "RecommendationResponse",
]
