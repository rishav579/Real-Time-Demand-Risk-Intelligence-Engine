"""Integration tests for FastAPI REST API endpoints using TestClient."""

from datetime import date
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from src.api.main import create_app
from src.api.service import IntelligenceService, get_intelligence_service
from src.config.settings import Settings, get_settings
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


def test_endpoint_invalid_location_returns_404(api_client):
    """Verify querying non-existent location returns 404 Not Found."""
    resp = api_client.get("/forecast?location_id=NON_EXISTENT_FACILITY")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_endpoint_invalid_product_returns_404(api_client):
    """Verify querying non-existent product returns 404 Not Found."""
    resp = api_client.get("/risk?product_id=NON_EXISTENT_SKU")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_prefixed_api_routes(api_client):
    """Verify /api/v1 prefix routes."""
    resp = api_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_auth_enforcement_on_protected_endpoints(monkeypatch, api_client):
    """Verify that when auth_enabled=True, unauthenticated requests fail with 401 and valid key succeeds."""
    # Temporarily enable authentication in settings
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: Settings(auth_enabled=True, api_key="secret-api-key-123"),
    )

    # 1. Health remains public
    health_resp = api_client.get("/health")
    assert health_resp.status_code == 200

    # 2. Protected endpoint without header returns 401
    unauth_resp = api_client.get("/summary")
    assert unauth_resp.status_code == 401
    assert "Invalid or missing API key" in unauth_resp.json()["detail"]

    # 3. Protected endpoint with invalid header returns 401
    invalid_resp = api_client.get("/summary", headers={"X-API-Key": "wrong-key"})
    assert invalid_resp.status_code == 401

    # 4. Protected endpoint with valid header returns 200 OK
    valid_resp = api_client.get("/summary", headers={"X-API-Key": "secret-api-key-123"})
    assert valid_resp.status_code == 200
    assert valid_resp.json()["total_node_positions"] == 75
