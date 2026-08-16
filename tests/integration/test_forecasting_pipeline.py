"""Integration test for end-to-end multi-horizon demand forecasting and benchmark pipeline."""

from datetime import date
import pytest
from sqlalchemy import create_engine

from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset
from src.forecasting.evaluate import run_comprehensive_benchmark
from src.forecasting.features import build_forecasting_dataset
from src.forecasting.splits import create_temporal_splits


@pytest.fixture(scope="module")
def populated_engine():
    """Create in-memory SQLite database populated with 365-day Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)
    return engine


def test_end_to_end_forecasting_pipeline_and_benchmark(populated_engine):
    """Verify full demand forecasting pipeline from SQL extraction to multi-horizon evaluation."""
    # 1. Feature Engineering
    feat_df = build_forecasting_dataset(populated_engine)
    assert len(feat_df) == 21900

    # 2. Strict Chronological Splitting
    train_df, val_df, test_df = create_temporal_splits(feat_df)
    assert len(train_df) == 60 * 273  # 60 series x 273 train days = 16,380
    assert len(val_df) == 60 * 46     # 60 series x 46 val days = 2,760
    assert len(test_df) == 60 * 46    # 60 series x 46 test days = 2,760

    # 3. Comprehensive Multi-Horizon Benchmark
    results = run_comprehensive_benchmark(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        engine=populated_engine,
        horizons=[7, 14, 30],
    )

    # 4. Assert Benchmark Structure
    assert "global_summary" in results
    assert "horizon_summary" in results
    assert "segment_summary" in results
    assert "raw_predictions" in results

    global_summary = results["global_summary"].set_index("model_name")
    assert set(global_summary.index) == {"Naive", "SeasonalNaive", "ExponentialSmoothing", "LightGBM"}

    # Verify LightGBM produces valid WAPE and beats or matches Naive baseline
    lgb_wape = global_summary.loc["LightGBM", "wape"]
    naive_wape = global_summary.loc["Naive", "wape"]
    assert lgb_wape > 0.0
    assert lgb_wape < naive_wape, f"Expected LightGBM ({lgb_wape}) to beat Naive ({naive_wape})"

    # Verify Horizon breakdown
    horizon_summary = results["horizon_summary"]
    assert set(horizon_summary["horizon_days"].unique()) == {7, 14, 30}

    # Verify Segment breakdown
    segment_summary = results["segment_summary"]
    assert len(segment_summary) > 0
    assert "abc_class" in segment_summary.columns
    assert "xyz_class" in segment_summary.columns
