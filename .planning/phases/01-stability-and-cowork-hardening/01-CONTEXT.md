# Phase 1: Stability and Cowork Hardening - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix pre-existing bugs (deprecated pandas API, silent exception handling) and guarantee clean execution in Claude Cowork's Python environment. No new features -- this phase creates a reliable baseline for Phase 2+.

</domain>

<decisions>
## Implementation Decisions

### Error Handling
- Fix ALL silent `except Exception: pass` patterns across the codebase, not just cache operations
- Warn and continue on cache failures -- cache is a convenience, not critical path
- Analysis results remain valid even if cache save/load fails

### Preflight Check
- Auto-check at pipeline start: import all required packages and report missing ones before proceeding
- On missing package: print clear error with install hint (`[ERROR] Missing: pyportfolioopt. Run: pip install -r requirements.txt`) and stop
- No auto-install attempts

### Claude's Discretion
- Error handling approach (print warnings vs logging module -- choose what fits the existing pattern)
- Dependency version pinning strategy (>= minimums vs exact pins -- choose what's best for a public repo)
- Exact placement and implementation of preflight check (in __init__.py, separate function, or inline)
- How to handle the deprecated `reindex(..., method='ffill')` fix (one-liner change)
- matplotlib Agg backend placement relative to existing imports

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- standard infrastructure cleanup. Follow existing `[OK]`/`[ERROR]`/`[WARN]` console output pattern.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `[OK]`/`[ERROR]`/`[WARN]`/`[FAILED]` print prefix pattern used consistently across all modules

### Established Patterns
- All modules use `encoding='utf-8'` for file I/O
- `pathlib.Path` used for path handling in most modules
- `mkdir(parents=True, exist_ok=True)` for directory creation
- Pickle-based caching with TTL in `market_data.py` and `macro_analysis.py`

### Integration Points
- `scripts/__init__.py` -- logical place for preflight check
- `scripts/macro_analysis.py` lines 242, 312-313, 349-350 -- silent exception sites
- `scripts/market_data.py` lines 163-165, 173-174 -- silent exception sites
- `scripts/visualize.py` line 12 -- `matplotlib.use('Agg')` already present
- `requirements.txt` -- add openpyxl, pydantic; remove python-dotenv

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 01-stability-and-cowork-hardening*
*Context gathered: 2026-03-13*
