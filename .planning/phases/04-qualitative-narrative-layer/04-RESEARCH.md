# Phase 4: Qualitative Narrative Layer - Research

**Researched:** 2026-03-13
**Domain:** LLM-driven narrative generation, report enhancement, README documentation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | Claude generates macro-regime narrative interpreting ERP, treasury yields, and P/E in plain language | Claude IS the AI layer -- no API needed; narrative generation is a CLAUDE.md instruction update + report.py section stub |
| QUAL-02 | Claude generates per-holding commentary for material rebalancing actions (>5% weight change) | comparison DataFrame already contains Difference column; threshold filter is trivial; commentary is Claude's in-context generation |
| QUAL-03 | Claude discloses method disagreement (CAPM vs Mean vs EMA spread) when spread is material | returns_dict is already in optimize_portfolio() output; spread calculation is simple arithmetic; disclosure is narrative text |
| QUAL-04 | Qualitative sections integrated into report output alongside mechanical tables | report.py accepts free-text params; integration is adding parameters + insertion points |
| COWK-03 | README updated with Cowork setup instructions (clone, link project, upload portfolio) | Pure documentation -- no code changes; README already has basic setup, needs Cowork-specific steps added |
</phase_requirements>

---

## Summary

Phase 4 adds the qualitative narrative that is the tool's stated core value proposition: "actionable portfolio rebalancing recommendations combining quantitative optimization with LLM qualitative analysis." Three phases of infrastructure (stability, input expansion, structured schemas) have already been completed. Phase 4 is primarily a CLAUDE.md workflow update and a moderate extension to `report.py` -- not a new module.

The key insight is that Claude itself is the AI layer. There is no external LLM API call. Claude generates narrative text during the Cowork session by reading structured data (macro dict, comparison DataFrame, returns_dict) and producing plain-English commentary. The planner must not design tasks that attempt to call an external API or install an LLM library. The pattern is: (1) extend `report.py` to accept narrative strings as parameters and emit them in the right sections, (2) extend CLAUDE.md to instruct Claude when and how to generate those strings, (3) update README for Cowork users.

The one non-trivial technical decision is where the method-spread calculation lives. It requires per-method expected return vectors from `returns_dict`, which are `pd.Series` objects already present in `optimize_portfolio()` output but not currently passed to `generate_report()`. The planner needs to decide: compute the spread inside `report.py` (add `returns_dict` parameter), or compute it in the workflow step and pass the result as a pre-computed summary string.

**Primary recommendation:** Compute spread in report.py (add `returns_dict` parameter) so the logic is testable in isolation. Claude generates the disclosure prose from the pre-computed spread value.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (string formatting) | 3.10+ | Narrative string assembly | No new dependency needed |
| pytest | installed (see tests/) | Unit tests for spread logic and report integration | Existing test pattern throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | already installed | Access comparison DataFrame and returns_dict Series | Spread calculation across CAPM/Mean/EMA |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-report spread calc | Pre-compute in CLAUDE.md step and pass string | Pre-compute is simpler for planner but untestable; report.py approach keeps logic in Python where it can be tested |
| Extending report.py | New generate_narrative.py module | Unnecessary -- report.py is already the output assembly point |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files or directories needed. Changes are confined to:

```
scripts/
    report.py          # Add narrative parameters + 3 new output sections
    schemas.py         # No change expected
CLAUDE.md              # Add Phase 6 narrative generation instructions
README.md              # Add Cowork setup section
tests/
    test_qual.py       # New: unit tests for spread calc and report sections
```

### Pattern 1: Narrative Parameters in generate_report()

**What:** Add optional keyword parameters to `generate_report()` for each qualitative section. Caller passes pre-generated strings; function inserts them at defined section markers.

**When to use:** Keeps report.py as the single assembly point. Claude generates strings in-conversation and passes them as arguments.

**Example:**
```python
# In scripts/report.py
def generate_report(optimization_results, macro_context, portfolio_info,
                    chart_paths=None, output_dir=OUTPUT_DIR,
                    macro_narrative=None,
                    holding_commentary=None,
                    method_spread_note=None):
    """
    macro_narrative : str or None
        Plain-language ERP/P/E interpretation produced by Claude.
    holding_commentary : dict or None
        {ticker: str} commentary for holdings with abs(Difference) > 0.05.
    method_spread_note : str or None
        Disclosure string if CAPM/Mean/EMA spread is material.
    """
    ...
    # After the macro table:
    if macro_narrative:
        lines.append(f"### Macro Interpretation")
        lines.append(f"")
        lines.append(macro_narrative)
        lines.append(f"")

    # After allocation table, per holding:
    if holding_commentary:
        lines.append(f"### Holding Commentary")
        lines.append(f"")
        for ticker, note in holding_commentary.items():
            lines.append(f"**{ticker}**: {note}")
        lines.append(f"")

    # Before or after performance comparison:
    if method_spread_note:
        lines.append(f"> **Confidence Note:** {method_spread_note}")
        lines.append(f"")
```

**Why this pattern:** Optional parameters with `None` defaults keep backward compatibility. Existing tests pass without modification. New tests can exercise each parameter independently.

### Pattern 2: Method Spread Calculation

**What:** Compute the spread between CAPM, Mean Historical, and EMA expected return estimates for each ticker. Report the maximum spread across tickers as the materiality indicator.

**When to use:** Called inside `generate_report()` or as a standalone helper. Triggered when `returns_dict` is passed.

**Example:**
```python
# In scripts/report.py (new helper function)
def _compute_method_spread(returns_dict):
    """
    Compute max pairwise spread between CAPM, Mean, EMA expected returns.

    Parameters
    ----------
    returns_dict : dict
        {'capm': pd.Series, 'mean': pd.Series, 'ema': pd.Series}
        Output from optimize.calculate_expected_returns().

    Returns
    -------
    float
        Maximum absolute spread across all tickers and method pairs.
    dict
        {ticker: max_spread} for tickers where spread exceeds threshold.
    """
    import pandas as pd
    methods = ['capm', 'mean', 'ema']
    available = {m: returns_dict[m] for m in methods if m in returns_dict}
    if len(available) < 2:
        return 0.0, {}

    df = pd.DataFrame(available)
    # Per-ticker spread = max - min across methods
    per_ticker_spread = df.max(axis=1) - df.min(axis=1)
    max_spread = float(per_ticker_spread.max())
    # Flag tickers with spread > 5 percentage points (0.05)
    flagged = {
        ticker: float(spread)
        for ticker, spread in per_ticker_spread.items()
        if spread > 0.05
    }
    return max_spread, flagged
```

**Materiality threshold:** 5 percentage points (0.05) spread between highest and lowest method return estimate for any single ticker. This is a judgment call -- justified because a 5pp spread in expected returns is large enough to materially affect optimal weight.

### Pattern 3: CLAUDE.md Narrative Generation Instructions

**What:** Add a new "Phase 5.5: Qualitative Narrative" step in CLAUDE.md between the optimize step (Phase 4) and report step (Phase 6). Claude reads validated schema objects and generates the three narrative strings.

**When to use:** Every analysis session. Claude executes this step in-conversation with no code execution required.

**Example CLAUDE.md addition:**
```markdown
### Phase 5.5: Qualitative Narrative

Before calling generate_report(), generate three narrative strings:

**Macro narrative (QUAL-01):**
Read macro_validated.erp, macro_validated.pe_ratio, macro_validated.treasury_yield,
and macro_validated.interpretation. Write 2-3 sentences of plain-language regime
interpretation. Must cite the actual ERP value and P/E. Example:
> "At a P/E of 27.4, the S&P 500 earnings yield is 3.6%, below the 10Y Treasury at 4.3%,
> producing an ERP of -0.7%. This negative premium suggests equities offer no
> compensation over risk-free bonds at current valuations -- a historically elevated
> risk environment for equity investors."

**Holding commentary (QUAL-02):**
From alloc_validated.difference, identify tickers where abs(difference) > 0.05.
For each, write one sentence explaining the direction and magnitude of the change.
Use plain English; do not use investment advice language.

**Method spread note (QUAL-03):**
Compute the spread between CAPM, mean historical, and EMA expected returns.
If any ticker's spread exceeds 5 percentage points:
> "[TICKER]'s expected return estimate ranges from X% (CAPM) to Y% (EMA) --
> a spread of Zpp. These results should be treated as lower confidence."
If no spread exceeds threshold, set method_spread_note = None.

Then call generate_report() with all three strings:
\```python
report_md = generate_report(results, macro, portfolio, charts,
                             macro_narrative=macro_narrative,
                             holding_commentary=holding_commentary,
                             method_spread_note=method_spread_note)
\```
```

### Pattern 4: README Cowork Setup Section

**What:** Add a dedicated "Claude Cowork Setup" section to README.md between Prerequisites and existing Setup.

**When to use:** Every public README update for Cowork-targeted tools.

**Content to cover:**
1. Open Claude Desktop and enable Cowork (or navigate to claude.ai)
2. Create a new Cowork session
3. Link the project folder (drag-and-drop or "Add project")
4. Upload portfolio file (CSV or XLSX) via the attachment button
5. Type the opening prompt from prompt.md
6. Cowork runs Python scripts in the linked project directory

### Anti-Patterns to Avoid

- **Calling an external LLM API:** Claude IS the AI layer. No API key, no `anthropic` library, no `openai` library. Any task that adds an API call is wrong.
- **Adding a new generate_narrative.py module:** The narrative is generated in-conversation by Claude. Only the insertion points in `report.py` need code.
- **Hardcoding narrative text in report.py:** The report generator must accept narrative as input, not generate it internally. Internal generation would bypass Claude's reasoning.
- **Blocking generate_report() when narratives are None:** All three narrative parameters must be optional with `None` defaults. Existing workflow (no narrative) must still produce a valid report.
- **Using Unicode symbols in print() output:** cp1252 encoding constraint. Use `[OK]`, `[WARN]`, `->` etc.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM text generation | Custom API wrapper, template engine | Claude in-conversation | Claude IS the AI layer; no API needed |
| Markdown formatting | Custom Markdown library | Python string formatting (already used in report.py) | report.py already uses string joins; no new dep needed |
| ERP regime classification | Custom threshold table | Existing `_get_interpretation()` in macro_analysis.py | Already implemented with percentile buckets; reuse the output |

**Key insight:** This phase is primarily instruction engineering (CLAUDE.md) and report wiring (report.py). The quantitative data is already computed by Phases 1-3. Phase 4 connects that data to Claude's natural language generation capability through explicit workflow steps.

---

## Common Pitfalls

### Pitfall 1: Narrative Hardcoded in report.py

**What goes wrong:** Developer implements narrative generation inside `generate_report()` using heuristics or canned strings. The narrative no longer reflects Claude's actual reasoning about the specific portfolio.

**Why it happens:** Easier to write than adding CLAUDE.md instructions and testing the workflow end-to-end.

**How to avoid:** Narrative strings are always passed as parameters. `generate_report()` only assembles -- it never generates prose. Enforce this in tests: call `generate_report()` with explicit strings and assert they appear verbatim in output.

**Warning signs:** Any `if erp < 0:` branching logic that produces user-facing prose inside report.py (beyond the existing `interpretation` field which is already handled).

### Pitfall 2: Breaking Existing Report Tests

**What goes wrong:** Adding required parameters to `generate_report()` causes existing callers and tests to fail with TypeError.

**Why it happens:** Not using keyword arguments with `None` defaults.

**How to avoid:** All new parameters MUST use keyword-only arguments with `None` defaults. Existing call signature `generate_report(results, macro, portfolio, charts)` must continue to work unchanged.

**Warning signs:** Any test in the existing suite that calls `generate_report()` failing after the change.

### Pitfall 3: Spread Calculation on Misaligned Series

**What goes wrong:** CAPM, Mean, and EMA return Series have different index sets (if a ticker failed for one method). `pd.DataFrame(returns_dict)` fills with NaN, and `max - min` propagates NaN into spread calculation.

**Why it happens:** `calculate_expected_returns()` in optimize.py may not always produce all three methods successfully.

**How to avoid:** Use `df.max(axis=1) - df.min(axis=1)` which skips NaN by default in pandas (min/max with skipna=True). Add a guard: if fewer than 2 methods succeeded, return spread=0 and skip disclosure.

**Warning signs:** `NaN` values in `_compute_method_spread()` output.

### Pitfall 4: Per-Holding Commentary on ALL Holdings

**What goes wrong:** Claude generates a commentary note for every ticker regardless of weight change, producing an overly long report.

**Why it happens:** Misreading QUAL-02 as "comment on all holdings" rather than "comment on material changes."

**How to avoid:** QUAL-02 threshold is explicit: abs(Difference) > 0.05 (5 percentage points). Only holdings meeting this threshold receive commentary. State this threshold explicitly in CLAUDE.md instructions.

**Warning signs:** holding_commentary dict with more entries than there are material changes.

### Pitfall 5: Cowork Disclaimer Confusion

**What goes wrong:** The report disclaimer (already present in report.py line 160-163) gets duplicated or removed when adding the qualitative sections.

**Why it happens:** Inserting new sections near the bottom of the report where the disclaimer lives.

**How to avoid:** The disclaimer section must remain the last element of the report. All new qualitative sections insert before the `---` disclaimer separator. The existing disclaimer text is already compliant with QUAL-04 -- no modification needed.

---

## Code Examples

### Existing Disclaimer (QUAL-04 -- already compliant)

```python
# Source: scripts/report.py lines 157-163
lines.append(f"---")
lines.append(f"")
lines.append(f"**Disclaimer**: This analysis is for educational and informational "
             f"purposes only. It does not constitute financial advice. Past performance "
             f"does not guarantee future results. Always consult a qualified financial "
             f"advisor before making investment decisions.")
```

QUAL-04 requires the disclaimer to "distinguish educational analysis from investment advice." The existing text already satisfies this. No change to disclaimer content is needed -- only ensure it survives the report.py refactor.

### Accessing Method Returns for Spread (from optimize.py output)

```python
# returns_dict is in optimize_portfolio() return value (line 208, optimize.py)
# Structure: {'capm': pd.Series, 'mean': pd.Series, 'ema': pd.Series}
# Each Series: index=tickers, values=expected annual return (float)
returns_dict = results['returns_dict']

# CAPM returns for VTI:
capm_vti = returns_dict['capm']['VTI']  # e.g. 0.087

# Max spread across all tickers between any two methods:
import pandas as pd
df = pd.DataFrame(returns_dict)
spread = df.max(axis=1) - df.min(axis=1)
# spread is a Series: index=tickers, values=spread in decimal (0.05 = 5pp)
```

### Reading Comparison for QUAL-02 Threshold

```python
# comparison DataFrame: index=tickers, columns=['Current', 'Optimal', 'Difference']
# Already present in results['comparison'] and alloc_validated.difference
comparison = results['comparison']
material = comparison[comparison['Difference'].abs() > 0.05]
# material is the subset of tickers with >5pp weight change
```

### Current generate_report() Signature (before Phase 4)

```python
# Source: scripts/report.py line 14-15
def generate_report(optimization_results, macro_context, portfolio_info,
                    chart_paths=None, output_dir=OUTPUT_DIR):
```

After Phase 4, target signature:

```python
def generate_report(optimization_results, macro_context, portfolio_info,
                    chart_paths=None, output_dir=OUTPUT_DIR,
                    macro_narrative=None,
                    holding_commentary=None,
                    method_spread_note=None,
                    returns_dict=None):
```

`returns_dict` is optional: if provided, `_compute_method_spread()` runs internally and the result informs the method_spread_note insertion even if the caller didn't pre-compute it. If `method_spread_note` is also provided, it takes precedence (Claude's narrative wins over mechanical computation).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static boilerplate interpretation in report | Claude-generated narrative citing actual values | Phase 4 | Report reflects specific portfolio context, not generic text |
| No per-holding prose | Per-holding commentary for material changes | Phase 4 | Users understand why specific tickers are flagged |
| No method uncertainty disclosure | Explicit spread disclosure when methods disagree | Phase 4 | Honest confidence signaling; distinguishes reliable from uncertain recommendations |

---

## Open Questions

1. **Exact materiality threshold for method spread**
   - What we know: 5pp (0.05) is proposed for QUAL-03
   - What's unclear: No industry-standard threshold for "material disagreement" between return estimation methods
   - Recommendation: Use 5pp as default; add a comment in code explaining the rationale. The planner can expose this as a config constant if the user wants to tune it later.

2. **mid-conversation model_validate() pattern in Cowork -- MEDIUM confidence (from STATE.md)**
   - What we know: Pydantic v2 model_validate() works in standard Python; STATE.md flags Cowork specifically as MEDIUM confidence
   - What's unclear: Whether Cowork's Python environment has a version of pydantic that behaves differently or has import constraints in multi-step sessions
   - Recommendation: The Phase 4 planner should include a proof-of-concept task: run the Phase 5.5 workflow stub in a real Cowork session before committing to full implementation. If model_validate() fails, the fallback is to read raw dict fields directly from the results dict.

3. **Cowork file upload path for README instructions**
   - What we know: README needs Cowork-specific setup steps; Claude Desktop Cowork links a project folder
   - What's unclear: Exact UI steps differ between Claude Desktop and claude.ai web Cowork; UI may change
   - Recommendation: Write README instructions for Claude Desktop (the more common path for this use case). Note that web Cowork instructions may differ.

---

## Validation Architecture

nyquist_validation is enabled (config.json `workflow.nyquist_validation: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed, confirmed by existing tests/) |
| Config file | none -- pytest auto-discovers from tests/ directory |
| Quick run command | `python -m pytest tests/test_qual.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | macro_narrative parameter appears in report output when provided | unit | `python -m pytest tests/test_qual.py::test_macro_narrative_in_report -x` | Wave 0 |
| QUAL-02 | holding_commentary appears for tickers with abs(diff) > 0.05, absent otherwise | unit | `python -m pytest tests/test_qual.py::test_holding_commentary_threshold -x` | Wave 0 |
| QUAL-03 | _compute_method_spread() returns correct spread; spread note appears in report when material | unit | `python -m pytest tests/test_qual.py::test_method_spread_calc -x` | Wave 0 |
| QUAL-04 | Disclaimer text survives report refactor and appears last | unit | `python -m pytest tests/test_qual.py::test_disclaimer_present -x` | Wave 0 |
| COWK-03 | README contains "Cowork" and required setup keywords | unit | `python -m pytest tests/test_qual.py::test_readme_cowork_section -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_qual.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qual.py` -- covers QUAL-01, QUAL-02, QUAL-03, QUAL-04, COWK-03

No new framework or fixtures needed. Existing `tests/__init__.py` and pytest auto-discovery handle setup. The new test file follows the same pattern as `test_sout.py` -- direct imports from `scripts.*`, no fixtures file required.

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `scripts/report.py` -- generate_report() signature, existing disclaimer, section structure
- Direct code inspection: `scripts/optimize.py` -- returns_dict structure, _run_single_optimization() output, method_results dict
- Direct code inspection: `scripts/schemas.py` -- MacroContext, AllocationComparison, PortfolioRecommendation field names
- Direct code inspection: `scripts/macro_analysis.py` -- ERP calculation, _get_interpretation() logic
- Direct code inspection: `.planning/REQUIREMENTS.md` -- QUAL-01 through QUAL-04 and COWK-03 exact wording
- Direct code inspection: `CLAUDE.md` -- existing workflow phase structure, "Claude IS the AI layer" constraint
- Direct code inspection: `tests/` -- existing test patterns (pytest, direct imports, no fixtures)

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` -- Cowork model_validate() pattern flagged as MEDIUM confidence; proof-of-concept recommended
- `README.md` -- existing setup steps that Cowork section must complement without breaking

### Tertiary (LOW confidence)

- None. All findings are from direct code and document inspection of the project at hand.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries; all tools already in project
- Architecture: HIGH -- Pattern is derived directly from existing report.py structure and CLAUDE.md workflow
- Pitfalls: HIGH -- Identified from direct reading of existing code; backward-compat and NaN risks are concrete
- Validation: HIGH -- Test framework confirmed present; test patterns observed in existing test files

**Research date:** 2026-03-13
**Valid until:** Stable (no external dependencies; validity tied to codebase changes, not ecosystem drift)
