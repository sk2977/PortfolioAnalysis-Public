# scripts/schemas.py
# Pydantic v2 schema definitions for portfolio analysis pipeline outputs.
# Strategy: "wrap, don't rewrite" -- pipeline functions return plain dicts;
# model_validate() is called at integration points only.
#
# Sources:
#   https://docs.pydantic.dev/latest/concepts/validators/
#   https://docs.pydantic.dev/latest/concepts/models/
#   https://docs.pydantic.dev/latest/concepts/json_schema/
import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Helper coercion functions (no numpy/pandas imports -- duck-typing only)
# ---------------------------------------------------------------------------

def _coerce_numpy(v: Any) -> Any:
    """Convert numpy scalar to Python native. Handles None and NaN.

    Uses hasattr duck-typing so this module never needs to import numpy.
    numpy scalars expose .item() which returns the Python native equivalent.
    float('nan') and numpy.nan are coerced to None so Optional[float] fields
    remain JSON-serializable (json.dumps raises ValueError on NaN).
    """
    if v is None:
        return None
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _coerce_dict_values(d: Any) -> Any:
    """Coerce all values in a dict from numpy scalars to Python native types.

    Does not recurse into nested dicts -- intended for flat stats dicts.
    """
    if not isinstance(d, dict):
        return d
    return {k: _coerce_numpy(val) for k, val in d.items()}


def _coerce_series_to_dict(v: Any) -> Any:
    """Convert pd.Series or dict with numpy values to Dict[str, float].

    Uses hasattr duck-typing to detect pd.Series without importing pandas.
    pd.Series exposes .to_dict() which returns {index_label: value}.
    """
    if hasattr(v, 'to_dict'):
        raw = v.to_dict()
    elif isinstance(v, dict):
        raw = v
    else:
        return v
    return {str(k): _coerce_numpy(val) for k, val in raw.items()}


# ---------------------------------------------------------------------------
# Schema: MacroContext
# ---------------------------------------------------------------------------

class MacroIndicator(BaseModel):
    """Single economic indicator from FRED."""
    value: Optional[float] = None
    yoy: Optional[float] = None
    date: Optional[str] = None
    symbol: Optional[str] = None

    @field_validator('value', 'yoy', mode='before')
    @classmethod
    def coerce_optional_float(cls, v: Any) -> Any:
        return _coerce_numpy(v)


class MacroContext(BaseModel):
    """Key economic indicators from get_macro_context().

    Raw timeseries data (data dict) and summary_df are intentionally
    excluded -- they are large DataFrames not needed for LLM consumption.
    """
    indicators: Dict[str, MacroIndicator] = {}
    interpretation: str = ""


# ---------------------------------------------------------------------------
# Schema: PerformanceMetrics
# ---------------------------------------------------------------------------

class PerformanceMetrics(BaseModel):
    """Return, volatility, and Sharpe ratio for current or optimal portfolio."""
    annual_return: float
    volatility: float
    sharpe: float

    @field_validator('annual_return', 'volatility', 'sharpe', mode='before')
    @classmethod
    def coerce_float(cls, v: Any) -> Any:
        return _coerce_numpy(v)


# ---------------------------------------------------------------------------
# Schema: AllocationComparison
# ---------------------------------------------------------------------------

class AllocationComparison(BaseModel):
    """Current vs optimal portfolio weights with per-ticker difference.

    Caller must unpack the comparison DataFrame before validating:
        AllocationComparison.model_validate({
            'current': comp_df['Current'],
            'optimal': comp_df['Optimal'],
            'difference': comp_df['Difference'],
        })
    """
    current: Dict[str, float]
    optimal: Dict[str, float]
    difference: Dict[str, float]

    @field_validator('current', 'optimal', 'difference', mode='before')
    @classmethod
    def coerce_allocation(cls, v: Any) -> Any:
        return _coerce_series_to_dict(v)


# ---------------------------------------------------------------------------
# Schema: PortfolioRecommendation
# ---------------------------------------------------------------------------

class PortfolioRecommendation(BaseModel):
    """Complete portfolio recommendation combining optimization results.

    Fields top_actions and macro_summary are populated by Claude (SOUT-03)
    during a Cowork session, not by the pipeline.

    Fields excluded from the pipeline results dict:
        method_results  -- internal optimization detail, nested numpy types
        cov_matrix      -- large DataFrame, not needed for LLM consumption
        returns_dict    -- dict of pd.Series, not needed for LLM consumption
    """
    risk_tolerance: str
    optimization_method: str
    optimal_allocations: Dict[str, float]
    performance_current: PerformanceMetrics
    performance_optimal: PerformanceMetrics
    top_actions: List[str] = []
    macro_summary: str = ""

    @field_validator('optimal_allocations', mode='before')
    @classmethod
    def coerce_allocations(cls, v: Any) -> Any:
        return _coerce_series_to_dict(v)
