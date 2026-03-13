---
phase: 01-stability-and-cowork-hardening
plan: 01
subsystem: testing
tags: [pytest, pandas, matplotlib, pickle, caching]

# Dependency graph
requires: []
provides:
  - pytest scaffold with 6 stability tests (tests/test_stab.py)
  - Fixed pandas reindex deprecation in macro_analysis._build_erp_timeseries
  - [WARN] messages replacing 6 silent except Exception: pass sites
  - Confirmed matplotlib Agg backend in visualize.py
affects: [all future phases that import macro_analysis, market_data, parse_portfolio]

# Tech tracking
tech-stack:
  added: [pytest 9.0.2]
  patterns: [TDD red-green for stability regressions, print [WARN] for cache failures]

key-files:
  created:
    - pytest.ini
    - tests/__init__.py
    - tests/test_stab.py
  modified:
    - scripts/macro_analysis.py
    - scripts/market_data.py
    - scripts/parse_portfolio.py

key-decisions:
  - "Use print([WARN]) not logging module -- matches existing codebase pattern"
  - "6 silent exception sites replaced; 2 remaining except Exception: blocks are intentional (visible output or safe UI fallback)"

patterns-established:
  - "Cache failure pattern: except Exception as e: print([WARN] ... {e}) then return None/[]"
  - "Reindex pattern: .reindex(index).ffill() not .reindex(index, method='ffill')"

requirements-completed: [STAB-01, STAB-02, STAB-03]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 1 Plan 01: Stability Fixes Summary

**pytest scaffold with 6 passing stability tests; pandas reindex fix and 6 silent-exception-to-[WARN] replacements across macro_analysis, market_data, and parse_portfolio**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-13T23:45:40Z
- **Completed:** 2026-03-13T23:49:42Z
- **Tasks:** 2
- **Files modified:** 5 (created 3, modified 3)

## Accomplishments

- Created pytest scaffold: pytest.ini, tests/__init__.py, tests/test_stab.py with 6 tests covering all 3 STAB requirements
- Fixed deprecated pandas reindex API: `reindex(index, method='ffill')` -> `reindex(index).ffill()` in macro_analysis._build_erp_timeseries
- Replaced 6 silent `except Exception: pass` sites with `[WARN]` print statements so cache failures are visible and diagnosable
- Confirmed matplotlib.use('Agg') is correctly placed before pyplot import in visualize.py (no rogue imports in other scripts)
- All 6 stability tests pass (GREEN)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold and write stability tests** - `ef473a6` (test)
2. **Task 2: Apply stability fixes across all modules** - `ee98c62` (feat)

**Plan metadata:** (docs commit to follow)

_Note: TDD tasks have two commits (test RED -> feat GREEN)_

## Files Created/Modified

- `pytest.ini` - pytest configuration: testpaths=tests, python_files=test_*.py
- `tests/__init__.py` - empty module marker
- `tests/test_stab.py` - 6 stability tests: test_reindex_ffill, test_no_reindex_warning, test_cache_warn_on_failure, test_parse_portfolio_warn_on_failure, test_pipeline_survives_cache_failure, test_matplotlib_agg_backend
- `scripts/macro_analysis.py` - Fixed reindex API (1 site) + 4 silent exception sites replaced with [WARN]
- `scripts/market_data.py` - Fixed 1 silent exception site in _load_cache
- `scripts/parse_portfolio.py` - Fixed 1 silent exception site in _detect_format

## Decisions Made

- Used `print(f"  [WARN] ...")` pattern (not logging module) to match existing codebase convention
- Two remaining `except Exception:` blocks were intentionally left: parse_portfolio.validate_tickers (already prints [INVALID]) and visualize.py font fallback (safe no-op with no data loss) -- neither is a "silent" swallow per STAB-02 definition

## Deviations from Plan

None - plan executed exactly as written. The 6 targeted sites were found exactly where the plan specified.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Stable warning-free baseline established for all Phase 2+ work
- pytest infrastructure in place for TDD on future plans
- No blockers

---
*Phase: 01-stability-and-cowork-hardening*
*Completed: 2026-03-13*
