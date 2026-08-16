"""Unit tests for safety stock and dynamic reorder point (ROP) calculations."""

import math
import pytest

from src.risk.safety_stock import (
    Z_SERVICE_LEVELS,
    calculate_safety_stock,
)


def test_safety_stock_tiered_abc_service_levels():
    """Verify safety stock scales according to ABC service levels (Class A > Class B > Class C)."""
    lt = 7
    sigma_lt = 1.5
    d_avg = 15.0
    sigma_d = 3.0

    ss_a = calculate_safety_stock(lt, sigma_lt, d_avg, sigma_d, abc_class="A")
    ss_b = calculate_safety_stock(lt, sigma_lt, d_avg, sigma_d, abc_class="B")
    ss_c = calculate_safety_stock(lt, sigma_lt, d_avg, sigma_d, abc_class="C")

    # Z-scores: A=2.05, B=1.65, C=1.28
    assert Z_SERVICE_LEVELS["A"] == 2.05
    assert Z_SERVICE_LEVELS["B"] == 1.65
    assert Z_SERVICE_LEVELS["C"] == 1.28

    assert ss_a > ss_b > ss_c
    assert pytest.approx(ss_a / Z_SERVICE_LEVELS["A"], 0.01) == pytest.approx(ss_b / Z_SERVICE_LEVELS["B"], 0.01)


def test_safety_stock_analytical_calculation():
    """Verify exact formula values on small known test parameters."""
    lt = 4
    sigma_lt = 1.0
    d_avg = 10.0
    sigma_d = 2.0
    # Combined variance = (4 * 4) + (100 * 1) = 16 + 100 = 116 -> sqrt(116) = 10.7703
    # For Class A (Z=2.05): SS = 2.05 * 10.7703 = 22.08
    expected_ss = round(2.05 * math.sqrt(116), 2)
    computed_ss = calculate_safety_stock(lt, sigma_lt, d_avg, sigma_d, abc_class="A")

    assert computed_ss == expected_ss
