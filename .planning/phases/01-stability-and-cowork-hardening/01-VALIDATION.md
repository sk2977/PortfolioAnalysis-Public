---
phase: 1
slug: stability-and-cowork-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Wave 0 installs) |
| **Config file** | none -- create pytest.ini in Wave 0 |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | STAB-01 | unit | `python -m pytest tests/test_stab.py::test_reindex_ffill -x` | Wave 0 | pending |
| 01-01-02 | 01 | 1 | STAB-01 | unit | `python -m pytest tests/test_stab.py::test_no_reindex_warning -x` | Wave 0 | pending |
| 01-01-03 | 01 | 1 | STAB-02 | unit | `python -m pytest tests/test_stab.py::test_cache_warn_on_failure -x` | Wave 0 | pending |
| 01-01-04 | 01 | 1 | STAB-02 | unit | `python -m pytest tests/test_stab.py::test_pipeline_survives_cache_failure -x` | Wave 0 | pending |
| 01-01-05 | 01 | 1 | STAB-03 | unit | `python -m pytest tests/test_stab.py::test_matplotlib_agg_backend -x` | Wave 0 | pending |
| 01-02-01 | 02 | 1 | COWK-01 | unit | `python -m pytest tests/test_cowk.py::test_preflight_passes -x` | Wave 0 | pending |
| 01-02-02 | 02 | 1 | COWK-01 | unit | `python -m pytest tests/test_cowk.py::test_preflight_fails_on_missing -x` | Wave 0 | pending |
| 01-02-03 | 02 | 1 | COWK-02 | unit | `python -m pytest tests/test_cowk.py::test_requirements_contents -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` -- empty, marks tests as package
- [ ] `tests/test_stab.py` -- stubs for STAB-01, STAB-02, STAB-03
- [ ] `tests/test_cowk.py` -- stubs for COWK-01, COWK-02
- [ ] `pytest` added to requirements.txt dev dependencies or installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cowork sandbox executes pipeline | COWK-01 | Requires Claude Cowork environment | Run sample_portfolio.csv workflow in Cowork session |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
