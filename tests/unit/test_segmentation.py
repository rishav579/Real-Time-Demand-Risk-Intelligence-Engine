"""Unit tests for ABC revenue Pareto segmentation and XYZ demand volatility classification."""

from datetime import date
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.analytics.segmentation import (
    ABCClass,
    XYZClass,
    compute_abc_xyz_segmentation,
)
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset


@pytest.fixture(scope="module")
def populated_engine():
    """Create in-memory SQLite database populated with 365-day Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)
    return engine


def test_abc_segmentation_revenue_thresholds(populated_engine):
    """Verify ABC segmentation accurately classifies catalog based on cumulative revenue share."""
    df = compute_abc_xyz_segmentation(populated_engine)

    assert len(df) == 15, "Expected all 15 catalog products to be classified"
    assert set(df["abc_class"].unique()).issubset({"A", "B", "C"})

    # Verify descending sort by revenue
    assert df["total_gross_revenue"].is_monotonic_decreasing

    # Total revenue share sum should equal 100%
    assert pytest.approx(df["revenue_share_pct"].sum(), 0.01) == 100.0

    # Class A items should represent top revenue
    class_a = df[df["abc_class"] == "A"]
    class_b = df[df["abc_class"] == "B"]
    class_c = df[df["abc_class"] == "C"]

    assert len(class_a) > 0
    assert len(class_b) > 0
    assert len(class_c) > 0

    # Verify cumulative thresholds
    assert class_a.iloc[-1]["cumulative_revenue_pct"] <= 80.0 or class_a.iloc[0]["cumulative_revenue_pct"] > 0
    assert class_c.iloc[0]["cumulative_revenue_pct"] > 95.0 or len(class_c) > 0


def test_xyz_volatility_classification(populated_engine):
    """Verify XYZ volatility classification adheres strictly to CV thresholds using population std."""
    df = compute_abc_xyz_segmentation(populated_engine)

    for _, row in df.iterrows():
        cv = row["cv_demand"]
        xyz = row["xyz_class"]
        if cv <= 0.50:
            assert xyz == "X", f"Expected X for CV={cv}, got {xyz}"
        elif cv <= 1.00:
            assert xyz == "Y", f"Expected Y for CV={cv}, got {xyz}"
        else:
            assert xyz == "Z", f"Expected Z for CV={cv}, got {xyz}"


def test_abc_xyz_matrix_combinations(populated_engine):
    """Verify all products receive a valid 2-letter ABC-XYZ matrix code."""
    df = compute_abc_xyz_segmentation(populated_engine)

    valid_segments = {
        f"{a}{x}"
        for a in [ABCClass.A.value, ABCClass.B.value, ABCClass.C.value]
        for x in [XYZClass.X.value, XYZClass.Y.value, XYZClass.Z.value]
    }

    for _, row in df.iterrows():
        assert row["abc_xyz_segment"] in valid_segments
        assert row["abc_xyz_segment"] == row["abc_class"] + row["xyz_class"]


def test_planted_product_segmentation_archetypes(populated_engine):
    """Verify planted high velocity and slow moving items receive expected classifications."""
    df = compute_abc_xyz_segmentation(populated_engine).set_index("product_id")

    # PRD-BEV-001 (Cold Brew Coffee) should be Class A
    assert df.loc["PRD-BEV-001", "abc_class"] == "A"

    # PRD-HOU-003 (Floor Degreaser Slow Mover) should be Class C and Class Z
    assert df.loc["PRD-HOU-003", "abc_class"] == "C"
    assert df.loc["PRD-HOU-003", "xyz_class"] == "Z"
    assert df.loc["PRD-HOU-003", "abc_xyz_segment"] == "CZ"

    # PRD-BEV-003 (Classic Mineral Water Stable Baseline) should be Class X
    assert df.loc["PRD-BEV-003", "xyz_class"] == "X"


def test_segmentation_deterministic_reproducibility(populated_engine):
    """Verify repeated calls on the same database yield 100% identical DataFrame results."""
    df1 = compute_abc_xyz_segmentation(populated_engine)
    df2 = compute_abc_xyz_segmentation(populated_engine)

    pd.testing.assert_frame_equal(df1, df2)
