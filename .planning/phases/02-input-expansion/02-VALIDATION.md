---
phase: 2
slug: input-expansion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in use from Phase 1) |
| **Config file** | pytest.ini (created in Phase 1) |
| **Quick run command** | `pytest tests/test_inpt.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_inpt.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INPT-01 | unit | `pytest tests/test_inpt.py::test_parse_excel_generic -x` | W0 | pending |
| 02-01-02 | 01 | 1 | INPT-01 | unit | `pytest tests/test_inpt.py::test_parse_excel_schwab -x` | W0 | pending |
| 02-01-03 | 01 | 1 | INPT-01 | unit | `pytest tests/test_inpt.py::test_parse_excel_missing_file -x` | W0 | pending |
| 02-02-01 | 02 | 1 | INPT-02 | unit | `pytest tests/test_inpt.py::test_weight_bounds_no_include -x` | W0 | pending |
| 02-02-02 | 02 | 1 | INPT-02 | unit | `pytest tests/test_inpt.py::test_weight_bounds_with_include -x` | W0 | pending |
| 02-02-03 | 02 | 1 | INPT-02 | unit | `pytest tests/test_inpt.py::test_include_ticker_forced -x` | W0 | pending |
| 02-03-01 | 03 | 1 | INPT-03 | unit | `pytest tests/test_inpt.py::test_custom_benchmark_param -x` | W0 | pending |
| 02-03-02 | 03 | 1 | INPT-03 | manual | Review CLAUDE.md after implementation | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_inpt.py` -- stubs for INPT-01, INPT-02, INPT-03
- [ ] Fixture: small in-memory .xlsx file using openpyxl directly (no actual brokerage file needed)

*Existing infrastructure (pytest.ini, tests/__init__.py) covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLAUDE.md Phase 3 snippet no longer hardcodes VTI | INPT-03 | Documentation change, not code | Review CLAUDE.md Phase 3 workflow snippet |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
