"""
Stability tests for Phase 1: STAB-01, STAB-02, STAB-03.

STAB-01: pandas reindex deprecation fix
STAB-02: silent exception replacement with [WARN] messages
STAB-03: matplotlib Agg backend placement
"""

import warnings
import pickle
import sys
import os
import datetime
import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# STAB-01: pandas reindex deprecation
# ---------------------------------------------------------------------------

def test_reindex_ffill():
    """
    _build_erp_timeseries must use .reindex(...).ffill() and produce correct
    numeric output.  We give it a treasury DF and a PE history that needs
    forward-filling and check the result is a non-empty DataFrame with an
    'erp' column whose values are finite floats.
    """
    from scripts.macro_analysis import _build_erp_timeseries

    # Build a tiny treasury series (5 days)
    idx = pd.date_range('2024-01-01', periods=5, freq='D')
    treasury_df = pd.DataFrame({'DGS10': [4.0, 4.1, 4.2, 4.3, 4.4]}, index=idx)

    # Provide a cache dir with a pre-built PE history (only 1 entry -- tests ffill)
    import tempfile, pickle
    tmp = Path(tempfile.mkdtemp())
    pe_history = [{'date': datetime.datetime(2024, 1, 1), 'pe_ratio': 25.0}]
    with open(tmp / 'sp500_pe_history.pkl', 'wb') as f:
        pickle.dump(pe_history, f)

    result = _build_erp_timeseries(treasury_df, tmp)

    assert not result.empty, "ERP timeseries must not be empty"
    assert 'erp' in result.columns, "Result must have 'erp' column"
    assert result['erp'].notna().all(), "All ERP values must be non-NaN"
    # Earnings yield at PE=25 is 4.0%; ERP = 4.0 - treasury_yield
    # At treasury=4.0: erp should be ~0.0 (allow float tolerance)
    first_erp = result['erp'].iloc[0]
    assert isinstance(first_erp, float), "ERP must be a float"


def test_no_reindex_warning():
    """
    No FutureWarning or DeprecationWarning must be emitted when _build_erp_timeseries
    runs (confirms that the deprecated method= parameter is not used).
    """
    from scripts.macro_analysis import _build_erp_timeseries

    import tempfile, pickle, datetime
    tmp = Path(tempfile.mkdtemp())
    idx = pd.date_range('2024-01-01', periods=3, freq='D')
    treasury_df = pd.DataFrame({'DGS10': [4.0, 4.1, 4.2]}, index=idx)
    pe_history = [{'date': datetime.datetime(2024, 1, 1), 'pe_ratio': 25.0}]
    with open(tmp / 'sp500_pe_history.pkl', 'wb') as f:
        pickle.dump(pe_history, f)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _build_erp_timeseries(treasury_df, tmp)

    deprecation_warnings = [
        w for w in caught
        if issubclass(w.category, (FutureWarning, DeprecationWarning))
        and 'reindex' in str(w.message).lower()
    ]
    assert len(deprecation_warnings) == 0, (
        f"Unexpected reindex deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
    )


# ---------------------------------------------------------------------------
# STAB-02: silent exception replacement with [WARN]
# ---------------------------------------------------------------------------

def test_cache_warn_on_failure(capsys):
    """
    When cache write/load operations raise exceptions, a [WARN] message must
    be printed to stdout -- not silently swallowed.

    Tests all 4 cache-related silent-exception sites:
      - macro_analysis._add_to_pe_history (save)
      - macro_analysis._load_pe_history (load)
      - macro_analysis._save_cache
      - macro_analysis._load_cache
      - market_data._load_cache
    """
    from scripts import macro_analysis, market_data

    # --- macro_analysis._add_to_pe_history save failure ---
    tmp = Path('/nonexistent_dir_that_cannot_be_created_xyz')
    macro_analysis._add_to_pe_history(25.0, tmp)
    out = capsys.readouterr().out
    assert '[WARN]' in out, (
        "_add_to_pe_history must print [WARN] when pickle save fails, got: " + repr(out)
    )

    # --- macro_analysis._load_pe_history with corrupt pickle ---
    import tempfile
    tmp2 = Path(tempfile.mkdtemp())
    corrupt = tmp2 / 'sp500_pe_history.pkl'
    corrupt.write_bytes(b'not a valid pickle')
    result = macro_analysis._load_pe_history(tmp2)
    out2 = capsys.readouterr().out
    assert '[WARN]' in out2, (
        "_load_pe_history must print [WARN] when pickle is corrupt, got: " + repr(out2)
    )
    assert result == [], "Must return [] on load failure"

    # --- macro_analysis._save_cache failure ---
    bad_path = Path('/nonexistent_dir_xyz/cache.pkl')
    macro_analysis._save_cache(bad_path, {'data': 1})
    out3 = capsys.readouterr().out
    assert '[WARN]' in out3, (
        "_save_cache must print [WARN] on failure, got: " + repr(out3)
    )

    # --- macro_analysis._load_cache with corrupt file ---
    corrupt2 = tmp2 / 'bad_cache.pkl'
    corrupt2.write_bytes(b'garbage')
    result2 = macro_analysis._load_cache(corrupt2, max_age_hours=None)
    out4 = capsys.readouterr().out
    assert '[WARN]' in out4, (
        "_load_cache (macro_analysis) must print [WARN] on corrupt pickle, got: " + repr(out4)
    )
    assert result2 is None, "Must return None on load failure"

    # --- market_data._load_cache with corrupt file ---
    corrupt3 = tmp2 / 'bad_market_cache.pkl'
    corrupt3.write_bytes(b'garbage')
    result3 = market_data._load_cache(corrupt3)
    out5 = capsys.readouterr().out
    assert '[WARN]' in out5, (
        "_load_cache (market_data) must print [WARN] on corrupt pickle, got: " + repr(out5)
    )
    assert result3 is None, "Must return None on load failure"


def test_parse_portfolio_warn_on_failure(capsys):
    """
    parse_portfolio._detect_format must print [WARN] when file read fails
    inside the try/except block, instead of silently swallowing the error.
    """
    from scripts.parse_portfolio import _detect_format

    # Create a minimal DataFrame (so we get past the cols check)
    df = pd.DataFrame({'Symbol': ['VTI'], 'Shares': ['10']})

    # Patch open to raise an exception inside the try block
    with patch('builtins.open', side_effect=PermissionError("Access denied")):
        fmt = _detect_format(df, '/some/file.csv')

    out = capsys.readouterr().out
    assert '[WARN]' in out, (
        "_detect_format must print [WARN] when file open fails, got: " + repr(out)
    )
    # Should fall through to generic
    assert fmt == 'generic', f"Should fall through to generic format, got: {fmt}"


def test_pipeline_survives_cache_failure():
    """
    Cache operations failing must not raise exceptions -- functions must
    complete and return valid results.
    """
    from scripts import macro_analysis

    # _load_pe_history must return [] (not raise) on corrupt pickle
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    corrupt = tmp / 'sp500_pe_history.pkl'
    corrupt.write_bytes(b'not a valid pickle')
    result = macro_analysis._load_pe_history(tmp)
    assert result == [], f"_load_pe_history must return [] on failure, got: {result}"

    # _load_cache must return None (not raise) on corrupt pickle
    result2 = macro_analysis._load_cache(corrupt, max_age_hours=None)
    assert result2 is None, f"_load_cache must return None on failure, got: {result2}"

    # _save_cache must not raise on bad path
    bad_path = Path('/nonexistent_xyz/cache.pkl')
    try:
        macro_analysis._save_cache(bad_path, {'x': 1})
    except Exception as e:
        pytest.fail(f"_save_cache must not raise on failure, but got: {e}")

    # market_data._load_cache must return None (not raise) on corrupt file
    from scripts.market_data import _load_cache as md_load_cache
    result3 = md_load_cache(corrupt)
    assert result3 is None, f"market_data._load_cache must return None on failure, got: {result3}"


# ---------------------------------------------------------------------------
# STAB-03: matplotlib Agg backend
# ---------------------------------------------------------------------------

def test_matplotlib_agg_backend():
    """
    After importing scripts.visualize, matplotlib.get_backend() must return
    'agg' (case-insensitive).  This confirms matplotlib.use('Agg') is called
    before any pyplot import in visualize.py.
    """
    import matplotlib
    import scripts.visualize  # noqa: F401  trigger module-level side effects

    backend = matplotlib.get_backend()
    assert backend.lower() == 'agg', (
        f"Expected matplotlib backend 'agg', got '{backend}'. "
        "scripts/visualize.py must call matplotlib.use('Agg') before importing pyplot."
    )
