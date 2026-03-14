"""
Unit tests for Phase 3: Structured Output Schema Layer (SOUT-01, SOUT-02).

Tests cover:
- SOUT-01: Schema importability
- SOUT-02: numpy/pandas type coercion, NaN handling, JSON serializability
"""
import json
import math

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# SOUT-01: Schema importability
# ---------------------------------------------------------------------------

def test_schema_importable():
    """All four schema classes can be imported from scripts.schemas."""
    from scripts.schemas import (
        AllocationComparison,
        MacroContext,
        PerformanceMetrics,
        PortfolioRecommendation,
    )
    assert MacroContext is not None
    assert PerformanceMetrics is not None
    assert AllocationComparison is not None
    assert PortfolioRecommendation is not None


# ---------------------------------------------------------------------------
# SOUT-02: numpy/pandas coercion
# ---------------------------------------------------------------------------

def test_macro_context_coercion():
    """MacroContext.model_validate() accepts numpy.float64 values and returns Python float fields."""
    from scripts.schemas import MacroContext

    data = {
        'pe_ratio': np.float64(22.5),
        'earnings_yield': np.float64(0.044),
        'treasury_yield': np.float64(0.043),
        'erp': np.float64(0.001),
        'interpretation': 'Slightly elevated valuations',
        'stats': {
            'mean': np.float64(0.032),
            'std': np.float64(0.018),
            'min': np.float64(-0.05),
            'max': np.float64(0.12),
        },
    }
    model = MacroContext.model_validate(data)

    assert isinstance(model.pe_ratio, float)
    assert isinstance(model.earnings_yield, float)
    assert isinstance(model.treasury_yield, float)
    assert isinstance(model.erp, float)
    assert isinstance(model.interpretation, str)
    assert isinstance(model.stats, dict)
    # stats values should be Python float, not numpy
    for v in model.stats.values():
        assert isinstance(v, (float, type(None))), f"Expected float or None, got {type(v)}"


def test_allocation_comparison_coercion():
    """AllocationComparison.model_validate() accepts pd.Series for current, optimal, difference."""
    from scripts.schemas import AllocationComparison

    tickers = ['VTI', 'BND', 'QQQ']
    current = pd.Series([0.40, 0.30, 0.30], index=tickers)
    optimal = pd.Series([0.50, 0.25, 0.25], index=tickers)
    difference = optimal - current

    model = AllocationComparison.model_validate({
        'current': current,
        'optimal': optimal,
        'difference': difference,
    })

    assert isinstance(model.current, dict)
    assert isinstance(model.optimal, dict)
    assert isinstance(model.difference, dict)
    assert set(model.current.keys()) == set(tickers)
    # Values must be Python float, not numpy
    for v in model.current.values():
        assert isinstance(v, float), f"Expected float, got {type(v)}"


def test_nan_coercion():
    """MacroContext with numpy.nan pe_ratio stores None, not float('nan')."""
    from scripts.schemas import MacroContext

    data = {
        'pe_ratio': np.nan,
        'earnings_yield': None,
        'treasury_yield': np.float64(0.043),
        'erp': None,
        'interpretation': 'Data unavailable',
        'stats': {},
    }
    model = MacroContext.model_validate(data)

    assert model.pe_ratio is None, f"Expected None, got {model.pe_ratio}"
    assert model.earnings_yield is None
    # Verify no nan in dump -- json.dumps would raise ValueError on NaN
    dumped = model.model_dump()
    json_str = json.dumps(dumped)  # Must not raise ValueError
    assert json_str is not None


def test_model_dump_json_serializable():
    """model_dump() outputs for MacroContext and PortfolioRecommendation pass json.dumps()."""
    from scripts.schemas import MacroContext, PerformanceMetrics, PortfolioRecommendation

    macro_data = {
        'pe_ratio': np.float64(22.5),
        'earnings_yield': np.float64(0.044),
        'treasury_yield': np.float64(0.043),
        'erp': np.float64(0.001),
        'interpretation': 'Elevated',
        'stats': {'mean': np.float64(0.032)},
    }
    macro_model = MacroContext.model_validate(macro_data)
    json.dumps(macro_model.model_dump())  # Must not raise

    rec_data = {
        'risk_tolerance': 'moderate',
        'optimization_method': 'max_sharpe',
        'optimal_allocations': pd.Series([0.50, 0.30, 0.20], index=['VTI', 'BND', 'QQQ']),
        'performance_current': {
            'annual_return': np.float64(0.10),
            'volatility': np.float64(0.15),
            'sharpe': np.float64(0.60),
        },
        'performance_optimal': {
            'annual_return': np.float64(0.12),
            'volatility': np.float64(0.14),
            'sharpe': np.float64(0.78),
        },
        'top_actions': ['Increase VTI to 50%', 'Reduce QQQ to 20%'],
        'macro_summary': 'Market slightly elevated.',
    }
    rec_model = PortfolioRecommendation.model_validate(rec_data)
    json.dumps(rec_model.model_dump())  # Must not raise


def test_performance_metrics_coercion():
    """PerformanceMetrics.model_validate() accepts numpy.float64 values and returns Python floats."""
    from scripts.schemas import PerformanceMetrics

    data = {
        'annual_return': np.float64(0.10),
        'volatility': np.float64(0.15),
        'sharpe': np.float64(0.60),
    }
    model = PerformanceMetrics.model_validate(data)

    assert isinstance(model.annual_return, float)
    assert isinstance(model.volatility, float)
    assert isinstance(model.sharpe, float)
    assert math.isclose(model.annual_return, 0.10)
    assert math.isclose(model.volatility, 0.15)
    assert math.isclose(model.sharpe, 0.60)


def test_portfolio_recommendation_nested():
    """PortfolioRecommendation.model_validate() accepts nested dicts with numpy.float64 and pd.Series."""
    from scripts.schemas import PortfolioRecommendation

    data = {
        'risk_tolerance': 'moderate',
        'optimization_method': 'max_sharpe',
        'optimal_allocations': pd.Series([0.50, 0.30, 0.20], index=['VTI', 'BND', 'QQQ']),
        'performance_current': {
            'annual_return': np.float64(0.10),
            'volatility': np.float64(0.15),
            'sharpe': np.float64(0.60),
        },
        'performance_optimal': {
            'annual_return': np.float64(0.12),
            'volatility': np.float64(0.14),
            'sharpe': np.float64(0.78),
        },
    }
    model = PortfolioRecommendation.model_validate(data)

    assert model.risk_tolerance == 'moderate'
    assert model.optimization_method == 'max_sharpe'
    assert isinstance(model.optimal_allocations, dict)
    assert set(model.optimal_allocations.keys()) == {'VTI', 'BND', 'QQQ'}
    assert isinstance(model.performance_current.annual_return, float)
    assert isinstance(model.performance_optimal.sharpe, float)
    # Default fields
    assert model.top_actions == []
    assert model.macro_summary == ""
