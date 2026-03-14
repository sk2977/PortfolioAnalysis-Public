# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 -- MVP

**Shipped:** 2026-03-14
**Phases:** 4 | **Plans:** 8 | **Sessions:** 1

### What Was Built
- Stability hardening: deprecated API fixes, warning-based error handling, preflight import checks
- Excel upload support with auto-format detection (Generic, Schwab)
- Forced-include tickers with weight floor, custom benchmark selection
- Pydantic v2 schema layer with numpy/pandas coercion for structured JSON
- Qualitative narrative engine: macro commentary, per-holding notes, method confidence disclosure
- 36 automated tests across 4 test modules

### What Worked
- TDD approach caught real issues (scikit-learn missing from venv, method spread NaN edge cases)
- Parallel wave execution cut wall-clock time significantly for independent plans
- Research phase identified that most features were shallower than expected (e.g., INPT-03 was just a CLAUDE.md change)
- Duck-typed coercion pattern kept schemas.py dependency-free from numpy/pandas

### What Was Inefficient
- Phase 4 plans ran in parallel but shared test_qual.py -- required defensive "if exists, append" logic
- VALIDATION.md was manually created by orchestrator for each phase rather than auto-generated
- Some executor agents duplicated work when parallel plans touched overlapping code (report.py in phase 4)

### Patterns Established
- "Wrap, don't rewrite" for schema layer -- pipeline functions keep returning plain dicts
- Claude generates narrative text, report.py assembles it -- no LLM library needed
- 5pp materiality threshold for both holding commentary and method spread disclosure
- All new generate_report() params use keyword-only with None defaults for backward compat

### Key Lessons
1. Research phase saves planning time: identifying "this is just a CLAUDE.md change" before planning prevents over-engineering
2. Preflight checks are high-value, low-cost: the import check caught a real missing dependency during development
3. Brownfield projects benefit from stability-first phasing: fixing silent exceptions first made all subsequent debugging faster

### Cost Observations
- Model mix: ~15% opus (orchestration), ~85% sonnet (research, planning, execution, verification)
- Sessions: 1 (full milestone in single conversation)
- Notable: Wave-based parallelism doubled throughput for phases 2 and 4

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 4 | Initial process -- TDD + wave parallelism established |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 36 | N/A | 0 (all deps already in requirements.txt) |

### Top Lessons (Verified Across Milestones)

1. Research-first planning prevents over-engineering
2. Stability before features -- fix silent errors early
