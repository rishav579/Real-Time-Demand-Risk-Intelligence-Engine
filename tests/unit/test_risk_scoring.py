"""Unit tests for stockout risk scoring, severity tiers, and capital-at-risk."""

import pytest

from src.risk.risk_scoring import (
    StockoutRiskTier,
    calculate_stockout_risk_score,
    classify_stockout_tier,
)


def test_stockout_risk_score_normalization():
    """Verify Stockout Risk Score stays strictly within 0-100 bounds."""
    lt = 7

    # Runout at day 0 -> 100% risk
    assert calculate_stockout_risk_score(days_to_runout=0.0, lead_time_days=lt) == 100.0
    # Runout at half lead time (3.5d) -> 50% risk
    assert calculate_stockout_risk_score(days_to_runout=3.5, lead_time_days=lt) == 50.0
    # Runout at lead time (7d) -> 0% risk score (threshold of critical)
    assert calculate_stockout_risk_score(days_to_runout=7.0, lead_time_days=lt) == 0.0
    # Runout beyond lead time -> 0% risk score
    assert calculate_stockout_risk_score(days_to_runout=14.0, lead_time_days=lt) == 0.0
    # Infinite runout -> 0% risk score
    assert calculate_stockout_risk_score(days_to_runout=float("inf"), lead_time_days=lt) == 0.0


def test_classify_stockout_tier_boundaries():
    """Verify classification covers all 4 severity tiers."""
    lt = 10

    # 1. CRITICAL: DTR <= LT (<= 10)
    assert classify_stockout_tier(0.0, lt) == StockoutRiskTier.CRITICAL
    assert classify_stockout_tier(10.0, lt) == StockoutRiskTier.CRITICAL

    # 2. HIGH: LT < DTR <= 1.5 * LT (10 < DTR <= 15)
    assert classify_stockout_tier(10.1, lt) == StockoutRiskTier.HIGH
    assert classify_stockout_tier(15.0, lt) == StockoutRiskTier.HIGH

    # 3. MEDIUM: 1.5 * LT < DTR <= 2.0 * LT (15 < DTR <= 20)
    assert classify_stockout_tier(15.1, lt) == StockoutRiskTier.MEDIUM
    assert classify_stockout_tier(20.0, lt) == StockoutRiskTier.MEDIUM

    # 4. LOW: DTR > 2.0 * LT (> 20)
    assert classify_stockout_tier(20.1, lt) == StockoutRiskTier.LOW
    assert classify_stockout_tier(float("inf"), lt) == StockoutRiskTier.LOW
