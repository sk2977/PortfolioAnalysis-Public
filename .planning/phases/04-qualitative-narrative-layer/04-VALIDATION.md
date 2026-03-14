---
phase: 4
slug: qualitative-narrative-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pytest.ini |
| **Quick run command** | `python -m pytest tests/test_qual.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_qual.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_qual.py::test_macro_narrative_in_report -x` | W0 | pending |
| 04-01-02 | 01 | 1 | QUAL-02 | unit | `pytest tests/test_qual.py::test_holding_commentary_threshold -x` | W0 | pending |
| 04-01-03 | 01 | 1 | QUAL-03 | unit | `pytest tests/test_qual.py::test_method_spread_calc -x` | W0 | pending |
| 04-01-04 | 01 | 1 | QUAL-04 | unit | `pytest tests/test_qual.py::test_disclaimer_present -x` | W0 | pending |
| 04-02-01 | 02 | 1 | COWK-03 | unit | `pytest tests/test_qual.py::test_readme_cowork_section -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qual.py` -- covers QUAL-01, QUAL-02, QUAL-03, QUAL-04, COWK-03

*No new framework or fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLAUDE.md narrative workflow produces useful output | QUAL-01 | Requires Claude in-session | Run full workflow and check narrative quality |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
