"""
Unit tests for Phase 4: Qualitative Narrative Layer (QUAL-01 through QUAL-04).

Tests cover:
- QUAL-01: macro_narrative param inserted into report
- QUAL-02: holding_commentary param inserted into report
- QUAL-03: _compute_method_spread() helper correctness
- QUAL-04: method_spread_note param and disclaimer preservation
"""
import math
from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Shared helper: minimal valid inputs for generate_report()
# ---------------------------------------------------------------------------

def _minimal_inputs():
    """Return minimal valid (optimization_results, macro_context, portfolio_info)."""
    return (
        {
            'config': {
                'risk_tolerance': 'moderate',
                'optimization_method': 'max_sharpe',
                'max_weight': 0.15,
            },
            'performance': {
                'current': {'return': 0.08, 'volatility': 0.15, 'sharpe': 0.53},
                'optimal': {'return': 0.10, 'volatility': 0.14, 'sharpe': 0.71},
            },
            'comparison': pd.DataFrame({
                'Current':    [0.40, 0.30, 0.30],
                'Optimal':    [0.50, 0.25, 0.25],
                'Difference': [0.10, -0.05, -0.05],
            }, index=['VTI', 'BND', 'QQQ']),
        },
        {
            'indicators': {
                'ten_year': {'value': 4.14, 'yoy': -5.69, 'date': '2025-12-01', 'symbol': 'GS10'},
                'unemployment': {'value': 4.30, 'yoy': 2.38, 'date': '2025-08-01', 'symbol': 'UNRATE'},
            },
            'interpretation': 'Moderate unemployment (4.3%)',
        },
        {'tickers': ['VTI', 'BND', 'QQQ']},
    )


# ---------------------------------------------------------------------------
# QUAL-01: macro_narrative
# ---------------------------------------------------------------------------

def test_macro_narrative_in_report():
    """macro_narrative text and header appear in report output when provided."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio,
                             macro_narrative="Test macro text")

    assert "Test macro text" in report
    assert "### Macro Interpretation" in report


def test_macro_narrative_absent_when_none():
    """'### Macro Interpretation' header does NOT appear when macro_narrative is None."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio)

    assert "### Macro Interpretation" not in report


# ---------------------------------------------------------------------------
# QUAL-02: holding_commentary
# ---------------------------------------------------------------------------

def test_holding_commentary_threshold():
    """holding_commentary dict entry and header appear when provided."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio,
                             holding_commentary={"VTI": "Increase VTI note"})

    assert "**VTI**: Increase VTI note" in report
    assert "### Holding Commentary" in report


def test_holding_commentary_absent_when_none():
    """'### Holding Commentary' header does NOT appear when holding_commentary is None."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio)

    assert "### Holding Commentary" not in report


# ---------------------------------------------------------------------------
# QUAL-03: _compute_method_spread()
# ---------------------------------------------------------------------------

def test_method_spread_calc():
    """_compute_method_spread() returns correct max_spread and flags tickers above 5pp threshold."""
    from scripts.report import _compute_method_spread

    # Ticker A: max=0.17 (ema), min=0.10 (capm) -> spread=0.07 (> 0.05, flagged)
    # Ticker B: max=0.09 (mean), min=0.08 (capm/ema) -> spread=0.01 (not flagged)
    returns_dict = {
        'capm': pd.Series([0.10, 0.08], index=['A', 'B']),
        'mean': pd.Series([0.12, 0.09], index=['A', 'B']),
        'ema':  pd.Series([0.17, 0.08], index=['A', 'B']),
    }

    max_spread, flagged = _compute_method_spread(returns_dict)

    assert math.isclose(max_spread, 0.07, rel_tol=1e-6), f"Expected 0.07, got {max_spread}"
    assert 'A' in flagged, "Ticker A with spread 0.07 should be flagged"
    assert 'B' not in flagged, "Ticker B with spread 0.01 should NOT be flagged"


def test_method_spread_calc_nan_safe():
    """_compute_method_spread() does not raise when one method has NaN for a ticker."""
    import math as _math
    from scripts.report import _compute_method_spread

    returns_dict = {
        'capm': pd.Series([0.10, float('nan')], index=['A', 'B']),
        'mean': pd.Series([0.12, 0.09],          index=['A', 'B']),
        'ema':  pd.Series([0.15, 0.08],           index=['A', 'B']),
    }

    # Should not raise; result must be a valid float
    max_spread, flagged = _compute_method_spread(returns_dict)
    assert isinstance(max_spread, float)
    assert not _math.isnan(max_spread)


# ---------------------------------------------------------------------------
# QUAL-04: method_spread_note and disclaimer preservation
# ---------------------------------------------------------------------------

def test_method_spread_note_in_report():
    """method_spread_note text appears in report with 'Confidence Note' label."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio,
                             method_spread_note="Confidence disclaimer text")

    assert "Confidence disclaimer text" in report
    assert "Confidence Note" in report


def test_disclaimer_present():
    """Disclaimer text appears and is after all narrative sections when all params provided."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(
        results, macro, portfolio,
        macro_narrative="Macro narrative text",
        holding_commentary={"VTI": "VTI note"},
        method_spread_note="Spread note text",
    )

    assert "educational and informational" in report

    # Disclaimer must appear after all narrative sections
    disclaimer_pos = report.index("educational and informational")
    for section in ["Macro narrative text", "VTI note", "Spread note text"]:
        assert report.index(section) < disclaimer_pos, (
            f"'{section}' must appear before disclaimer"
        )


def test_backward_compat():
    """generate_report() with only the original 4 positional args returns a string without error."""
    from scripts.report import generate_report

    results, macro, portfolio = _minimal_inputs()
    report = generate_report(results, macro, portfolio, [])

    assert isinstance(report, str)
    assert len(report) > 0


# ---------------------------------------------------------------------------
# COWK-03: README Cowork setup section
# ---------------------------------------------------------------------------

def test_readme_cowork_section():
    """COWK-03: README contains Cowork setup instructions."""
    readme_path = Path(__file__).parent.parent / 'README.md'
    content = readme_path.read_text(encoding='utf-8')
    assert 'Cowork' in content, "README must mention Cowork"
    assert 'clone' in content.lower(), "README must include clone step"
    assert 'upload' in content.lower() or 'portfolio' in content.lower(), "README must mention uploading portfolio"
