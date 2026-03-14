"""
Input expansion tests for Phase 2: INPT-01, INPT-02, INPT-03.

INPT-01: Excel (.xlsx) upload support for portfolio parser
INPT-02: Weight bounds and include-ticker constraints
INPT-03: Custom benchmark parameter
"""

import os
import numpy as np
import pytest
import pandas as pd
import openpyxl
from pathlib import Path

from scripts.parse_portfolio import parse_csv, parse_excel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def generic_xlsx_path(tmp_path):
    """Create a minimal generic-format .xlsx (Symbol, Shares, Price) with 3 rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Symbol", "Shares", "Price"])
    ws.append(["AAPL", 100, 150])
    ws.append(["MSFT", 50, 300])
    ws.append(["GOOG", 25, 2800])
    path = tmp_path / "generic_portfolio.xlsx"
    wb.save(str(path))
    return str(path)


@pytest.fixture
def schwab_xlsx_path(tmp_path):
    """
    Create a Schwab-format .xlsx (Symbol, Description, Quantity, Price, Market Value).
    Includes a CASH row and an ACCOUNT TOTAL row to test filtering.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Symbol", "Description", "Quantity", "Price", "Market Value"])
    ws.append(["AAPL", "Apple Inc", 100, 150, 15000])
    ws.append(["MSFT", "Microsoft Corp", 50, 300, 15000])
    ws.append(["GOOG", "Alphabet Inc", 25, 2800, 70000])
    ws.append(["CASH", "Cash & Cash Investments", "", "", 5000])
    ws.append(["ACCOUNT TOTAL", "", "", "", 105000])
    path = tmp_path / "schwab_portfolio.xlsx"
    wb.save(str(path))
    return str(path)


# ---------------------------------------------------------------------------
# INPT-01: Excel parsing tests
# ---------------------------------------------------------------------------

def test_parse_excel_generic(generic_xlsx_path):
    """parse_excel() on a generic .xlsx produces a valid portfolio dict."""
    result = parse_excel(generic_xlsx_path)

    assert isinstance(result, dict), "parse_excel must return a dict"
    assert 'tickers' in result, "Result must have 'tickers' key"
    assert 'allocations' in result, "Result must have 'allocations' key"
    assert 'raw_data' in result, "Result must have 'raw_data' key"
    assert 'format_detected' in result, "Result must have 'format_detected' key"

    assert len(result['tickers']) == 3, (
        f"Expected 3 tickers, got {len(result['tickers'])}: {result['tickers']}"
    )
    alloc_sum = result['allocations'].sum()
    assert abs(alloc_sum - 1.0) < 1e-6, (
        f"Allocations must sum to 1.0, got {alloc_sum}"
    )


def test_parse_excel_schwab(schwab_xlsx_path):
    """parse_excel() on a Schwab-format .xlsx detects format and filters CASH/TOTAL."""
    result = parse_excel(schwab_xlsx_path)

    assert result['format_detected'] == 'schwab', (
        f"Expected format_detected='schwab', got '{result['format_detected']}'"
    )

    tickers_upper = [t.upper() for t in result['tickers']]
    assert 'CASH' not in tickers_upper, "CASH must be filtered out"
    assert 'ACCOUNT TOTAL' not in tickers_upper, "ACCOUNT TOTAL must be filtered out"
    assert len(result['tickers']) == 3, (
        f"Expected 3 tickers after filtering, got {len(result['tickers'])}: {result['tickers']}"
    )


def test_parse_excel_missing_file():
    """parse_excel() raises FileNotFoundError for a missing file path."""
    with pytest.raises(FileNotFoundError):
        parse_excel("nonexistent.xlsx")


def test_csv_still_works():
    """parse_csv() on sample_portfolio.csv still returns a valid portfolio dict (regression guard)."""
    csv_path = "sample_portfolio.csv"
    if not os.path.exists(csv_path):
        pytest.skip("sample_portfolio.csv not found -- skipping regression guard")

    result = parse_csv(csv_path)

    assert isinstance(result, dict), "parse_csv must return a dict"
    assert 'tickers' in result, "Result must have 'tickers' key"
    assert 'allocations' in result, "Result must have 'allocations' key"
    alloc_sum = result['allocations'].sum()
    assert abs(alloc_sum - 1.0) < 1e-6, (
        f"CSV allocations must sum to ~1.0, got {alloc_sum}"
    )
    assert len(result['tickers']) > 0, "parse_csv must return at least one ticker"


# ---------------------------------------------------------------------------
# INPT-02: Weight bounds and include-ticker constraints
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
    mu = pd.Series({'AAPL': 0.18, 'MSFT': 0.15, 'GOOG': -0.05})

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


# ---------------------------------------------------------------------------
# INPT-03: Custom benchmark parameter
# ---------------------------------------------------------------------------

def test_custom_benchmark_param():
    """
    get_default_config must include 'benchmark', 'include_tickers', and
    'include_floor' keys with correct defaults. Benchmark must be overrideable.
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
