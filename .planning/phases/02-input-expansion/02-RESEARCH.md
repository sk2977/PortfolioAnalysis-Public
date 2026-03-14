# Phase 2: Input Expansion - Research

**Researched:** 2026-03-13
**Domain:** Python file parsing (openpyxl/pandas), pyportfolioopt weight constraints, CLAUDE.md workflow surface area
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INPT-01 | User can upload Excel (.xlsx) files from any supported broker format | openpyxl already in requirements.txt; `pd.read_excel()` returns same DataFrame type as `pd.read_csv()`; existing format-detection and row-parsing logic in `parse_portfolio.py` is reusable after a thin `parse_excel()` wrapper |
| INPT-02 | User can specify tickers to include in optimization (forced floor weight via pyportfolioopt weight_bounds) | `EfficientFrontier(weight_bounds=list_of_tuples)` verified working: per-ticker bounds as a list of (min, max) tuples is the correct API; confirmed with live test that a 0.0-weight ticker gets forced to floor |
| INPT-03 | User can choose a custom benchmark ticker (not hardcoded to VTI) | `download_prices()` already accepts `benchmark` parameter with `'VTI'` as default; only change needed is surfacing this parameter in the CLAUDE.md Phase 3 workflow snippet |
</phase_requirements>

---

## Summary

Phase 2 adds three user-facing features: Excel upload, forced include-list, and custom benchmark. All three are shallower than they might appear.

For INPT-01, `openpyxl` is already in `requirements.txt` and `pd.read_excel()` produces the same `pd.DataFrame` type as `pd.read_csv()`. The existing `_parse_generic()`, `_parse_etrade()`, and `_parse_schwab()` functions in `parse_portfolio.py` can be reused after a thin `parse_excel()` entry point normalizes the DataFrame. The main risk is that Excel cells can arrive as numeric types rather than strings (percentages as 0.10 float, currencies as 1234.56 float), so the normalization path must force `dtype=str` or use `pd.to_numeric(errors='coerce')` instead of bare `float()` casts.

For INPT-02, `EfficientFrontier` already supports per-ticker `weight_bounds` as a list of `(min, max)` tuples -- verified live against the installed package. Forced inclusion means setting the lower bound for each include-ticker to a small floor value (e.g., 0.01) rather than 0. The floor goes into `_run_single_optimization()` in `optimize.py`. The `config` dict needs an `include_tickers` key and a `include_floor` key so the optimizer can build the bounds list.

For INPT-03, the `download_prices()` function already accepts a `benchmark` parameter defaulting to `'VTI'`. The only gap is that CLAUDE.md's Phase 3 workflow snippet hardcodes `benchmark='VTI'`. Fixing this requires updating the CLAUDE.md snippet to surface the parameter and updating the CLAUDE.md Phase 2 config step to ask the user for a benchmark preference.

**Primary recommendation:** Implement in dependency order: parse_excel() first (INPT-01), then include_tickers in config+optimize (INPT-02), then benchmark surfacing in CLAUDE.md (INPT-03). No new dependencies are required.

---

## Standard Stack

### Core (no changes from Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | >=3.1.0 | Excel .xlsx engine for `pd.read_excel()` | Already in requirements.txt; pandas-recommended engine for .xlsx; xlrd dropped .xlsx support in v2.0 |
| pandas | >=2.0.0 | DataFrame I/O, `pd.read_excel()`, `pd.to_numeric()` | Core data layer; `read_excel()` returns same type as `read_csv()` |
| pyportfolioopt | >=1.5.0 | `EfficientFrontier(weight_bounds=list_of_tuples)` | Verified: per-ticker bounds accepted as list of (min,max) tuples |

### No New Dependencies

All three requirements are achievable with libraries already installed. Do not add new packages.

**Installation:** Nothing new. Phase 1 already put openpyxl and pydantic in requirements.txt.

---

## Architecture Patterns

### Recommended Project Structure (no new files required)

```
scripts/
├── parse_portfolio.py   # Add parse_excel() + _normalize_excel_numerics()
├── optimize.py          # Add include_tickers support in config + _run_single_optimization()
├── market_data.py       # No changes (benchmark param already exists)
└── ...
CLAUDE.md                # Update Phase 2 config step + Phase 3 download snippet
```

### Pattern 1: parse_excel() as a thin entry point

**What:** `parse_excel(file_path, exclude_tickers, sheet_name=0)` reads with `pd.read_excel(..., dtype=str)`, then dispatches to existing `_parse_etrade()`, `_parse_schwab()`, or `_parse_generic()`. Format detection reuses `_detect_format()` but reads from the DataFrame, not the file bytes (since Excel has no text header lines).

**When to use:** Whenever the file path ends in `.xlsx` or `.xls`.

**Example:**
```python
# In parse_portfolio.py
def parse_excel(file_path, exclude_tickers=None, sheet_name=0):
    """
    Parse portfolio from Excel file. Auto-detects broker format.
    openpyxl engine is required (already in requirements.txt).
    """
    if exclude_tickers is None:
        exclude_tickers = []

    # dtype=str forces all cells to strings -- avoids numeric type ambiguity
    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]

    fmt = _detect_format_from_df(df)
    print(f"  Detected Excel format: {fmt}")

    if fmt == 'etrade':
        # E-Trade Excel has same column layout as CSV; reuse parser
        return _parse_etrade_df(df, exclude_tickers)
    elif fmt == 'schwab':
        return _parse_schwab_df(df, exclude_tickers)
    else:
        return _parse_generic_df(df, exclude_tickers, format_label='excel_generic')
```

**Key detail:** Using `dtype=str` on `pd.read_excel()` forces all cells to strings, eliminating the numeric-type ambiguity pitfall. The existing `_parse_generic()` and `_parse_schwab()` already strip `$`, `,`, `%` and cast with `float()` -- so they work correctly on string-typed Excel input.

**Format detection for Excel:** E-Trade Excel exports include "% of Portfolio" as a column header. Schwab Excel exports include "Market Value" and "Description" columns. Generic is the fallback. Detection reads column names only (no byte-scanning of file lines).

### Pattern 2: Per-ticker weight_bounds for include list

**What:** When `config['include_tickers']` is set, build a list of `(min, max)` tuples aligned to the ticker order in `prices.columns`. Tickers in the include list get `(include_floor, max_weight)`. All others get `(0, max_weight)`.

**When to use:** `_run_single_optimization()` in `optimize.py`, invoked for each of the three return methods.

**Example (verified against installed pyportfolioopt):**
```python
# In optimize.py -- _run_single_optimization()
def _build_weight_bounds(tickers, max_weight, include_tickers=None, include_floor=0.01):
    """
    Build per-ticker weight bounds list for EfficientFrontier.
    tickers: list of str (must match prices.columns order)
    include_tickers: set of str to force above zero
    """
    if not include_tickers:
        return (0, max_weight)  # scalar form -- same behavior as before

    bounds = []
    include_set = {t.upper() for t in include_tickers}
    for t in tickers:
        if t.upper() in include_set:
            bounds.append((include_floor, max_weight))
        else:
            bounds.append((0, max_weight))
    return bounds  # list form -- triggers per-ticker mode in pyportfolioopt


# Usage in _run_single_optimization():
bounds = _build_weight_bounds(
    list(cov_matrix.index),
    config['max_weight'],
    include_tickers=config.get('include_tickers'),
    include_floor=config.get('include_floor', 0.01)
)
ef = EfficientFrontier(mu, cov_matrix, weight_bounds=bounds)
```

**Verified:** `EfficientFrontier(weight_bounds=list_of_tuples)` is the documented and working API. When a ticker has low expected returns, `weight_bounds=(0, max)` allows the optimizer to zero it out. Setting `(include_floor, max)` forces it to at least `include_floor`. Tested live: a ticker with 0.03 expected return that would be zeroed out is forced to 0.10 weight when given a (0.10, 0.60) bound.

### Pattern 3: Custom benchmark surfacing (CLAUDE.md change only)

**What:** `download_prices()` already accepts `benchmark` as a parameter. The fix is purely in CLAUDE.md -- the Phase 2 config step must ask the user for a benchmark, and the Phase 3 download snippet must pass that value rather than hardcoding `'VTI'`.

**Example (CLAUDE.md Phase 3 update):**
```python
# Before (hardcoded):
market = download_prices(portfolio['tickers'], start_date='2020-01-01', benchmark='VTI')

# After (surfaced):
market = download_prices(
    portfolio['tickers'],
    start_date='2020-01-01',
    benchmark=config.get('benchmark', 'VTI')
)
```

The `config` dict from `get_default_config()` does not currently have a `benchmark` key. Add it to each preset in `RISK_PRESETS` as `'benchmark': 'VTI'` so it can be overridden by the user without breaking anything that reads the config.

### Anti-Patterns to Avoid

- **Do not use `dtype=object` or no dtype on `pd.read_excel()`:** Without `dtype=str`, percentage cells arrive as Python floats (0.10) rather than the string "10%" that the existing parsers expect. Force `dtype=str` and let existing code handle the cast.
- **Do not pass `include_tickers` as a list to `weight_bounds` directly:** pyportfolioopt expects `weight_bounds` to be either a scalar tuple or a list of tuples aligned to `cov_matrix.index` order. The helper `_build_weight_bounds()` must be index-order-aware.
- **Do not modify `get_default_config()` return value signature destructively:** Downstream consumers (Phase 3, Phase 4) will call `optimize_portfolio()` without `include_tickers`. `config.get('include_tickers')` returning `None` must fall through to scalar bounds gracefully.
- **Do not add new benchmark-download logic:** The benchmark download is already handled by `download_prices()`. Only the CLAUDE.md call site needs updating.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel cell type coercion | Custom type-detection logic | `pd.read_excel(..., dtype=str)` | Forces all cells to strings; eliminates numeric/string ambiguity at source |
| Forced inclusion weight floor | Custom LP constraint | `EfficientFrontier(weight_bounds=list_of_tuples)` | pyportfolioopt exposes this natively; verified working |
| Excel format detection | New regex-based byte scanner | Reuse `_detect_format()` on column headers | Excel has no text header lines; column names carry the same signal |

**Key insight:** All three requirements have exact API-level solutions in the current stack. The work is integration and surfacing -- not new algorithms.

---

## Common Pitfalls

### Pitfall 1: Excel percentage cells arriving as floats when dtype is not forced

**What goes wrong:** Without `dtype=str`, `pd.read_excel()` returns percentage-formatted cells as Python floats (e.g., 0.10 for "10%"). The existing `_parse_generic()` strips `%` from strings and divides by 100 if the sum > 1. A float `0.10` passed to this path produces `0.10 / total` -- correct if the total also comes in as a float fraction, but if the broker mixes percentage and dollar columns in the same file, normalization silently produces wrong weights.

**How to avoid:** Always pass `dtype=str` to `pd.read_excel()`. The existing string-to-float coercion in `_parse_generic()` handles all cases correctly when input is consistently string-typed.

**Warning signs:** Weights summing to a value far from 1.0 (e.g., 0.01 instead of 1.0 if percentages were double-divided, or 100.0 if they were treated as whole numbers).

### Pitfall 2: `_detect_format()` reads file bytes -- unusable for Excel

**What goes wrong:** The current `_detect_format()` opens the file path as a text file and scans for "e*trade" in the raw bytes. This works for CSV but will fail or produce garbage for an Excel binary file.

**How to avoid:** Add a `_detect_format_from_df(df)` variant that inspects `df.columns` only (column-name-based detection). The E-Trade signal ("% of portfolio" in a column name) and Schwab signal ("market value" + "description" columns) are preserved in the Excel column headers. Keep the original `_detect_format()` for CSV unchanged.

### Pitfall 3: `include_tickers` not in the prices DataFrame

**What goes wrong:** A user specifies `include_tickers=['TSLA']` but TSLA is not in their portfolio CSV. The ticker was never downloaded. `_build_weight_bounds()` iterates over `cov_matrix.index` which only includes downloaded tickers -- TSLA is silently ignored.

**How to avoid:** Before calling `optimize_portfolio()`, validate that all `include_tickers` are present in `portfolio['tickers']`. If any are missing, print a `[WARN]` and either add them to the download list or remove them from `include_tickers` with an explanation. The CLAUDE.md Phase 2 step should include a validation call.

### Pitfall 4: Cowork file path for uploaded .xlsx

**What goes wrong:** A user uploads an Excel file in a Cowork conversation. The file may land in a temp path that Claude's Python execution context cannot resolve. This is flagged as MEDIUM confidence in STATE.md.

**How to avoid:** Instruct users to place the file in the project root (same directory as CLAUDE.md) and provide just the filename. Add `os.path.exists(file_path)` check as the first line of `parse_excel()` with a clear error message. Document the supported file-provision method in CLAUDE.md.

### Pitfall 5: weight_bounds list must match cov_matrix index order exactly

**What goes wrong:** `EfficientFrontier` maps the list of bounds by position, not by ticker name. If the tickers list passed to `_build_weight_bounds()` differs in order from `cov_matrix.index`, the floor is applied to the wrong ticker.

**How to avoid:** Always build bounds from `list(cov_matrix.index)`, not from `portfolio['tickers']` or `prices.columns`. These may differ after pyportfolioopt internal reordering. The `cov_matrix` returned from `risk_models.CovarianceShrinkage` preserves `prices.columns` order, so use `list(cov_matrix.index)` as the authoritative order.

---

## Code Examples

### parse_excel() entry point

```python
# Source: openpyxl + pandas official docs; pattern verified against existing codebase
def parse_excel(file_path, exclude_tickers=None, sheet_name=0):
    if exclude_tickers is None:
        exclude_tickers = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot find file: {file_path}")

    # dtype=str is critical -- prevents numeric type ambiguity in brokerage exports
    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]

    fmt = _detect_format_from_df(df)
    print(f"  Detected Excel format: {fmt}")

    # Dispatch to existing parsers (they expect a file_path -- refactor to _df variants)
    # Simplest approach: write to a temp CSV and call existing parsers
    # Better approach: refactor _parse_generic/_parse_schwab/_parse_etrade to accept df
    ...
```

**Implementation note:** The cleanest refactor is to extract the row-iteration logic from `_parse_generic()`, `_parse_schwab()`, and `_parse_etrade()` into `_parse_generic_df(df, exclude_tickers)` variants that accept a DataFrame directly. The existing functions become thin wrappers: `_parse_generic(file_path, exclude_tickers)` reads with `pd.read_csv()` and calls `_parse_generic_df()`. `parse_excel()` reads with `pd.read_excel()` and calls the same `_parse_generic_df()`.

### Per-ticker weight_bounds (verified live)

```python
# Verified: pyportfolioopt EfficientFrontier accepts list of (min, max) tuples
# A ticker with (0.10, 0.60) is forced to at least 10% even with low expected return
def _build_weight_bounds(tickers, max_weight, include_tickers=None, include_floor=0.01):
    if not include_tickers:
        return (0, max_weight)  # scalar -- same behavior as before
    include_set = {t.upper() for t in include_tickers}
    return [
        (include_floor if t.upper() in include_set else 0, max_weight)
        for t in tickers
    ]
```

### config dict additions

```python
# get_default_config() must add these keys to each preset
config['include_tickers'] = []     # list of str; empty means no forced inclusion
config['include_floor'] = 0.01     # minimum weight for forced-include tickers
config['benchmark'] = 'VTI'       # benchmark ticker; user can override
```

### CLAUDE.md Phase 2 config step (addition)

```
Ask the user:
- "Are there any tickers you want to guarantee appear in the optimized portfolio?"
  (Apply as include_tickers in config)
- "Which benchmark would you like to compare against? Default is VTI."
  (Apply as benchmark in config; used in Phase 3 download call)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `xlrd` for .xlsx | `openpyxl` for .xlsx | xlrd dropped .xlsx in v2.0 (2020); openpyxl is the correct engine |
| Scalar `weight_bounds=(0, max)` | List of tuples `[(min, max), ...]` | pyportfolioopt >=1.5 supports per-ticker bounds natively |

**No deprecated features relevant to this phase.** Phase 1 already fixed the pandas `reindex` deprecation.

---

## Open Questions

1. **Cowork file path for uploaded .xlsx**
   - What we know: `download_prices()` uses `open()` with a file path. If a user uploads a file in Cowork, the path Cowork provides may or may not be accessible from the Python execution context.
   - What's unclear: Whether Cowork exposes uploaded files at a stable path relative to the project root.
   - Recommendation: Instruct users to place the file in the project root. Add `os.path.exists()` guard. Document this in CLAUDE.md. Mark as a known limitation until tested in actual Cowork environment.
   - Confidence: MEDIUM (flagged in STATE.md Blockers)

2. **E-Trade Excel export column layout**
   - What we know: E-Trade CSV has ~10 header rows before data, detected by scanning for "e*trade" in raw bytes. Excel exports may differ.
   - What's unclear: Whether E-Trade's .xlsx export has the same column structure as its .csv export, or whether it uses a different layout.
   - Recommendation: Test with an actual E-Trade .xlsx export. If layout differs, add a separate `_parse_etrade_excel()` variant. Do not assume CSV and Excel layouts are identical.
   - Confidence: LOW (no sample E-Trade .xlsx available for verification)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in use from Phase 1) |
| Config file | none -- pytest discovers tests/ directory |
| Quick run command | `pytest tests/test_inpt.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPT-01 | `parse_excel()` with a generic .xlsx produces same parsed holdings as equivalent CSV | unit | `pytest tests/test_inpt.py::test_parse_excel_generic -x` | Wave 0 |
| INPT-01 | `parse_excel()` with a Schwab .xlsx format is detected and parsed correctly | unit | `pytest tests/test_inpt.py::test_parse_excel_schwab -x` | Wave 0 |
| INPT-01 | `parse_excel()` raises FileNotFoundError for missing path | unit | `pytest tests/test_inpt.py::test_parse_excel_missing_file -x` | Wave 0 |
| INPT-02 | `_build_weight_bounds()` returns scalar tuple when include_tickers is empty | unit | `pytest tests/test_inpt.py::test_weight_bounds_no_include -x` | Wave 0 |
| INPT-02 | `_build_weight_bounds()` returns list with floor applied to included tickers | unit | `pytest tests/test_inpt.py::test_weight_bounds_with_include -x` | Wave 0 |
| INPT-02 | A low-expected-return ticker specified in include_tickers is not zeroed out by optimizer | unit | `pytest tests/test_inpt.py::test_include_ticker_forced -x` | Wave 0 |
| INPT-03 | `download_prices()` accepts benchmark parameter and uses it | unit | `pytest tests/test_inpt.py::test_custom_benchmark_param -x` | Wave 0 |
| INPT-03 | CLAUDE.md Phase 3 snippet no longer hardcodes VTI | manual | Review CLAUDE.md after implementation | N/A |

### Sampling Rate

- **Per task commit:** `pytest tests/test_inpt.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_inpt.py` -- covers INPT-01, INPT-02, INPT-03 (create in Wave 0 before implementation)
- [ ] Fixture: small in-memory .xlsx file using `openpyxl` directly (no actual brokerage file needed for unit tests)

---

## Sources

### Primary (HIGH confidence)

- pyportfolioopt source + live test -- `EfficientFrontier.__init__` docstring confirms `weight_bounds` accepts "tuple OR tuple list"; verified with live Python execution in project venv
- pandas `read_excel()` docs -- `dtype` parameter forces all columns to specified type; `engine='openpyxl'` selects openpyxl backend
- Direct codebase analysis -- `parse_portfolio.py`, `optimize.py`, `market_data.py`, `CLAUDE.md` read in full

### Secondary (MEDIUM confidence)

- `.planning/research/STACK.md` (researched 2026-03-13) -- openpyxl recommendation, xlrd .xlsx removal, pydantic v2 rationale
- `.planning/research/PITFALLS.md` (researched 2026-03-13) -- Excel numeric type coercion pitfall, Cowork file path pitfall

### Tertiary (LOW confidence)

- E-Trade .xlsx export column layout -- no sample file available; assumption that it matches CSV layout needs verification during implementation

---

## Metadata

**Confidence breakdown:**
- INPT-01 (Excel parsing): HIGH -- openpyxl in requirements.txt; `pd.read_excel(dtype=str)` pattern is established; reuse of existing parsers is straightforward
- INPT-02 (include list): HIGH -- verified live against installed pyportfolioopt; API confirmed working
- INPT-03 (custom benchmark): HIGH -- `download_prices(benchmark=...)` already exists; change is CLAUDE.md only
- Cowork file path for .xlsx: MEDIUM -- flagged in STATE.md Blockers; verify during implementation
- E-Trade .xlsx column layout: LOW -- no sample file

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable libraries; pyportfolioopt API unlikely to change)
