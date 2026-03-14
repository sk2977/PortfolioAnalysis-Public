---
phase: 02-input-expansion
verified: 2026-03-14T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 2: Input Expansion Verification Report

**Phase Goal:** Users can upload any standard broker file and control which tickers enter the optimization
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user uploading a .xlsx brokerage export receives the same parsed holdings table as a CSV user | VERIFIED | `parse_excel()` in `scripts/parse_portfolio.py` lines 344-386; `test_parse_excel_generic` and `test_parse_excel_schwab` both PASS -- same dict shape as CSV path |
| 2 | A user can name specific tickers that must appear in the optimized portfolio (they are not zeroed out) | VERIFIED | `_build_weight_bounds()` in `scripts/optimize.py` lines 51-80; wired into `_run_single_optimization()` at lines 236-240; `test_include_ticker_forced` passes with GOOG >= 0.05 floor enforced |
| 3 | A user can specify a benchmark ticker other than VTI and see that benchmark used in all comparison outputs | VERIFIED | `benchmark` key present in all three RISK_PRESETS (lines 26, 36, 46); `CLAUDE.md` Phase 3 uses `config.get('benchmark', 'VTI')` at line 109; `test_custom_benchmark_param` PASSES |
| 4 | Existing CSV parsing is unchanged after refactor (regression guard) | VERIFIED | `_parse_generic` and `_parse_schwab` refactored to thin wrappers (lines 265-272, 334-341); `test_csv_still_works` PASSES; full suite 17/17 pass |
| 5 | CLAUDE.md workflow surfaces Excel upload, include-list, and benchmark prompts to user | VERIFIED | Option C (Excel) at CLAUDE.md line 42-47; include_tickers prompt at lines 85-93; benchmark prompt at lines 94-100; Phase 3 uses `config.get('benchmark', 'VTI')` at line 109 |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/parse_portfolio.py` | `parse_excel()`, `_detect_format_from_df()`, `_parse_generic_df()`, `_parse_schwab_df()` | VERIFIED | All four functions present and substantive. `parse_excel()` 43 lines, full logic. `_parse_generic_df()` 85 lines, full row-iteration logic. `_parse_schwab_df()` 67 lines, full Schwab logic. |
| `scripts/optimize.py` | `_build_weight_bounds()`, updated `get_default_config()` with `include_tickers`/`include_floor`/`benchmark` keys | VERIFIED | `_build_weight_bounds()` at line 51, 30 lines, substantive. All three RISK_PRESETS include the three new keys. `optimize_portfolio()` passes them through to `_run_single_optimization()`. |
| `CLAUDE.md` | Option C (Excel), include-list prompt, benchmark prompt, `config.get('benchmark')` in Phase 3 | VERIFIED | All four changes confirmed present. `contains: "config.get('benchmark'"` verified at line 109. |
| `tests/test_inpt.py` | 8 passing tests covering INPT-01 (4), INPT-02 (3), INPT-03 (1) -- no xfail stubs | VERIFIED | 238 lines. All 8 tests PASS. No xfail markers remain. pytest run confirmed: `8 passed`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `parse_portfolio.py::parse_excel` | `pd.read_excel(dtype=str, engine='openpyxl')` | openpyxl engine call | WIRED | Line 376: `pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine='openpyxl')` |
| `parse_portfolio.py::parse_excel` | `_detect_format_from_df` | column-name-based format detection | WIRED | Line 378: `fmt = _detect_format_from_df(df)` called inside `parse_excel()` |
| `parse_portfolio.py::_parse_generic` | `parse_portfolio.py::_parse_generic_df` | CSV wrapper calls df variant | WIRED | Line 272: `return _parse_generic_df(df, exclude_tickers)` |
| `optimize.py::_run_single_optimization` | `optimize.py::_build_weight_bounds` | builds bounds before EfficientFrontier constructor | WIRED | Lines 236-240: `bounds = _build_weight_bounds(list(cov_matrix.index), ...)` then `ef = EfficientFrontier(..., weight_bounds=bounds)` |
| `optimize.py::RISK_PRESETS` | `market_data.py::download_prices(benchmark=)` | `config['benchmark']` passed via CLAUDE.md workflow | WIRED | `CLAUDE.md` line 109: `benchmark=config.get('benchmark', 'VTI')` correctly wires config to download_prices |
| `CLAUDE.md` | `optimize.py::get_default_config` | workflow instructs Claude to set `config['include_tickers']` and `config['benchmark']` | WIRED | Lines 85-100 of CLAUDE.md contain explicit prompts and code snippets for both keys |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INPT-01 | 02-01-PLAN.md | User can upload Excel (.xlsx) files from any supported broker format | SATISFIED | `parse_excel()` implemented; generic and Schwab formats tested; `test_parse_excel_generic`, `test_parse_excel_schwab`, `test_parse_excel_missing_file` all PASS |
| INPT-02 | 02-02-PLAN.md | User can specify tickers to include in optimization (forced floor weight) | SATISFIED | `_build_weight_bounds()` implemented; wired into optimizer; `test_weight_bounds_no_include`, `test_weight_bounds_with_include`, `test_include_ticker_forced` all PASS |
| INPT-03 | 02-02-PLAN.md | User can choose a custom benchmark ticker (not hardcoded to VTI) | SATISFIED | `benchmark` key in all RISK_PRESETS; `CLAUDE.md` workflow updated; `test_custom_benchmark_param` PASSES |

**Orphaned requirements check:** REQUIREMENTS.md maps INPT-01, INPT-02, INPT-03 to Phase 2. All three appear in plan frontmatter. No orphaned requirements.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | -- | -- | No TODOs, FIXMEs, placeholders, empty returns, or stub handlers found in any phase 2 file |

### Human Verification Required

None. All behaviors verified programmatically:

- Excel file parsing verified by tests using in-memory openpyxl fixtures (no network dependency).
- Weight floor enforcement verified by synthetic price data with controlled expected returns.
- Benchmark config flow verified end-to-end from RISK_PRESETS through CLAUDE.md workflow snippet.

The one item that cannot be verified without a live session:

**Test: CLAUDE.md prompts actually appear during a Cowork session**
- **Test:** Run a Cowork session through Phase 1 and Phase 2 workflow steps.
- **Expected:** Claude asks the include-list question and benchmark question after risk tolerance is set.
- **Why human:** CLAUDE.md is a behavioral instruction file -- the prompts are instructions to Claude, not executable code. Programmatic verification of whether Claude will follow the instructions requires a live session.

This is informational only -- it does not block the phase from passing. The instructions are unambiguously present in CLAUDE.md.

### Gaps Summary

No gaps. All three requirements are fully implemented, tested, and wired. The full test suite (17 tests across Phase 1 and Phase 2) passes with no failures or skips (one skip is conditional on `sample_portfolio.csv` being absent -- the file is present so the test ran and passed).

---

## Test Run Evidence

```
pytest tests/test_inpt.py -v
8 passed, 5 warnings in 2.79s

pytest tests/ -v
17 passed, 5 warnings in 4.40s
```

Warnings are DeprecationWarning from `pandas_datareader` (third-party package, not project code) and a pypfopt UserWarning about `max_sharpe` with additional objectives (expected behavior, documented in pypfopt).

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
