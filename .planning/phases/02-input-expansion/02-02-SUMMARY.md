---
phase: 02-input-expansion
plan: "02"
subsystem: optimize
tags: [optimization, weight-bounds, include-tickers, benchmark, config]
dependency_graph:
  requires: [02-01]
  provides: [_build_weight_bounds, include_tickers config, benchmark config]
  affects: [scripts/optimize.py, CLAUDE.md, tests/test_inpt.py]
tech_stack:
  added: []
  patterns: [per-ticker weight bounds list, scalar-vs-list bounds dispatch, case-insensitive ticker matching]
key_files:
  created: []
  modified:
    - scripts/optimize.py
    - tests/test_inpt.py
    - CLAUDE.md
decisions:
  - Use scalar tuple (0, max_weight) as backward-compatible return when no include list -- avoids touching existing optimizer behavior
  - Use list(cov_matrix.index) as authoritative ticker order in _build_weight_bounds (not portfolio['tickers']) to avoid index mismatch
  - Fallback EfficientFrontier in except block reuses same bounds object (not hardcoded scalar) so include floors survive errors
  - Add include_tickers validation to Phase 1 (not Phase 2) since tickers must be known before config is used
metrics:
  duration: "7 minutes"
  completed: "2026-03-13"
  tasks_completed: 2
  files_modified: 3
---

# Phase 02 Plan 02: Forced-Include Tickers and Custom Benchmark Summary

One-liner: Per-ticker weight bounds helper with case-insensitive floor enforcement, plus benchmark and include-list keys surfaced in config presets and CLAUDE.md workflow.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD RED) | Failing tests for INPT-02/03 | 1c1b9cc | tests/test_inpt.py (created) |
| 1 (TDD GREEN) | _build_weight_bounds + config keys | d70083e | scripts/optimize.py, tests/test_inpt.py |
| 2 | CLAUDE.md workflow updates | bb6b8eb | CLAUDE.md |

## What Was Built

### scripts/optimize.py

Added `_build_weight_bounds(tickers, max_weight, include_tickers=None, include_floor=0.01)`:
- Returns scalar `(0, max_weight)` tuple when `include_tickers` is None or empty -- identical to pre-existing behavior, no regressions
- Returns list of `(min, max)` tuples aligned to ticker order when include list is provided
- Case-insensitive matching: `include_tickers=['msft']` matches `'MSFT'` in tickers list

Added `include_tickers`, `include_floor`, and `benchmark` keys to all three RISK_PRESETS dicts (conservative/moderate/aggressive) with defaults `[]`, `0.01`, `'VTI'`.

Updated `_run_single_optimization()` to accept `include_tickers` and `include_floor` params, call `_build_weight_bounds()` with `list(cov_matrix.index)` as authoritative order, and reuse the same bounds in the fallback `EfficientFrontier` inside the except block.

Updated `optimize_portfolio()` to pass `config.get('include_tickers')` and `config.get('include_floor', 0.01)` to each `_run_single_optimization()` call.

### tests/test_inpt.py

Replaced four `@pytest.mark.xfail` stubs with real implementations:
- `test_weight_bounds_no_include`: asserts scalar return for empty include list
- `test_weight_bounds_with_include`: asserts per-ticker list and case-insensitivity
- `test_include_ticker_forced`: synthetic price data (rng seed 42) where GOOG has negative expected return; verifies GOOG weight >= 0.05 after forced floor
- `test_custom_benchmark_param`: asserts benchmark='VTI', include_tickers=[], include_floor present in moderate config

All 8 INPT tests pass; full suite: 17 passed, 0 failed.

### CLAUDE.md

- Phase 1: Added Option C (Excel upload via `parse_excel()`) with format note
- Phase 1: Added include_tickers validation snippet (warns if forced tickers missing from portfolio)
- Phase 2: Added two prompts after risk tolerance -- include-list question and benchmark question
- Phase 3: Changed hardcoded `benchmark='VTI'` to `benchmark=config.get('benchmark', 'VTI')`

## Verification Results

```
pytest tests/test_inpt.py -x -q    -> 8 passed
pytest tests/ -x -q                -> 17 passed
grep "config.get('benchmark'"      -> match in CLAUDE.md
grep "include_tickers"             -> match in CLAUDE.md
python -c "from scripts.optimize import _build_weight_bounds" -> [OK]
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- scripts/optimize.py: FOUND
- tests/test_inpt.py: FOUND
- CLAUDE.md: FOUND
- Commit 1c1b9cc (test RED): FOUND
- Commit d70083e (feat GREEN): FOUND
- Commit bb6b8eb (CLAUDE.md): FOUND
