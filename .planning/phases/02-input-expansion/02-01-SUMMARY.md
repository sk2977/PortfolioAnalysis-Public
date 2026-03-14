---
phase: 02-input-expansion
plan: "01"
subsystem: testing, parsing
tags: [openpyxl, xlsx, pandas, portfolio-parser, tdd]

# Dependency graph
requires:
  - phase: 01-stability-cowork-hardening
    provides: stable parse_portfolio.py with [WARN] patterns and CSV parsing working

provides:
  - parse_excel() entry point in scripts/parse_portfolio.py
  - _detect_format_from_df() column-based format detection (no file I/O)
  - _parse_generic_df() shared DataFrame logic for generic CSV and Excel parsing
  - _parse_schwab_df() shared DataFrame logic for Schwab CSV and Excel parsing
  - tests/test_inpt.py Phase 2 test file with INPT-01, INPT-02, INPT-03 tests

affects:
  - 02-input-expansion future plans (INPT-02, INPT-03 already fully implemented)
  - CLAUDE.md workflow (Option A now supports .xlsx as well as CSV)

# Tech tracking
tech-stack:
  added: [openpyxl (already installed, now explicitly used via pd.read_excel engine param)]
  patterns:
    - "DF-variant pattern: extract row logic into _parse_X_df(), make file readers thin wrappers"
    - "dtype=str on read_excel to prevent numeric type ambiguity in mixed-type broker exports"
    - "Column-based format detection (_detect_format_from_df) separate from file-byte detection (_detect_format)"

key-files:
  created:
    - tests/test_inpt.py (Phase 2 test scaffold -- INPT-01 implemented, INPT-02/03 also implemented)
  modified:
    - scripts/parse_portfolio.py (added parse_excel, _detect_format_from_df, _parse_generic_df, _parse_schwab_df; refactored _parse_generic and _parse_schwab as wrappers)

key-decisions:
  - "Use dtype=str on pd.read_excel() to prevent openpyxl numeric coercion causing float-as-string parse failures"
  - "E-Trade Excel support explicitly deferred -- if _detect_format_from_df returns etrade for xlsx, print [WARN] and fall back to generic"
  - "_detect_format() (CSV, reads file bytes) kept unchanged; _detect_format_from_df() (DataFrame only) added as separate function"
  - "INPT-02 and INPT-03 were already fully implemented in the codebase before this plan ran -- tests updated to reflect real implementation rather than xfail stubs"

patterns-established:
  - "DF-variant refactor: extract shared row logic into _parse_X_df(), thin file-reader wrapper calls it"
  - "Excel parsing uses engine='openpyxl' explicitly and dtype=str always"

requirements-completed: [INPT-01]

# Metrics
duration: 7min
completed: 2026-03-14
---

# Phase 2 Plan 01: Excel Upload Support Summary

**parse_excel() added to portfolio parser using openpyxl engine with DF-variant refactor sharing logic between CSV and Excel format handlers**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-14T00:17:03Z
- **Completed:** 2026-03-14T00:23:30Z
- **Tasks:** 2 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- parse_excel() parses generic .xlsx and Schwab .xlsx broker exports correctly
- FileNotFoundError raised on missing file path
- _detect_format_from_df() detects Schwab/E-Trade/generic from column names without file I/O
- CSV parsing unchanged -- regression test passes
- Full suite: 17 tests passing (INPT-01, INPT-02, INPT-03 all green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Phase 2 test scaffold with INPT-01 tests** - `541b123` (test)
2. **Task 2: Implement parse_excel() and refactor parsers** - `470be1d` (feat)

## Files Created/Modified

- `tests/test_inpt.py` - Phase 2 test file: INPT-01 Excel tests, INPT-02 weight bounds tests, INPT-03 benchmark config test
- `scripts/parse_portfolio.py` - Added parse_excel(), _detect_format_from_df(), _parse_generic_df(), _parse_schwab_df(); refactored _parse_generic() and _parse_schwab() as thin wrappers; added import os

## Decisions Made

- Used dtype=str on pd.read_excel() to prevent openpyxl numeric coercion (per research pitfall)
- E-Trade Excel explicitly deferred with [WARN] fallback to generic -- low confidence per research
- _detect_format() (file-byte CSV reader) left unchanged; new _detect_format_from_df() operates on DataFrame only
- INPT-02/INPT-03 were already implemented in the codebase; tests written to match real behavior rather than xfail stubs

## Deviations from Plan

### Auto-noted Observations

**1. INPT-02 and INPT-03 already implemented**
- **Found during:** Task 1 (checking existing test_inpt.py)
- **Issue:** The original test_inpt.py already contained full INPT-02 and INPT-03 test implementations (not xfail stubs), and scripts/optimize.py already had _build_weight_bounds() and get_default_config() with benchmark/include_tickers/include_floor keys
- **Resolution:** Kept the full implementations in the test file since the behavior was already correct and passing. Plan called for xfail stubs because INPT-02/03 were assumed not yet implemented -- they were.
- **Impact:** All 17 tests pass green. Ahead of plan on INPT-02/03.

---

**Total deviations:** 1 observation (no code fixes needed -- implementation was ahead of plan)
**Impact on plan:** Positive -- INPT-02/03 are already complete, reducing work for plans 02-02 and 02-03.

## Issues Encountered

None -- implementation matched plan exactly for INPT-01. The linter/pre-commit hook auto-restored the full INPT-02/03 test implementations when the xfail stubs were written, confirming those tests were expected to work.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- parse_excel() is production-ready for generic and Schwab .xlsx broker exports
- INPT-02 and INPT-03 are already implemented (weight bounds, include-tickers, custom benchmark config)
- Plans 02-02 and 02-03 may be lighter than expected since implementations exist
- E-Trade Excel support remains deferred (low confidence per research notes)

## Self-Check: PASSED

- FOUND: scripts/parse_portfolio.py
- FOUND: tests/test_inpt.py
- FOUND: .planning/phases/02-input-expansion/02-01-SUMMARY.md
- FOUND: commit 541b123 (test(02-01): add failing INPT-01 Excel tests)
- FOUND: commit 470be1d (feat(02-01): implement parse_excel() and refactor)

---
*Phase: 02-input-expansion*
*Completed: 2026-03-14*
