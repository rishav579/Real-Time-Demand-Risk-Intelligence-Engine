"""Unit tests for LightGBM gradient-boosted demand forecasting model."""

from datetime import date
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset
from src.forecasting.features import build_forecasting_dataset
from src.forecasting.model import LightGBMDemandForecaster
from src.forecasting.splits import create_temporal_splits


@pytest.fixture(scope="module")
def train_val_test_features():
    """Build and split engineered features from Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    feat_df = build_forecasting_dataset(engine)
    train_df, val_df, test_df = create_temporal_splits(feat_df)
    return train_df, val_df, test_df


def test_lightgbm_fit_and_predict_multi_horizon(train_val_test_features):
    """Verify LightGBM model fits and produces multi-horizon predictions without NaNs or negatives."""
    train_df, val_df, test_df = train_val_test_features
    model = LightGBMDemandForecaster(random_state=42)
    model.fit(train_df=train_df, val_df=val_df)

    for h in [7, 14, 30]:
        preds = model.predict(test_df=test_df, horizon_days=h)
        assert len(preds) == 60 * h  # 60 series * h steps
        assert preds["y_pred"].isna().sum() == 0
        assert (preds["y_pred"] >= 0.0).all()
        assert "model_name" in preds.columns
        assert (preds["model_name"] == "LightGBM").all()


def test_lightgbm_deterministic_seed_reproducibility(train_val_test_features):
    """Verify identical random_state=42 produces 100% identical predictions across runs."""
    train_df, val_df, test_df = train_val_test_features

    model1 = LightGBMDemandForecaster(random_state=42).fit(train_df, val_df)
    preds1 = model1.predict(test_df, horizon_days=14)

    model2 = LightGBMDemandForecaster(random_state=42).fit(train_df, val_df)
    preds2 = model2.predict(test_df, horizon_days=14)

    pd.testing.assert_frame_equal(preds1, preds2)


def test_lightgbm_feature_importances(train_val_test_features):
    """Verify feature importances are computed and top features reflect demand drivers."""
    train_df, val_df, _ = train_val_test_features
    model = LightGBMDemandForecaster(random_state=42).fit(train_df, val_df)

    imp_df = model.get_feature_importances()

    assert len(imp_df) == len(model.feature_cols)
    assert set(imp_df.columns) == {"feature", "importance_gain", "importance_split"}
    assert (imp_df["importance_gain"] >= 0).all()
    # Lags or rolling mean should be among top features
    top_features = imp_df.head(5)["feature"].tolist()
    assert any("lag" in f or "rolling" in f for f in top_features)
