---
phase: 03-structured-output-schema-layer
plan: 01
subsystem: testing
tags: [pydantic, pydantic-v2, numpy, pandas, schema, validation, json-serialization]

requires:
  - phase: 02-input-expansion
    provides: pipeline functions returning plain dicts with numpy/pandas types

provides:
  - Pydantic v2 BaseModel classes (MacroContext, PerformanceMetrics, AllocationComparison, PortfolioRecommendation)
  - numpy scalar coercion to Python float via _coerce_numpy (hasattr duck-typing)
  - pandas Series coercion to Dict[str, float] via _coerce_series_to_dict
  - numpy NaN -> None coercion for Optional[float] fields
  - JSON-serializable model_dump() output for all four schemas
  - 7-test unit test suite covering SOUT-01 and SOUT-02

affects:
  - phase 04 qualitative narrative (consumes MacroContext and PortfolioRecommendation)
  - CLAUDE.md workflow (integration call sites)

tech-stack:
  added: []
  patterns:
    - "Pydantic v2 field_validator(mode='before') with classmethod for numpy/pandas coercion"
    - "Duck-typing via hasattr(v, 'item') for numpy scalars, hasattr(v, 'to_dict') for pd.Series"
    - "NaN guard: math.isnan() after .item() for Optional float fields"
    - "No numpy/pandas imports in schemas.py -- duck-typing only"
    - "Wrap, don't rewrite: pipeline functions unchanged; model_validate() at integration points"

key-files:
  created:
    - scripts/schemas.py
    - tests/test_sout.py
  modified: []

key-decisions:
  - "Use hasattr duck-typing in schemas.py to avoid importing numpy/pandas in the schema module"
  - "numpy NaN coerced to None (not stored as float('nan')) to ensure json.dumps() compliance"
  - "erp_history DataFrame excluded from MacroContext schema -- large, not needed for LLM consumption"
  - "method_results, cov_matrix, returns_dict excluded from PortfolioRecommendation -- internal detail"

patterns-established:
  - "TDD RED/GREEN: write failing tests first, then implement minimal passing code"
  - "_coerce_numpy handles None, numpy scalar (.item()), and NaN->None in one function"
  - "AllocationComparison caller must unpack comparison DataFrame columns before model_validate()"

requirements-completed: [SOUT-01, SOUT-02]

duration: 2min
completed: 2026-03-14
---

# Phase 3 Plan 01: Structured Output Schema Layer Summary

**Pydantic v2 schema module with four BaseModel classes (MacroContext, PerformanceMetrics, AllocationComparison, PortfolioRecommendation) coercing numpy float64 and pandas Series to JSON-serializable Python types via duck-typed field_validator(mode='before') helpers.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T00:38:44Z
- **Completed:** 2026-03-14T00:40:47Z
- **Tasks:** 1 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- Four Pydantic v2 BaseModel classes exported from scripts/schemas.py with full numpy/pandas coercion
- NaN->None coercion in Optional[float] fields guarantees json.dumps() compliance
- 7 unit tests covering all SOUT-01 and SOUT-02 requirements pass; full suite (24 tests) remains green
- No numpy or pandas imports in schemas.py -- duck-typing only for portability

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: add failing tests for SOUT-01 and SOUT-02** - `7fafc25` (test)
2. **Task 1 GREEN: implement schema layer with coercion** - `062cc8b` (feat)

_TDD task: separate RED and GREEN commits per TDD execution flow._

## Files Created/Modified

- `scripts/schemas.py` - Four Pydantic v2 BaseModel classes with numpy/pandas coercion validators and helper functions
- `tests/test_sout.py` - 7 unit tests covering importability, numpy coercion, pandas Series coercion, NaN handling, JSON serializability, nested models

## Decisions Made

- Use hasattr duck-typing (hasattr(v, 'item') for numpy, hasattr(v, 'to_dict') for pandas) so schemas.py has no numpy/pandas import dependency -- cleaner and more portable
- NaN coerced to None after calling .item() using math.isnan() -- standard library only, no numpy needed
- erp_history DataFrame excluded from MacroContext schema (large, not needed for LLM consumption; documented in code comment)
- method_results, cov_matrix, returns_dict excluded from PortfolioRecommendation (internal optimization detail)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- scripts/schemas.py ready for Phase 4 qualitative narrative consumption
- MacroContext.model_validate(macro) and PortfolioRecommendation.model_validate({...}) call sites documented in RESEARCH.md
- AllocationComparison requires DataFrame column unpacking at call site (documented in code and RESEARCH.md)
- Phase 4 should test model_validate_json() for SOUT-03 (Claude structured JSON output in Cowork)

---
*Phase: 03-structured-output-schema-layer*
*Completed: 2026-03-14*

## Self-Check: PASSED
