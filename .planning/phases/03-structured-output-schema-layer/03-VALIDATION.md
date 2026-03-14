---
phase: 3
slug: structured-output-schema-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, pytest.ini present) |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/test_sout.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_sout.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SOUT-01 | unit | `pytest tests/test_sout.py::test_schema_importable -x` | W0 | pending |
| 03-01-02 | 01 | 1 | SOUT-02 | unit | `pytest tests/test_sout.py::test_macro_context_coercion tests/test_sout.py::test_allocation_comparison_coercion -x` | W0 | pending |
| 03-01-03 | 01 | 1 | SOUT-02 | unit | `pytest tests/test_sout.py::test_nan_coercion -x` | W0 | pending |
| 03-01-04 | 01 | 1 | SOUT-02 | unit | `pytest tests/test_sout.py::test_model_dump_json_serializable -x` | W0 | pending |
| 03-02-01 | 02 | 1 | SOUT-03 | unit | `pytest tests/test_sout.py::test_validate_json_string -x` | W0 | pending |
| 03-02-02 | 02 | 1 | SOUT-03 | unit | `pytest tests/test_sout.py::test_schema_generable -x` | W0 | pending |
| 03-02-03 | 02 | 1 | SOUT-04 | manual | Review CLAUDE.md for validation call sites | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sout.py` -- stubs for SOUT-01, SOUT-02, SOUT-03
- [ ] `scripts/schemas.py` -- schema module must exist before tests can import

*Framework already installed; no new dependencies needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLAUDE.md contains validation call site instructions | SOUT-04 | Documentation change | Review CLAUDE.md for schema import and model_validate() instructions at each pipeline step |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
