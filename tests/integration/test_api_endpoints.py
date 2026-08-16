"""Integration tests for FastAPI REST API endpoints using TestClient."""

from datetime import date
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from src.api.main import create_app
from src.api.service import IntelligenceService, get_intelligence_service
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset


@pytest.fixture(scope="module")
def api_client():
    """Create test client with pre-populated in-memory test database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    service = IntelligenceService(engine=engine, as_of_date=date(2026, 12, 31))
    service.initialize()

    app = create_app()
    app.dependency_overrides[get_intelligence_service] = lambda: service

    with TestClient(app) as client:
        yield client


def test_endpoint_health(api_client):
    """Verify /health endpoint returns 200 OK and valid health payload."""
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["engine_version"] == "1.0.0"


def test_endpoint_summary(api_client):
    """Verify /summary endpoint returns network KPIs."""
    resp = api_client.get("/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_node_positions"] == 75
    assert data["total_locations"] == 5
    assert data["total_products"] == 15
    assert data["critical_stockout_risks"] > 0
    assert data["champion_model_name"] == "LightGBM"


def test_endpoint_forecast(api_client):
    """Verify /forecast endpoint with filtering and horizon."""
    resp = api_client.get("/forecast?location_id=LOC-ST-01&product_id=PRD-BEV-001&horizon_days=14")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 14
    assert data["horizon_days"] == 14
    assert len(data["items"]) == 14


def test_endpoint_risk(api_client):
    """Verify /risk endpoint with risk tier filter."""
    resp = api_client.get("/risk?risk_tier=CRITICAL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_positions"] > 0
    for pos in data["positions"]:
        assert pos["stockout_risk_tier"] == "CRITICAL"


def test_endpoint_inventory(api_client):
    """Verify /inventory endpoint."""
    resp = api_client.get("/inventory?location_id=LOC-DC-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 15


def test_endpoint_recommendations(api_client):
    """Verify /recommendations endpoint with priority filter."""
    resp = api_client.get("/recommendations?priority_tier=URGENT")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recommendations"] > 0
    for rec in data["recommendations"]:
        assert rec["priority_tier"] == "URGENT"


def test_prefixed_api_routes(api_client):
    """Verify /api/v1 prefix routes."""
    resp = api_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
