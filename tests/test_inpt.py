"""
Input expansion tests for Phase 2: INPT-02, INPT-03.

INPT-02: Forced-include tickers -- optimizer must respect minimum floor weights
INPT-03: Custom benchmark selection -- config must support benchmark key
"""

import sys
import os
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# INPT-02: Weight bounds helper -- _build_weight_bounds
# ---------------------------------------------------------------------------

def test_weight_bounds_no_include():
    """
    _build_weight_bounds with no include_tickers must return scalar tuple
    (0, max_weight) for backward compatibility.
    """
    from scripts.optimize import _build_weight_bounds

    result = _build_weight_bounds(['AAPL', 'MSFT', 'GOOG'], max_weight=0.15)
    assert result == (0, 0.15), (
        f"Expected scalar tuple (0, 0.15) for no-include case, got: {result}"
    )


def test_weight_bounds_with_include():
    """
    _build_weight_bounds with include_tickers must return a per-ticker list
    where forced tickers get (include_floor, max_weight) and others get (0, max_weight).
    Also verifies case-insensitive matching.
    """
    from scripts.optimize import _build_weight_bounds

    tickers = ['AAPL', 'MSFT', 'GOOG']

    # Case-sensitive include
    result = _build_weight_bounds(
        tickers, max_weight=0.15,
        include_tickers=['MSFT'], include_floor=0.05
    )
    expected = [(0, 0.15), (0.05, 0.15), (0, 0.15)]
    assert result == expected, (
        f"Expected {expected}, got {result}"
    )

    # Case-insensitive include
    result_lower = _build_weight_bounds(
        tickers, max_weight=0.15,
        include_tickers=['msft'], include_floor=0.05
    )
    assert result_lower == expected, (
        f"Case-insensitive: expected {expected}, got {result_lower}"
    )


def test_include_ticker_forced():
    """
    Full optimization with include_tickers must produce non-zero weight for
    a ticker that would otherwise be zeroed by the optimizer.

    Uses synthetic price data where GOOG has flat/declining returns so the
    optimizer would naturally zero it without a forced floor.
    """
    import numpy as np
    import pandas as pd
    from pypfopt import risk_models, EfficientFrontier, objective_functions
    from scripts.optimize import _build_weight_bounds

    rng = np.random.default_rng(42)

    # 3 years of daily prices
    dates = pd.date_range('2021-01-01', periods=756, freq='B')

    # AAPL and MSFT: strong upward trend
    aapl = 100 * np.cumprod(1 + rng.normal(0.0010, 0.015, len(dates)))
    msft = 100 * np.cumprod(1 + rng.normal(0.0008, 0.014, len(dates)))
    # GOOG: flat/slightly declining (would be zeroed without floor)
    goog = 100 * np.cumprod(1 + rng.normal(-0.0005, 0.015, len(dates)))

    prices = pd.DataFrame({'AAPL': aapl, 'MSFT': msft, 'GOOG': goog}, index=dates)

    tickers = list(prices.columns)
    include_floor = 0.05

    cov_matrix = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
    mu = pd.Series(
        {'AAPL': 0.18, 'MSFT': 0.15, 'GOOG': -0.05}
    )

    bounds = _build_weight_bounds(
        tickers, max_weight=0.50,
        include_tickers=['GOOG'], include_floor=include_floor
    )

    ef = EfficientFrontier(mu, cov_matrix, weight_bounds=bounds)
    ef.add_objective(objective_functions.L2_reg, gamma=0.05)
    ef.max_sharpe(risk_free_rate=0.04)
    weights = ef.clean_weights()

    goog_weight = weights.get('GOOG', 0.0)
    assert goog_weight >= include_floor, (
        f"GOOG weight {goog_weight:.4f} should be >= include_floor {include_floor}"
    )


def test_custom_benchmark_param():
    """
    get_default_config must include 'benchmark', 'include_tickers', and
    'include_floor' keys with correct defaults.
    """
    from scripts.optimize import get_default_config

    config = get_default_config('moderate')

    assert 'benchmark' in config, "Config must have 'benchmark' key"
    assert config['benchmark'] == 'VTI', (
        f"Default benchmark must be 'VTI', got: {config['benchmark']!r}"
    )
    assert 'include_tickers' in config, "Config must have 'include_tickers' key"
    assert config['include_tickers'] == [], (
        f"Default include_tickers must be [], got: {config['include_tickers']!r}"
    )
    assert 'include_floor' in config, "Config must have 'include_floor' key"

    # Verify custom benchmark assignment works
    config['benchmark'] = 'SPY'
    assert config['benchmark'] == 'SPY', "Benchmark must be overrideable"
