"""
Input expansion tests for Phase 2: INPT-01, INPT-02, INPT-03.

INPT-01: Excel (.xlsx) upload support for portfolio parser
INPT-02: Weight bounds and include-ticker constraints
INPT-03: Custom benchmark parameter
"""

import os
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
# INPT-02: Weight bounds and include-ticker constraints (stubs)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="INPT-02 not yet implemented")
def test_weight_bounds_no_include():
    """Optimization respects min/max weight bounds when no include-list is given."""
    assert False


@pytest.mark.xfail(reason="INPT-02 not yet implemented")
def test_weight_bounds_with_include():
    """Optimization forces included tickers above min bound even when optimizer would exclude them."""
    assert False


@pytest.mark.xfail(reason="INPT-02 not yet implemented")
def test_include_ticker_forced():
    """Include-ticker list forces specified tickers into the optimized portfolio."""
    assert False


# ---------------------------------------------------------------------------
# INPT-03: Custom benchmark parameter (stub)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="INPT-03 not yet implemented")
def test_custom_benchmark_param():
    """download_prices() accepts a custom benchmark ticker and uses it for comparison."""
    assert False
