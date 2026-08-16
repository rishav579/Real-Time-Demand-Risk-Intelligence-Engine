"""Unit tests for IntelligenceService singleton and filtering logic."""

from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.api.service import IntelligenceService
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset


@pytest.fixture(scope="module")
def populated_service():
    """Create initialized IntelligenceService backed by in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    service = IntelligenceService(engine=engine, as_of_date=date(2026, 12, 31))
    service.initialize()
    return service


def test_service_executive_summary(populated_service):
    """Verify executive summary metrics from service."""
    summary = populated_service.get_executive_summary()

    assert summary["total_node_positions"] == 75
    assert summary["total_locations"] == 5
    assert summary["total_products"] == 15
    assert summary["critical_stockout_risks"] > 0
    assert summary["total_recommendations"] > 0
    assert summary["champion_model_name"] == "LightGBM"


def test_service_forecast_filtering(populated_service):
    """Verify forecast filtering by location and product."""
    fc_all = populated_service.get_forecasts(horizon_days=14)
    assert len(fc_all) == 60 * 14

    fc_filtered = populated_service.get_forecasts(
        location_id="LOC-ST-01",
        product_id="PRD-BEV-001",
        horizon_days=7,
    )
    assert len(fc_filtered) == 7
    assert (fc_filtered["location_id"] == "LOC-ST-01").all()
    assert (fc_filtered["product_id"] == "PRD-BEV-001").all()


def test_service_risk_filtering(populated_service):
    """Verify risk filtering by tier."""
    crit_risks = populated_service.get_risk_positions(risk_tier="CRITICAL")
    assert len(crit_risks) > 0
    assert (crit_risks["stockout_risk_tier"] == "CRITICAL").all()


def test_service_recommendation_filtering(populated_service):
    """Verify recommendation filtering by action type and priority tier."""
    dc_transfers = populated_service.get_recommendations(action_type="DC_TRANSFER")
    assert len(dc_transfers) > 0
    assert (dc_transfers["action_type"] == "DC_TRANSFER").all()

    urgent_recs = populated_service.get_recommendations(priority_tier="URGENT")
    assert len(urgent_recs) > 0
    assert (urgent_recs["priority_tier"] == "URGENT").all()


def test_service_concurrent_thread_safe_initialization():
    """Verify concurrent threads do not cause duplicate training or race conditions."""
    import concurrent.futures

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    service = IntelligenceService(engine=engine, as_of_date=date(2026, 12, 31))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(service.initialize) for _ in range(6)]
        for f in futures:
            f.result()

    assert service._initialized is True
    assert service._risk_nodes_df is not None
    assert len(service._risk_nodes_df) == 75
