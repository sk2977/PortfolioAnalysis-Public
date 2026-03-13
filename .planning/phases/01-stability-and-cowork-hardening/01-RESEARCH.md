# Phase 1: Stability and Cowork Hardening - Research

**Researched:** 2026-03-13
**Domain:** Python compatibility hardening, pandas deprecations, matplotlib headless rendering, preflight checks
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix ALL silent `except Exception: pass` patterns across the codebase, not just cache operations
- Warn and continue on cache failures -- cache is a convenience, not critical path
- Analysis results remain valid even if cache save/load fails
- Auto-check at pipeline start: import all required packages and report missing ones before proceeding
- On missing package: print clear error with install hint (`[ERROR] Missing: pyportfolioopt. Run: pip install -r requirements.txt`) and stop
- No auto-install attempts

### Claude's Discretion
- Error handling approach (print warnings vs logging module -- choose what fits the existing pattern)
- Dependency version pinning strategy (>= minimums vs exact pins -- choose what's best for a public repo)
- Exact placement and implementation of preflight check (in __init__.py, separate function, or inline)
- How to handle the deprecated `reindex(..., method='ffill')` fix (one-liner change)
- matplotlib Agg backend placement relative to existing imports

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STAB-01 | Deprecated pandas `reindex(..., method='ffill')` replaced with `.reindex(...).ffill()` across all modules | Exact location confirmed: `macro_analysis.py` line 242. One-line fix. |
| STAB-02 | Silent `except Exception: pass` in cache operations replaced with logged warnings | All silent sites catalogued: 5 sites across `macro_analysis.py` and `market_data.py`, plus 1 in `parse_portfolio.py`. |
| STAB-03 | matplotlib Agg backend explicitly set before any pyplot imports for headless Cowork execution | `visualize.py` line 11-12 already has `matplotlib.use('Agg')` before pyplot import. Verify no other pyplot imports exist in codebase. |
| COWK-01 | All scripts execute successfully in Claude Cowork Python environment | Preflight check in `scripts/__init__.py` will catch missing imports before pipeline starts. |
| COWK-02 | Requirements.txt updated: +openpyxl, +pydantic; -python-dotenv | Confirmed: `python-dotenv>=1.0.0` is present and must be removed; `openpyxl` and `pydantic` are absent and must be added. |
</phase_requirements>

---

## Summary

This phase is infrastructure-only: fix deprecated pandas API usage, replace silent exception swallowing with visible warnings, confirm matplotlib headless operation, add a preflight import check, and clean up requirements.txt. There are no algorithmic changes or new features.

The codebase is well-structured and the required changes are surgical. All five silent-exception sites are catalogued below with exact file/line locations. The one pandas deprecation (`reindex(..., method='ffill')`) is a single one-line fix. The matplotlib Agg backend is already placed correctly in `visualize.py` -- the main question is whether any other module calls pyplot before that import runs. The preflight check belongs in `scripts/__init__.py`, which currently contains only a docstring.

**Primary recommendation:** Treat this as five discrete, independently testable patches. Each maps cleanly to one or two requirement IDs. Execute in order: STAB-01 (one-liner), STAB-02 (exception rewrites), STAB-03 (verify Agg placement), COWK-01 (preflight), COWK-02 (requirements.txt).

---

## Standard Stack

### Core (already in project)
| Library | Version in requirements.txt | Purpose | Notes |
|---------|----------------------------|---------|-------|
| pandas | >=2.0.0 | Data frames, reindex | Breaking change: `reindex(method=)` removed in 2.x |
| matplotlib | >=3.7.0 | Charting | Agg backend required for headless |
| openpyxl | missing -- add | Excel read/write (Phase 2 prereq) | Required by pandas `read_excel` |
| pydantic | missing -- add | Data validation (Phase 3 prereq) | v2 API; add now per COWK-02 |
| python-dotenv | present -- REMOVE | Not used in codebase | No `.env` file, no `os.getenv` usage |

### Version Pinning Strategy (Claude's Discretion)
Use `>=` minimums (current pattern). This is correct for a public repo -- exact pins create unnecessary friction for contributors and CI. The existing floor versions (pandas>=2.0.0, etc.) are appropriate.

**For new additions:**
```
openpyxl>=3.1.0
pydantic>=2.0.0
```

---

## Architecture Patterns

### Preflight Check Placement
`scripts/__init__.py` currently contains only a docstring. It is imported whenever any `from scripts.X import Y` statement runs -- making it the correct and standard location for a one-time startup check.

**Pattern: fail-fast preflight in `__init__.py`**
```python
# scripts/__init__.py
"""
PortfolioAnalysis-Public: Portfolio optimization and US macro analysis toolkit.
...
"""

_REQUIRED_PACKAGES = [
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('matplotlib', 'matplotlib'),
    ('seaborn', 'seaborn'),
    ('yfinance', 'yfinance'),
    ('pypfopt', 'pyportfolioopt'),
    ('pandas_datareader', 'pandas-datareader'),
    ('requests', 'requests'),
    ('bs4', 'beautifulsoup4'),
    ('sklearn', 'scikit-learn'),
    ('openpyxl', 'openpyxl'),
    ('pydantic', 'pydantic'),
]

def _preflight_check():
    missing = []
    for import_name, pip_name in _REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        for pkg in missing:
            print(f"[ERROR] Missing: {pkg}. Run: pip install -r requirements.txt")
        raise SystemExit(1)

_preflight_check()
```

### Silent Exception Replacement Pattern
**Existing pattern in codebase:** `[OK]`/`[WARN]`/`[ERROR]`/`[FAILED]` print prefixes. No `logging` module in use anywhere. Use `print()` to match.

**Cache operations** -- warn and continue (cache is not critical path):
```python
# Before (silent):
except Exception:
    pass

# After (warn and continue):
except Exception as e:
    print(f"  [WARN] Cache write failed: {e}")
```

**Non-cache silent sites** -- context determines correct behavior (see site inventory below).

### STAB-01: pandas reindex Fix
```python
# Before (deprecated in pandas 2.x):
pe_aligned = pe_df['pe_ratio'].reindex(treasury_aligned.index, method='ffill')

# After (current API):
pe_aligned = pe_df['pe_ratio'].reindex(treasury_aligned.index).ffill()
```
Source: pandas 2.0 migration guide -- `reindex` no longer accepts `method` parameter directly on Series/DataFrame.

### STAB-03: matplotlib Agg Backend
`visualize.py` lines 10-12 already correctly set the backend:
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
```
The `matplotlib.use('Agg')` call MUST come before any pyplot import. This is already correct. The risk is if any other module imports pyplot directly without going through `visualize.py`. Scan confirms no other pyplot imports in the scripts directory.

---

## Exact Change Inventory

### STAB-01: pandas reindex (1 site)
| File | Line | Change |
|------|------|--------|
| `scripts/macro_analysis.py` | 242 | `.reindex(treasury_aligned.index, method='ffill')` -> `.reindex(treasury_aligned.index).ffill()` |

### STAB-02: Silent Exceptions (6 sites total)

**Cache-related (warn and continue):**

| File | Lines | Context | Fix |
|------|-------|---------|-----|
| `macro_analysis.py` | 312-313 | `_add_to_pe_history` -- saves P/E history pickle | `print(f"  [WARN] PE history save failed: {e}")` |
| `macro_analysis.py` | 349-350 | `_save_cache` -- generic cache save | `print(f"  [WARN] Cache save failed: {e}")` |
| `market_data.py` | 164-165 | `_load_cache` -- load returns None silently | Print `[WARN]` and return None |

**Non-cache silent sites (context-dependent):**

| File | Lines | Context | Fix |
|------|-------|---------|-----|
| `parse_portfolio.py` | 70-71 | `_detect_format` -- file read to detect E-Trade header | Warn and fall through to generic format detection |
| `macro_analysis.py` | 323-324 | `_load_pe_history` -- returns empty list on failure | `print(f"  [WARN] PE history load failed: {e}")`, return `[]` |
| `macro_analysis.py` | 340-341 | `_load_cache` -- returns None silently | `print(f"  [WARN] Cache load failed: {e}")`, return None |

**Note on market_data.py `_load_cache` (lines 163-165):** The market_data version already has `print(f"  Cache hit ...")` in the happy path but the exception is a bare return. Add `[WARN]` print before the return.

### COWK-02: requirements.txt changes
```
# Remove:
python-dotenv>=1.0.0

# Add:
openpyxl>=3.1.0
pydantic>=2.0.0
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Headless matplotlib | Custom display detection | `matplotlib.use('Agg')` before pyplot import | Already in codebase; no custom backend detection needed |
| Import validation | importlib.util.find_spec loops | Simple `__import__` in try/except | find_spec returns None for namespace packages in some envs; __import__ raises ImportError reliably |
| Package version checking | Version comparison logic | Omit -- presence check is sufficient | Version floor is enforced at install time via requirements.txt |

---

## Common Pitfalls

### Pitfall 1: matplotlib.use() called after pyplot import
**What goes wrong:** `UserWarning: cannot switch to Agg backend after pyplot is imported` -- Agg does not activate, RuntimeError on headless display.
**Why it happens:** Any module-level `import matplotlib.pyplot` before `visualize.py` runs will lock in the default backend.
**How to avoid:** `matplotlib.use('Agg')` must be first -- before `import matplotlib.pyplot as plt` anywhere in the process. The existing placement in `visualize.py` is correct as long as `visualize` is the first module to touch pyplot.
**Warning signs:** `UserWarning: cannot switch to non-interactive backend` in output.

### Pitfall 2: reindex method= silently accepted in older pandas
**What goes wrong:** Code runs without error on pandas 1.x, raises `FutureWarning` then `TypeError` on pandas 2.x.
**Why it happens:** API was deprecated in 1.5, removed in 2.0.
**How to avoid:** Replace with two-step chain: `.reindex(index).ffill()`.
**Warning signs:** `FutureWarning: The 'method' keyword in DataFrame.reindex with a fill_method is deprecated` on pandas 1.5.x; `TypeError` on 2.0+.

### Pitfall 3: Preflight runs on every import
**What goes wrong:** `from scripts.parse_portfolio import parse_csv` triggers full preflight check every time -- acceptable for a pipeline tool, but could add import latency in tests.
**Why it happens:** `scripts/__init__.py` runs on first package import. Subsequent imports of the same package are cached by Python's module system.
**How to avoid:** This is fine -- `__init__.py` runs only once per process. Not a real pitfall for this codebase.

### Pitfall 4: pydantic v1 vs v2 import paths
**What goes wrong:** Adding `pydantic>=2.0.0` to requirements.txt while any code uses v1 API (`from pydantic import validator`) will raise ImportError at runtime.
**Why it happens:** pydantic v2 changed many import paths and decorator names.
**How to avoid:** Phase 1 only adds pydantic to requirements.txt as a prereq for Phase 3. Do NOT write any pydantic model code in Phase 1. Pydantic imports only appear in Phase 3.

### Pitfall 5: openpyxl installed but not tested in Phase 1
**What goes wrong:** openpyxl added to requirements.txt but preflight check tries to `import openpyxl` -- this passes, but if the user's environment has an old version, Phase 2's `pd.read_excel` may fail.
**Why it happens:** openpyxl 3.0.x vs 3.1.x have minor API differences relevant to newer pandas.
**How to avoid:** Pin `openpyxl>=3.1.0` in requirements.txt. Presence check in preflight is sufficient for Phase 1.

---

## Code Examples

### Verified: pandas reindex chained API
```python
# Source: pandas 2.0 migration guide / official docs
# https://pandas.pydata.org/docs/whatsnew/v2.0.0.html

# DEPRECATED (raises FutureWarning in 1.5, TypeError in 2.0):
series.reindex(new_index, method='ffill')

# CURRENT:
series.reindex(new_index).ffill()
```
Confidence: HIGH (standard pandas 2.x idiom, directly observable in pandas release notes).

### Verified: matplotlib Agg backend for headless
```python
# Source: matplotlib FAQ "Using matplotlib in a web application server"
# https://matplotlib.org/stable/users/explain/figure/backends.html

import matplotlib
matplotlib.use('Agg')          # Must come BEFORE pyplot import
import matplotlib.pyplot as plt  # Now safe in headless environment
```
Confidence: HIGH (official matplotlib documentation pattern).

### Verified: Simple preflight import check
```python
# Pattern: check importability, fail fast with actionable message
# Source: standard Python idiom used in Django, pytest, setuptools

_REQUIRED_PACKAGES = [
    ('pandas', 'pandas'),
    ('pypfopt', 'pyportfolioopt'),   # import name != pip name
    ('bs4', 'beautifulsoup4'),        # import name != pip name
    ('sklearn', 'scikit-learn'),      # import name != pip name
    ('pandas_datareader', 'pandas-datareader'),
]

missing = []
for import_name, pip_name in _REQUIRED_PACKAGES:
    try:
        __import__(import_name)
    except ImportError:
        missing.append(pip_name)

if missing:
    for pkg in missing:
        print(f"[ERROR] Missing: {pkg}. Run: pip install -r requirements.txt")
    raise SystemExit(1)
```
Note: import name differs from pip name for 4 packages in this project (see table above).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `series.reindex(idx, method='ffill')` | `series.reindex(idx).ffill()` | pandas 2.0 (April 2023) | Required fix -- raises TypeError in pandas 2.x |
| `except Exception: pass` | `except Exception as e: print(...)` | N/A (best practice) | Surfaces hidden failures |
| `python-dotenv` for env management | Not needed (Claude is the AI layer) | Project design | Remove to simplify dependency tree |

---

## Open Questions

1. **Does any module import pyplot before visualize.py runs?**
   - What we know: `visualize.py` has `matplotlib.use('Agg')` at line 11. No other `import matplotlib.pyplot` found in scripts/ via code review.
   - What's unclear: If user-land code (e.g., a notebook or CLAUDE.md workflow) imports pyplot before calling `visualize`, the Agg call would be too late.
   - Recommendation: Add a note in the Agg verification task to grep for any rogue pyplot imports. The current codebase is clean.

2. **Should `_load_cache` silent failures in `market_data.py` print at INFO or WARN level?**
   - What we know: A corrupted pickle cache that fails to load is expected behavior (disk corruption, serialization mismatch). The function returns None and download proceeds normally.
   - What's unclear: WARN may alarm users unnecessarily on a routine cache miss due to corruption.
   - Recommendation: Use `[WARN]` to match the CONTEXT.md decision that all silent exceptions should be made visible. A corrupted cache is worth knowing about.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (not yet installed -- Wave 0 gap) |
| Config file | none -- create `pytest.ini` in Wave 0 |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAB-01 | `.reindex(idx).ffill()` produces same result as deprecated API | unit | `python -m pytest tests/test_stab.py::test_reindex_ffill -x` | Wave 0 |
| STAB-01 | No FutureWarning or TypeError on reindex call | unit | `python -m pytest tests/test_stab.py::test_no_reindex_warning -x` | Wave 0 |
| STAB-02 | Cache write failure prints [WARN] and does not raise | unit | `python -m pytest tests/test_stab.py::test_cache_warn_on_failure -x` | Wave 0 |
| STAB-02 | Pipeline completes when cache write fails (no exception propagated) | unit | `python -m pytest tests/test_stab.py::test_pipeline_survives_cache_failure -x` | Wave 0 |
| STAB-03 | `matplotlib.get_backend()` returns 'agg' after importing visualize | unit | `python -m pytest tests/test_stab.py::test_matplotlib_agg_backend -x` | Wave 0 |
| COWK-01 | All required packages importable; preflight passes | unit | `python -m pytest tests/test_cowk.py::test_preflight_passes -x` | Wave 0 |
| COWK-01 | Preflight raises SystemExit on missing package | unit | `python -m pytest tests/test_cowk.py::test_preflight_fails_on_missing -x` | Wave 0 |
| COWK-02 | requirements.txt contains openpyxl and pydantic, not python-dotenv | unit | `python -m pytest tests/test_cowk.py::test_requirements_contents -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` -- empty, marks tests as package
- [ ] `tests/test_stab.py` -- covers STAB-01, STAB-02, STAB-03
- [ ] `tests/test_cowk.py` -- covers COWK-01, COWK-02
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` -- minimal config
- [ ] Framework install: `pip install pytest` (or add to requirements.txt as dev dependency)

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `scripts/macro_analysis.py`, `scripts/market_data.py`, `scripts/visualize.py`, `scripts/parse_portfolio.py`, `scripts/__init__.py` -- silent exception sites, reindex usage, Agg placement all confirmed by reading source
- `requirements.txt` -- package inventory confirmed by reading file
- pandas 2.0 release notes -- `reindex(method=)` removal is a well-known breaking change in the 2.0 migration

### Secondary (MEDIUM confidence)
- matplotlib documentation pattern for headless backends -- standard `matplotlib.use('Agg')` before pyplot import is widely documented
- pydantic v1/v2 migration incompatibility -- well-documented breaking change; v2 was released June 2023

### Tertiary (LOW confidence)
- None -- all findings are based on direct source inspection or well-established library documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- read directly from requirements.txt and source files
- Architecture: HIGH -- preflight pattern is standard Python, all change sites confirmed by grep
- Pitfalls: HIGH -- all identified from actual code reading, not speculation

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (stable libraries; pandas/matplotlib APIs do not change frequently)
