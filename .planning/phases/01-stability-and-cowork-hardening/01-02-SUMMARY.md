---
phase: 01-stability-and-cowork-hardening
plan: 02
subsystem: testing
tags: [preflight, dependencies, requirements, pydantic, openpyxl, scikit-learn]

# Dependency graph
requires:
  - phase: 01-01
    provides: Stability fixes to scripts package (silent exceptions, reindex, Agg backend)
provides:
  - Fail-fast preflight import check in scripts/__init__.py that catches missing packages on first import
  - Updated requirements.txt with openpyxl and pydantic; python-dotenv removed
  - Unit tests for COWK-01 (preflight) and COWK-02 (requirements contents)
affects:
  - Phase 2 (xlsx parsing needs openpyxl confirmed in requirements)
  - Phase 4 (pydantic model_validate pattern needs pydantic in requirements)

# Tech tracking
tech-stack:
  added: [openpyxl>=3.1.0, pydantic>=2.0.0]
  patterns: [fail-fast preflight check on package import, _REQUIRED_PACKAGES list maps import_name to pip_name]

key-files:
  created:
    - tests/test_cowk.py
  modified:
    - scripts/__init__.py
    - requirements.txt

key-decisions:
  - "Preflight uses __import__ directly so it can be monkeypatched in tests without module reload complexity"
  - "python-dotenv removed -- not used anywhere in codebase, was a stale dependency"
  - "scikit-learn was missing from environment; installed as Rule 3 auto-fix (blocking issue found during TDD RED phase)"

patterns-established:
  - "_REQUIRED_PACKAGES: list of (import_name, pip_name) tuples -- import_name for __import__(), pip_name for error messages"
  - "Preflight pattern: _preflight_check() defined then called immediately at module level"

requirements-completed: [COWK-01, COWK-02]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 1 Plan 02: Cowork Compatibility Summary

**Fail-fast preflight check in scripts/__init__.py using _REQUIRED_PACKAGES list, with openpyxl and pydantic added to requirements.txt and python-dotenv removed**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-13T23:52:02Z
- **Completed:** 2026-03-13T23:56:24Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- scripts/__init__.py now runs _preflight_check() on first import; prints [ERROR] with pip install hint for each missing package and raises SystemExit(1)
- requirements.txt updated: +openpyxl>=3.1.0, +pydantic>=2.0.0, -python-dotenv
- tests/test_cowk.py created with 3 tests covering preflight pass, preflight fail (monkeypatched ImportError), and requirements contents
- All 9 tests pass: 6 stability (test_stab.py) + 3 Cowork (test_cowk.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Cowork tests and add preflight check** - `1c677f0` (feat)
2. **Task 2: Update requirements.txt** - `6c89e9a` (feat)

_Note: Task 1 used TDD: RED (tests created, 2/3 failing) -> GREEN (preflight implemented, scikit-learn installed, all pass after task 2)_

## Files Created/Modified
- `scripts/__init__.py` - Added _REQUIRED_PACKAGES list and _preflight_check() called at module load
- `tests/test_cowk.py` - 3 tests for COWK-01/02: preflight pass, preflight fail on missing, requirements contents
- `requirements.txt` - Added openpyxl>=3.1.0 and pydantic>=2.0.0; removed python-dotenv>=1.0.0

## Decisions Made
- Preflight uses `__import__` directly (not importlib) so tests can monkeypatch `builtins.__import__` without reloading the module
- python-dotenv removed -- searching the codebase confirmed it is not imported anywhere
- scikit-learn was already missing from the environment; installed as part of plan execution (Rule 3 auto-fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing scikit-learn package**
- **Found during:** Task 1 (TDD GREEN phase -- preflight check ran and found sklearn missing)
- **Issue:** scikit-learn not installed in the active Python environment; preflight check correctly caught it with SystemExit(1), which broke test_preflight_passes
- **Fix:** Ran `pip install scikit-learn`; package is already listed in requirements.txt (scikit-learn>=1.2.0)
- **Files modified:** None (environment install only)
- **Verification:** All 9 tests pass after install; `python -c "import sklearn"` succeeds
- **Committed in:** 1c677f0 (noted in commit message)

---

**Total deviations:** 1 auto-fixed (1 blocking environment issue)
**Impact on plan:** Auto-fix essential -- environment was missing a listed dependency. No scope creep.

## Issues Encountered
- The plan's success criteria noted "8 tests" (5 stability + 3 Cowork) but test_stab.py actually contains 6 stability tests. Final suite is 9 tests total. All pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Excel/xlsx parsing) can proceed: openpyxl is confirmed in requirements.txt
- Phase 4 (pydantic model_validate) can proceed: pydantic>=2.0.0 is confirmed in requirements.txt
- Any Cowork user running `pip install -r requirements.txt` then `python -c "from scripts import *"` will get a clean [OK] or actionable [ERROR] for missing packages

---
*Phase: 01-stability-and-cowork-hardening*
*Completed: 2026-03-13*
