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
    """All schema classes can be imported from scripts.schemas."""
    from scripts.schemas import (
        AllocationComparison,
        MacroContext,
        MacroIndicator,
        PerformanceMetrics,
        PortfolioRecommendation,
    )
    assert MacroContext is not None
    assert MacroIndicator is not None
    assert PerformanceMetrics is not None
    assert AllocationComparison is not None
    assert PortfolioRecommendation is not None


# ---------------------------------------------------------------------------
# SOUT-02: numpy/pandas coercion
# ---------------------------------------------------------------------------

def test_macro_context_coercion():
    """MacroContext.model_validate() accepts MacroIndicator dicts with numpy values."""
    from scripts.schemas import MacroContext

    data = {
        'indicators': {
            'ten_year': {
                'value': np.float64(4.14),
                'yoy': np.float64(-5.69),
                'date': '2025-12-01',
                'symbol': 'GS10',
            },
            'unemployment': {
                'value': np.float64(4.30),
                'yoy': np.float64(2.38),
                'date': '2025-08-01',
                'symbol': 'UNRATE',
            },
        },
        'interpretation': 'Moderate unemployment (4.3%)',
    }
    model = MacroContext.model_validate(data)

    assert isinstance(model.indicators['ten_year'].value, float)
    assert isinstance(model.indicators['ten_year'].yoy, float)
    assert isinstance(model.interpretation, str)


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
    """MacroIndicator with numpy.nan value stores None, not float('nan')."""
    from scripts.schemas import MacroContext

    data = {
        'indicators': {
            'ten_year': {
                'value': np.nan,
                'yoy': None,
                'date': '2025-12-01',
                'symbol': 'GS10',
            },
        },
        'interpretation': 'Data unavailable',
    }
    model = MacroContext.model_validate(data)

    assert model.indicators['ten_year'].value is None, \
        f"Expected None, got {model.indicators['ten_year'].value}"
    assert model.indicators['ten_year'].yoy is None
    # Verify no nan in dump -- json.dumps would raise ValueError on NaN
    dumped = model.model_dump()
    json_str = json.dumps(dumped)  # Must not raise ValueError
    assert json_str is not None


def test_model_dump_json_serializable():
    """model_dump() outputs for MacroContext and PortfolioRecommendation pass json.dumps()."""
    from scripts.schemas import MacroContext, PerformanceMetrics, PortfolioRecommendation

    macro_data = {
        'indicators': {
            'ten_year': {
                'value': np.float64(4.14),
                'yoy': np.float64(-5.69),
                'date': '2025-12-01',
                'symbol': 'GS10',
            },
        },
        'interpretation': 'Elevated',
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


# ---------------------------------------------------------------------------
# SOUT-03: JSON schema generation and validation
# ---------------------------------------------------------------------------

def test_schema_generable():
    """model_json_schema() returns a valid JSON Schema dict with 'properties' key."""
    from scripts.schemas import MacroContext, PortfolioRecommendation

    pr_schema = PortfolioRecommendation.model_json_schema()
    mc_schema = MacroContext.model_json_schema()

    assert isinstance(pr_schema, dict), "PortfolioRecommendation schema must be a dict"
    assert 'properties' in pr_schema, "PortfolioRecommendation schema must have 'properties' key"
    assert 'risk_tolerance' in pr_schema['properties'], "PortfolioRecommendation schema must have 'risk_tolerance' in properties"

    assert isinstance(mc_schema, dict), "MacroContext schema must be a dict"
    assert 'properties' in mc_schema, "MacroContext schema must have 'properties' key"
    assert 'indicators' in mc_schema['properties'], "MacroContext schema must have 'indicators' in properties"


def test_validate_json_string():
    """model_validate_json() accepts a plain JSON string conforming to PortfolioRecommendation schema."""
    from scripts.schemas import PortfolioRecommendation

    json_str = (
        '{"risk_tolerance": "moderate", "optimization_method": "max_sharpe",'
        ' "optimal_allocations": {"VTI": 0.5, "BND": 0.3, "QQQ": 0.2},'
        ' "performance_current": {"annual_return": 0.08, "volatility": 0.15, "sharpe": 0.53},'
        ' "performance_optimal": {"annual_return": 0.10, "volatility": 0.14, "sharpe": 0.71},'
        ' "top_actions": ["Increase VTI by 10%"], "macro_summary": "Market is fairly valued"}'
    )
    result = PortfolioRecommendation.model_validate_json(json_str)

    assert isinstance(result, PortfolioRecommendation), "Result must be a PortfolioRecommendation instance"
    assert result.risk_tolerance == "moderate"
    assert math.isclose(result.performance_optimal.sharpe, 0.71)
