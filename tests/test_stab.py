"""
Stability tests for Phase 1: STAB-02, STAB-03.

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
# STAB-02: silent exception replacement with [WARN]
# ---------------------------------------------------------------------------

def test_cache_warn_on_failure(capsys):
    """
    When cache write/load operations raise exceptions, a [WARN] message must
    be printed to stdout -- not silently swallowed.

    Tests market_data._load_cache with corrupt pickle file.
    """
    from scripts import market_data

    import tempfile
    tmp2 = Path(tempfile.mkdtemp())

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
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    corrupt = tmp / 'sp500_pe_history.pkl'
    corrupt.write_bytes(b'not a valid pickle')

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
