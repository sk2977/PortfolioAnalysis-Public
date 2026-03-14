# Phase 3: Structured Output Schema Layer - Research

**Researched:** 2026-03-14
**Domain:** Pydantic v2 schema design, numpy/pandas type coercion, LLM structured output patterns
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SOUT-01 | Pydantic v2 schema defined for portfolio analysis results (MacroContext, PortfolioRecommendation, AllocationComparison) | Pipeline return shapes fully catalogued below. Three schemas map directly to the three primary pipeline output dicts. |
| SOUT-02 | Pipeline output dicts validated against Pydantic schemas with numpy/pandas type normalization | `@field_validator(mode='before')` with `.item()` for numpy scalars and `.to_dict()` for pandas Series/DataFrame is the verified pattern. No external libraries needed. |
| SOUT-03 | Claude produces structured JSON output block conforming to schema during Cowork sessions | `Model.model_json_schema()` generates the schema to embed in CLAUDE.md prompts. Claude then produces a JSON block that passes `Model.model_validate_json()`. |
| SOUT-04 | CLAUDE.md workflow updated with structured output instructions and schema references | CLAUDE.md already follows step-by-step pattern. New section added after Phase 6 (Report) with exact call site and schema name at each step. |
</phase_requirements>

---

## Summary

Phase 3 adds a thin validation wrapper around the pipeline's existing plain-dict outputs. The strategy decided in roadmap planning is "wrap, don't rewrite": pipeline functions keep returning plain dicts; `model_validate()` is called at integration points in the CLAUDE.md workflow, not inside the scripts. This keeps the scripts simple and testable independently.

The core technical challenge is that the pipeline produces numpy float64 scalars (from pandas operations), pandas Series objects (allocations), and pandas DataFrames (comparison, cov_matrix, erp_history). Pydantic v2 does not accept these natively as `float` or `dict` fields. The solution is `@field_validator(mode='before')` coercers that normalize these types before Pydantic's own validation runs. The `.item()` method on any numpy scalar converts it to a Python native type; pandas Series become dicts via `.to_dict()`.

For Claude's structured output (SOUT-03), the standard pattern is: embed `Model.model_json_schema()` in the Cowork prompt, Claude produces a fenced JSON block, caller validates with `Model.model_validate_json()`. No API key or streaming required -- this is purely a Claude Cowork in-conversation pattern. The schema module (`scripts/schemas.py`) is the single source of truth for all schema definitions and is imported both in validation calls and in CLAUDE.md code snippets.

**Primary recommendation:** Create `scripts/schemas.py` with three Pydantic v2 BaseModel classes using `@field_validator(mode='before')` for numpy/pandas coercion. Validate at three call sites in the CLAUDE.md workflow (after macro analysis, after optimize_portfolio, as Claude's structured output block). Test with pytest covering all four requirements.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0.0 | Schema definition, validation, JSON schema generation | Already in requirements.txt; v2 is the current major version with field_validator |
| numpy | >=1.24.0 | Source of float64 types that need coercion | Already in requirements.txt |
| pandas | >=2.0.0 | Source of Series/DataFrame types that need coercion | Already in requirements.txt |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic_numpy | optional | Typed numpy array fields | Not needed here -- we coerce OUT of numpy, not validate INTO it |
| numpydantic | optional | Full array shape/dtype validation | Overkill for this use case -- we want plain Python floats in schema |

**pydantic_numpy and numpydantic are explicitly NOT used here.** This pipeline's goal is to coerce pipeline outputs into JSON-serializable Python types (float, dict, list, str), not to validate numpy arrays within the model. Those libraries solve the opposite problem.

**Installation:** No new packages needed. `pydantic>=2.0.0` is already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
scripts/
    schemas.py          # NEW: all Pydantic BaseModel classes
    macro_analysis.py   # unchanged -- still returns plain dict
    optimize.py         # unchanged -- still returns plain dict
    parse_portfolio.py  # unchanged -- still returns plain dict
    ...
tests/
    test_sout.py        # NEW: SOUT-01 through SOUT-04 tests
```

### Pattern 1: numpy/pandas Coercion via field_validator mode='before'

**What:** A `@field_validator(..., mode='before')` runs before Pydantic's own type coercion. It receives the raw value (which may be numpy.float64, pd.Series, etc.) and must return a Python-native equivalent. Pydantic then validates the returned value against the declared field type.

**When to use:** Any field that will receive numpy or pandas types from pipeline output dicts.

**Key coercion rules:**
- `numpy.float64` and all numpy scalars have `.item()` which returns the Python native equivalent
- `pandas.Series` -> `.to_dict()` returns `{index_label: python_float, ...}`
- `pandas.DataFrame` -> `.to_dict(orient='records')` or `.to_dict()` depending on shape
- `Optional[float]` fields: check for None and pandas NA before calling `.item()`

**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/validators/
from typing import Any, Optional
from pydantic import BaseModel, field_validator

class PerformanceMetrics(BaseModel):
    """Return, volatility, Sharpe for current or optimal portfolio."""
    annual_return: float
    volatility: float
    sharpe: float

    @field_validator('annual_return', 'volatility', 'sharpe', mode='before')
    @classmethod
    def coerce_numpy_scalar(cls, v: Any) -> Any:
        # numpy scalars expose .item() to get Python native
        if hasattr(v, 'item'):
            return v.item()
        return v
```

```python
class MacroContext(BaseModel):
    pe_ratio: Optional[float] = None
    earnings_yield: Optional[float] = None
    treasury_yield: Optional[float] = None
    erp: Optional[float] = None
    interpretation: str
    stats: dict = {}
    # erp_history is excluded -- too large and not needed for LLM consumption

    @field_validator('pe_ratio', 'earnings_yield', 'treasury_yield', 'erp', mode='before')
    @classmethod
    def coerce_optional_numpy(cls, v: Any) -> Any:
        if v is None:
            return None
        if hasattr(v, 'item'):
            return v.item()
        return v

    @field_validator('stats', mode='before')
    @classmethod
    def coerce_stats_dict(cls, v: Any) -> Any:
        # stats dict values are numpy floats from pandas describe()
        if isinstance(v, dict):
            return {k: val.item() if hasattr(val, 'item') else val
                    for k, val in v.items()}
        return v
```

### Pattern 2: Pandas Series -> Dict Coercion for Allocation Fields

**What:** `optimal_allocations` and `current_allocations` are `pd.Series(index=ticker, values=weight)`. Schema represents these as `Dict[str, float]`.

**Example:**
```python
from typing import Dict

class AllocationComparison(BaseModel):
    """Current vs optimal weights with difference, sorted descending by difference."""
    current: Dict[str, float]
    optimal: Dict[str, float]
    difference: Dict[str, float]

    @field_validator('current', 'optimal', 'difference', mode='before')
    @classmethod
    def coerce_series_or_dict(cls, v: Any) -> Any:
        # pandas Series
        if hasattr(v, 'to_dict'):
            raw = v.to_dict()
            return {k: val.item() if hasattr(val, 'item') else float(val)
                    for k, val in raw.items()}
        # already a dict -- still coerce values
        if isinstance(v, dict):
            return {k: val.item() if hasattr(val, 'item') else val
                    for k, val in v.items()}
        return v
```

### Pattern 3: Constructing AllocationComparison from comparison DataFrame

The `optimize_portfolio()` result contains `comparison` as a `pd.DataFrame` with columns `['Current', 'Optimal', 'Difference']`. The schema expects three separate dict fields. Caller must unpack before validating:

```python
from scripts.schemas import AllocationComparison

comp_df = results['comparison']
validated = AllocationComparison.model_validate({
    'current': comp_df['Current'],
    'optimal': comp_df['Optimal'],
    'difference': comp_df['Difference'],
})
```

This is intentionally done at the call site (in CLAUDE.md workflow), not inside the schema, to keep schemas simple and testable.

### Pattern 4: LLM Structured Output via model_json_schema()

**What:** Claude (as the LLM) produces a JSON block conforming to the schema during a Cowork session. The caller validates it with `model_validate_json()`.

**When to use:** SOUT-03 -- any time Claude is asked to provide qualitative analysis in structured form (Phase 4 will rely heavily on this).

**Example:**
```python
# In CLAUDE.md (shown as Python code block for Cowork):
from scripts.schemas import PortfolioRecommendation
import json

schema = PortfolioRecommendation.model_json_schema()
# Embed schema in prompt: "Produce a JSON block matching this schema: {json.dumps(schema, indent=2)}"
# Claude produces:
json_block = '{"risk_tolerance": "moderate", "top_actions": [...], ...}'
validated = PortfolioRecommendation.model_validate_json(json_block)
```

**Constraint:** The schema must be fully JSON-serializable to work with `model_json_schema()`. This means no `arbitrary_types_allowed` with pandas types in the schema itself -- all fields must be Python native types (float, str, dict, list). The coercion validators ensure inputs can be numpy/pandas but outputs stored in the model are always native.

### Anti-Patterns to Avoid

- **Storing pd.Series or pd.DataFrame as schema fields:** Pydantic v2 cannot generate a JSON schema for these. Always coerce to dict or list in a before-validator.
- **Using `arbitrary_types_allowed=True` as a shortcut:** This breaks `model_json_schema()`, which is required for SOUT-03. Avoid entirely.
- **Putting validation calls inside pipeline scripts:** Breaks the "wrap, don't rewrite" decision. Keep validation in the orchestration layer (CLAUDE.md workflow code snippets and test fixtures).
- **Excluding `erp_history` from the schema after the fact:** Better to simply never include it -- it is a large DataFrame unsuitable for JSON. Define the schema to omit it from the start.
- **Using pydantic_numpy or numpydantic:** Adds a dependency and solves the wrong problem (validating array shapes INTO a model, not coercing OUT of numpy).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| numpy type detection | Custom isinstance checks per type | `hasattr(v, 'item')` duck-typing | Catches all numpy scalar subtypes (float32, float64, int64, etc.) without importing numpy in the schema module |
| pandas Series detection | `isinstance(v, pd.Series)` | `hasattr(v, 'to_dict')` duck-typing | Same duck-typing principle; avoids pandas import in schemas.py if desired |
| JSON schema generation | Manual dict describing schema | `Model.model_json_schema()` | Pydantic generates complete, correct JSON Schema draft 2020-12 from the model class |
| JSON validation | Manual `json.loads()` + type checks | `Model.model_validate_json(json_str)` | Single call validates and constructs the model; raises `ValidationError` with field-level detail |

**Key insight:** The coercion problem is ~10 lines of `hasattr` duck-typing per model. The real value of Pydantic here is `model_json_schema()` for SOUT-03 and `ValidationError` with readable field-level messages for debugging.

---

## Common Pitfalls

### Pitfall 1: numpy NaN vs None in Optional fields

**What goes wrong:** `macro['pe_ratio']` is `None` when the fetch fails, but it might also be `numpy.nan` or `float('nan')` from pandas operations. Pydantic's `Optional[float]` accepts None but not numpy.nan (it becomes `float('nan')` which is a valid float -- so it passes, but downstream JSON serialization may emit `NaN` which is not valid JSON).

**Why it happens:** `numpy.nan` is a Python float, not None. `float('nan')` passes `float` validation. `json.dumps({'x': float('nan')})` raises `ValueError` in standard library.

**How to avoid:** In the before-validator for Optional float fields, convert `float('nan')` and `numpy.nan` to `None` explicitly:
```python
import math
if v is not None and hasattr(v, 'item'):
    v = v.item()
if isinstance(v, float) and math.isnan(v):
    return None
return v
```

**Warning signs:** `json.dumps(model.model_dump())` raises `ValueError: Out of range float values are not JSON compliant`.

### Pitfall 2: stats dict has numpy float values, not Python float

**What goes wrong:** `macro['stats']` is built from `pd.Series.mean()`, `.std()` etc., all returning `numpy.float64`. A plain `stats: dict` field in Pydantic accepts the dict but the values remain numpy.float64. `model.model_dump()` will contain numpy objects that fail JSON serialization.

**Why it happens:** Pydantic v2 `dict` type annotation does not recurse into dict values for coercion. You must handle this in a before-validator.

**How to avoid:** Coerce all dict values in the `stats` before-validator (shown in Pattern 1 above).

**Warning signs:** `json.dumps(model.model_dump())` raises `TypeError: Object of type float64 is not JSON serializable`.

### Pitfall 3: method_results dict has nested numpy floats

**What goes wrong:** `results['method_results']` is `{'capm': {'weights': {...}, 'performance': {'return': np.float64(...), ...}}, ...}`. Including this in a schema field typed as `dict` will pass validation but still contain numpy types in the dump.

**Why it happens:** Same as Pitfall 2 -- Pydantic does not deep-coerce generic dicts.

**How to avoid:** Either (a) exclude method_results from the schema entirely (it is internal computation detail, not needed for LLM consumption), or (b) define a typed nested model for it. Recommendation: exclude it. The schema focuses on outputs Claude needs to consume and produce, not internal optimization internals.

**Warning signs:** `json.dumps(model.model_dump())` fails on deeply nested numpy values.

### Pitfall 4: model_json_schema() fails on complex types

**What goes wrong:** If any schema field type cannot be represented in JSON Schema (e.g., a pd.Series field without a custom schema), `model_json_schema()` raises `PydanticUserError`.

**Why it happens:** Pydantic v2 needs to be able to express every field type as a JSON Schema component to generate the full schema.

**How to avoid:** Keep all schema field types as Python natives: `float`, `str`, `int`, `bool`, `dict`, `list`, `Optional[...]`, `Dict[str, float]`, `List[str]`. The before-validators handle conversion from complex types into these native types before they reach field storage.

**Warning signs:** `PydanticUserError: Cannot generate a JsonSchema for core_schema.is_instance_schema` at import time.

### Pitfall 5: Calling model_validate() on the full results dict without unpacking

**What goes wrong:** `results` from `optimize_portfolio()` contains `cov_matrix` (DataFrame), `method_results` (nested dict with numpy values), `returns_dict` (dict of pd.Series). If the schema tries to validate the whole dict, complex fields will cause issues.

**Why it happens:** The schema should not try to represent every field returned by the pipeline -- only the fields needed for LLM consumption and downstream workflow.

**How to avoid:** Use explicit unpacking at the call site. Pass only the fields the schema defines:
```python
PortfolioRecommendation.model_validate({
    'optimal_allocations': results['optimal_allocations'],
    'performance': results['performance'],
    'config': results['config'],
})
```

---

## Code Examples

Verified patterns from official sources:

### Full schemas.py module structure

```python
# scripts/schemas.py
# Source: https://docs.pydantic.dev/latest/concepts/validators/
# Source: https://docs.pydantic.dev/latest/concepts/models/
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


def _coerce_numpy(v: Any) -> Any:
    """Convert numpy scalar to Python native. Handles None and NaN."""
    if v is None:
        return None
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _coerce_dict_values(d: Any) -> Any:
    """Recursively coerce dict values from numpy to Python native."""
    if not isinstance(d, dict):
        return d
    return {k: _coerce_numpy(val) for k, val in d.items()}


def _coerce_series_to_dict(v: Any) -> Any:
    """Convert pd.Series or dict with numpy values to Dict[str, float]."""
    if hasattr(v, 'to_dict'):
        raw = v.to_dict()
    elif isinstance(v, dict):
        raw = v
    else:
        return v
    return {str(k): _coerce_numpy(val) for k, val in raw.items()}


class MacroContext(BaseModel):
    pe_ratio: Optional[float] = None
    earnings_yield: Optional[float] = None
    treasury_yield: Optional[float] = None
    erp: Optional[float] = None
    interpretation: str = ""
    stats: Dict[str, Optional[float]] = {}
    # erp_history excluded: large DataFrame, not needed for LLM consumption

    @field_validator('pe_ratio', 'earnings_yield', 'treasury_yield', 'erp', mode='before')
    @classmethod
    def coerce_optional_float(cls, v: Any) -> Any:
        return _coerce_numpy(v)

    @field_validator('stats', mode='before')
    @classmethod
    def coerce_stats(cls, v: Any) -> Any:
        return _coerce_dict_values(v)


class PerformanceMetrics(BaseModel):
    annual_return: float
    volatility: float
    sharpe: float

    @field_validator('annual_return', 'volatility', 'sharpe', mode='before')
    @classmethod
    def coerce_float(cls, v: Any) -> Any:
        return _coerce_numpy(v)


class AllocationComparison(BaseModel):
    current: Dict[str, float]
    optimal: Dict[str, float]
    difference: Dict[str, float]

    @field_validator('current', 'optimal', 'difference', mode='before')
    @classmethod
    def coerce_allocation(cls, v: Any) -> Any:
        return _coerce_series_to_dict(v)


class PortfolioRecommendation(BaseModel):
    risk_tolerance: str
    optimization_method: str
    optimal_allocations: Dict[str, float]
    performance_current: PerformanceMetrics
    performance_optimal: PerformanceMetrics
    top_actions: List[str] = []   # For Claude to populate (SOUT-03)
    macro_summary: str = ""       # For Claude to populate (SOUT-03)
```

### Validation call sites (CLAUDE.md workflow)

```python
# After Phase 4 (Analysis) -- validate macro context
from scripts.schemas import MacroContext
macro_validated = MacroContext.model_validate(macro)

# After Phase 4 (Analysis) -- validate optimization results
from scripts.schemas import AllocationComparison, PortfolioRecommendation, PerformanceMetrics
comp_df = results['comparison']
alloc_validated = AllocationComparison.model_validate({
    'current': comp_df['Current'],
    'optimal': comp_df['Optimal'],
    'difference': comp_df['Difference'],
})

# Validate portfolio recommendation
rec_validated = PortfolioRecommendation.model_validate({
    'risk_tolerance': results['config']['risk_tolerance'],
    'optimization_method': results['config']['optimization_method'],
    'optimal_allocations': results['optimal_allocations'],
    'performance_current': results['performance']['current'],
    'performance_optimal': results['performance']['optimal'],
})
```

### LLM structured output call (SOUT-03)

```python
# Source: https://pydantic.dev/articles/llm-intro
import json
from scripts.schemas import PortfolioRecommendation

# Show schema to guide Claude:
schema = PortfolioRecommendation.model_json_schema()
print(json.dumps(schema, indent=2))

# Claude produces a JSON block -- validate it:
json_block = """{"risk_tolerance": "moderate", ...}"""
validated = PortfolioRecommendation.model_validate_json(json_block)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `@validator` | Pydantic v2 `@field_validator` + `mode='before'` | Pydantic 2.0 (2023) | Cleaner decorator, explicit mode, `@classmethod` required |
| Pydantic v1 `schema()` | Pydantic v2 `model_json_schema()` | Pydantic 2.0 (2023) | Returns JSON Schema draft 2020-12, directly usable as LLM structured output spec |
| `model.dict()` | `model.model_dump()` | Pydantic 2.0 (2023) | Old method still works but deprecated |
| `model.parse_obj(d)` | `model.model_validate(d)` | Pydantic 2.0 (2023) | Old method still works but deprecated |
| `model.parse_raw(s)` | `model.model_validate_json(s)` | Pydantic 2.0 (2023) | Old method still works but deprecated |

**Deprecated/outdated:**
- `@validator` (v1): Use `@field_validator` with explicit `mode=` parameter
- `schema()`: Use `model_json_schema()`
- `parse_obj()` / `parse_raw()`: Use `model_validate()` / `model_validate_json()`
- `arbitrary_types_allowed=True` when schema generation is needed: Breaks `model_json_schema()`. Use before-validators to coerce to native types instead.

---

## Open Questions

1. **`erp_history` DataFrame: exclude or serialize?**
   - What we know: It is a DataFrame of variable length, not needed for LLM consumption in Phase 3 or 4
   - What's unclear: Phase 4 might want to cite historical ERP stats -- but `stats` dict covers that
   - Recommendation: Exclude from schema entirely. If Phase 4 needs it, add a `erp_history_summary: dict` field then.

2. **`method_results` dict: exclude or model?**
   - What we know: Contains nested numpy floats from three optimization runs; needed for Phase 4 QUAL-03 (method disagreement disclosure)
   - What's unclear: Whether Phase 4 will validate method_results via schema or just read the raw dict
   - Recommendation: Exclude from Phase 3 schema. Phase 4 research should decide whether to model it.

3. **Claude's structured JSON output format in Cowork**
   - What we know: Claude can produce fenced code blocks with JSON; `model_validate_json()` accepts a plain JSON string
   - What's unclear: Whether Claude's JSON block needs to be extracted from a fenced block (i.e., strip the triple-backtick markers before parsing) -- this is MEDIUM confidence
   - Recommendation: CLAUDE.md workflow snippet should show the user how to strip fencing if needed: `json_str = json_block.strip().removeprefix('```json').removesuffix('```').strip()`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, pytest.ini present) |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run command | `pytest tests/test_sout.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOUT-01 | MacroContext, AllocationComparison, PortfolioRecommendation schemas exist and are importable | unit | `pytest tests/test_sout.py::test_schema_importable -x` | No -- Wave 0 |
| SOUT-02 | model_validate() on pipeline output dicts succeeds; numpy float64 and pd.Series coerced cleanly | unit | `pytest tests/test_sout.py::test_macro_context_coercion tests/test_sout.py::test_allocation_comparison_coercion -x` | No -- Wave 0 |
| SOUT-02 | NaN -> None coercion in Optional float fields | unit | `pytest tests/test_sout.py::test_nan_coercion -x` | No -- Wave 0 |
| SOUT-02 | model_dump() output is fully JSON-serializable (no numpy types leak through) | unit | `pytest tests/test_sout.py::test_model_dump_json_serializable -x` | No -- Wave 0 |
| SOUT-03 | model_validate_json() accepts a JSON string matching the schema | unit | `pytest tests/test_sout.py::test_validate_json_string -x` | No -- Wave 0 |
| SOUT-03 | model_json_schema() returns a non-empty dict (schema is generable) | unit | `pytest tests/test_sout.py::test_schema_generable -x` | No -- Wave 0 |
| SOUT-04 | CLAUDE.md contains validation call site instructions | manual | Read CLAUDE.md and verify section exists | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_sout.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_sout.py` -- covers SOUT-01, SOUT-02, SOUT-03 (6 test functions listed above)
- [ ] `scripts/schemas.py` -- the schema module itself must exist before any test can import it
- [ ] CLAUDE.md update -- SOUT-04 (manual verification, but file must be edited in Wave 0 or Wave 1)

*Framework already installed; conftest.py not needed (no shared fixtures required).*

---

## Sources

### Primary (HIGH confidence)
- https://docs.pydantic.dev/latest/concepts/validators/ -- field_validator syntax, mode='before', classmethod requirement
- https://docs.pydantic.dev/latest/concepts/models/ -- model_validate(), model_dump(), ConfigDict
- https://docs.pydantic.dev/latest/concepts/json_schema/ -- model_json_schema()
- https://pydantic.dev/articles/llm-intro -- model_json_schema() for LLM structured output pattern

### Secondary (MEDIUM confidence)
- https://pypi.org/project/pydantic_numpy/ -- confirmed pydantic_numpy exists but is not appropriate here
- https://machinelearningmastery.com/the-complete-guide-to-using-pydantic-for-validating-llm-outputs/ -- corroborates model_validate_json() pattern for LLM output validation

### Tertiary (LOW confidence)
- None -- all key claims verified with official Pydantic docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pydantic already in requirements.txt, v2 is current, all APIs verified in official docs
- Architecture: HIGH -- field_validator mode='before' pattern verified, coercion approach confirmed via official docs
- Pitfalls: HIGH -- numpy NaN/json serialization issue verified by code inspection of macro_analysis.py return structure; Pydantic dict limitation is a known documented behavior
- CLAUDE.md integration pattern: MEDIUM -- JSON fencing stripping is inferred from how Claude produces code blocks in Cowork; not explicitly tested

**Research date:** 2026-03-14
**Valid until:** 2026-09-14 (Pydantic v2 API is stable; unlikely to change in 6 months)
