# Architecture Patterns

**Domain:** Portfolio optimization toolkit running inside Claude Cowork (Claude Desktop)
**Researched:** 2026-03-13
**Confidence note:** WebSearch and template read were blocked during this session. Architecture analysis is based on direct codebase inspection (all 6 modules read) plus training-data knowledge of Pydantic/Anthropic structured outputs. Claims specific to Claude Cowork's Python sandbox capabilities are MEDIUM confidence (training data, unverified against current Cowork docs).

---

## Existing Architecture (Brownfield Baseline)

### Pattern

Sequential pipeline with Claude as the controller. No web framework, no server, no CLI entry point. Claude reads `CLAUDE.md`, calls Python functions from `scripts/` in order, and presents results conversationally.

```
[User] <-> [Claude AI -- orchestrator + narrative layer]
                    |
    +---------------+---------------+
    |               |               |
[Input Layer]  [Data Layer]   [Analysis Layer]
parse_portfolio  market_data    macro_analysis
                                optimize
                    |               |
              [Presentation Layer]
               visualize, report
```

### Current Data Contracts

All inter-module communication uses plain Python dicts. No type enforcement at module boundaries.

| Dict | Key fields | Produced by | Consumed by |
|------|-----------|-------------|-------------|
| portfolio | tickers (list), allocations (Series), raw_data (DataFrame), format_detected (str) | parse_portfolio | market_data, optimize, report |
| market | prices (DataFrame), benchmark (Series), failed (list), coverage (dict) | market_data | optimize, visualize |
| macro | pe_ratio, earnings_yield, treasury_yield, erp (float/None), interpretation (str), erp_history (DataFrame) | macro_analysis | visualize, report |
| results | optimal_allocations (Series), comparison (DataFrame), performance (dict), method_results (dict), cov_matrix (DataFrame), config (dict) | optimize | visualize, report |

---

## Recommended Architecture for New Milestone

### Core Change: Add a Structured Output Layer

The new milestone adds three capabilities that require a structured integration layer between the computation pipeline and Claude's narrative generation:

1. **Excel (.xlsx) input** -- new parse path in Input Layer
2. **Pydantic structured outputs** -- typed wrappers around existing dict contracts
3. **LLM qualitative narrative** -- Claude synthesizes macro + optimization data into prose

The recommended approach is to add a thin `schemas/` module that defines Pydantic models mirroring the existing dict contracts, and a `qualitative.py` module that Claude populates via structured output prompts.

### Revised Layer Diagram

```
[User]
  |
  | CSV or XLSX upload
  v
[Input Layer]
  parse_portfolio.py  (existing)
  + Excel parse path via openpyxl/pandas read_excel
  |
  v
[Data Layer]
  market_data.py  (existing)
  |
  v
[Analysis Layer]
  macro_analysis.py  (existing)
  optimize.py        (existing)
  |
  v
[Schema Layer]  <-- NEW
  scripts/schemas.py
  Pydantic models: PortfolioInput, MarketData, MacroContext,
                   OptimizationResults, QualitativeAnalysis
  |
  v
[Qualitative Layer]  <-- NEW
  scripts/qualitative.py
  Claude-generated narrative: macro interpretation, rebalancing rationale,
  risk commentary -- structured into QualitativeAnalysis model
  |
  v
[Presentation Layer]
  visualize.py  (existing)
  report.py     (existing, extended to consume QualitativeAnalysis)
```

---

## Component Boundaries

### Input Layer (parse_portfolio.py + Excel extension)

**Responsibility:** Accept user portfolio data in any supported format, normalize to the portfolio dict, validate tickers.

**New boundary:** Add `parse_xlsx()` function following the same return contract as `parse_csv()`. Use `pandas.read_excel()` (already available via openpyxl if added to requirements). Keep format detection logic in `_detect_format()` extended to check file extension first.

**Communicates with:** Data Layer (passes portfolio dict), Schema Layer (portfolio dict wrapped into PortfolioInput model).

### Schema Layer (scripts/schemas.py) -- NEW

**Responsibility:** Define Pydantic v2 models that give typed, validated representations of the existing pipeline dicts. These models serve two purposes:

1. They validate that pipeline stages produced well-formed output (catches silent failures earlier).
2. They define the JSON schema Claude uses to produce structured qualitative outputs.

**Key models:**

```python
class MacroContext(BaseModel):
    pe_ratio: float | None
    earnings_yield: float | None
    treasury_yield: float | None
    erp: float | None
    interpretation: str

class AllocationChange(BaseModel):
    ticker: str
    current_weight: float
    optimal_weight: float
    delta: float
    direction: Literal["increase", "decrease", "hold"]

class OptimizationSummary(BaseModel):
    method: str
    current_sharpe: float
    optimal_sharpe: float
    current_return: float
    optimal_return: float
    current_volatility: float
    optimal_volatility: float
    top_changes: list[AllocationChange]
    implementation_priority: Literal["HIGH", "MODERATE", "LOW"]

class QualitativeAnalysis(BaseModel):
    macro_narrative: str        # 2-3 sentence market context interpretation
    portfolio_narrative: str    # What the optimization found and why it matters
    top_actions: list[str]      # 3-5 plain-English rebalancing actions
    risk_commentary: str        # Risk-tolerance-specific commentary
    disclaimer: str             # Standard educational disclaimer
```

**Communicates with:** All upstream layers (receives dicts, validates them), Qualitative Layer (provides schemas for structured prompts), Presentation Layer (passes typed data to report.py).

**Confidence:** Pydantic v2 BaseModel pattern is HIGH confidence. The specific structured output mechanism for Claude-in-Cowork (whether Claude can produce a Pydantic-validated JSON block mid-conversation) is MEDIUM confidence -- see Cowork Execution note below.

### Qualitative Layer (scripts/qualitative.py) -- NEW

**Responsibility:** Prepare structured data summaries that Claude uses to generate QualitativeAnalysis. This module does NOT call an API. Instead, it formats the pipeline data into a prompt-ready dict that Claude receives and responds to with a structured JSON block matching QualitativeAnalysis schema.

**How it works in Cowork:**

Claude Cowork runs inside Claude Desktop. Claude executes Python scripts directly via the `computer_use` or file-execution pathway. The "structured output" pattern in this context is:

1. `qualitative.py` runs and returns a formatted dict of pipeline data (numbers, allocations, macro metrics).
2. Claude reads that dict output from the script run.
3. Claude then generates the QualitativeAnalysis JSON block using its own reasoning.
4. `report.py` receives the QualitativeAnalysis dict (Claude pastes/returns it) and includes it in the markdown report.

This is different from using the Anthropic API's `response_format` parameter (which enforces structured outputs server-side). In Cowork, Claude IS the generator, so the "enforcement" is the schema definition being visible to Claude in the prompt / CLAUDE.md instructions.

**Practical implementation:** Define QualitativeAnalysis as a Pydantic model in schemas.py. In CLAUDE.md, instruct Claude to populate it using `model.model_validate(json_dict)` to self-validate before passing to report.py. This gives schema enforcement without an API call.

**Communicates with:** Schema Layer (uses QualitativeAnalysis model), Presentation Layer (passes validated dict).

### Presentation Layer (visualize.py, report.py)

**Responsibility:** Generate charts and assemble final report. report.py extended to accept an optional `qualitative: dict` parameter and insert narrative sections.

**Change needed in report.py:** Add a `qualitative` parameter. If present, insert macro_narrative, portfolio_narrative, top_actions, and risk_commentary into the appropriate report sections instead of (or in addition to) the mechanical text currently generated.

**Communicates with:** Schema Layer (receives typed dicts), no new external dependencies.

---

## Data Flow (Revised)

```
CSV or XLSX
  -> parse_csv() or parse_xlsx()
  -> portfolio dict
  -> PortfolioInput.model_validate(portfolio_dict)   [validates + types]

  -> download_prices(tickers)
  -> market dict

  -> get_macro_context()
  -> macro dict
  -> MacroContext.model_validate(macro_dict)         [validates + types]

  -> optimize_portfolio(prices, benchmark, allocations, config)
  -> results dict
  -> OptimizationSummary.model_validate(results)     [validates + types]

  -> prepare_qualitative_prompt(macro_model, results_model)
  -> prompt_data dict                                [formatted for Claude]
  -> [Claude generates QualitativeAnalysis JSON]
  -> QualitativeAnalysis.model_validate(llm_output)  [self-validates]

  -> generate_report(results, macro, portfolio, charts, qualitative)
  -> report.md
```

---

## Patterns to Follow

### Pattern 1: Thin Schema Wrapper (don't rewrite, wrap)

**What:** Define Pydantic models that mirror existing dict keys exactly. Use `model_validate()` to wrap dicts after each pipeline stage, not before. The pipeline functions themselves stay unchanged.

**When:** Adding type safety to a brownfield dict-based pipeline.

**Why:** Avoids rewriting 1,400 lines of working code. Adds validation at integration points only.

```python
# In CLAUDE.md workflow, after optimize_portfolio():
from scripts.schemas import OptimizationSummary
try:
    summary = OptimizationSummary.model_validate(results_dict)
except ValidationError as e:
    print(f"[ERROR] Optimization results malformed: {e}")
```

### Pattern 2: Claude-as-Structured-Generator

**What:** Rather than calling an LLM API for structured outputs, Claude (running in Cowork) generates the structured JSON itself based on a schema provided in CLAUDE.md instructions.

**When:** The execution environment IS Claude (Cowork/Desktop), so there is no API boundary.

**Example CLAUDE.md instruction addition:**
```
After running optimization, generate a QualitativeAnalysis JSON block
matching the schema in scripts/schemas.py. Validate it with:
  from scripts.schemas import QualitativeAnalysis
  qa = QualitativeAnalysis.model_validate({your_json})
Then pass `qa.model_dump()` to generate_report() as the `qualitative` parameter.
```

### Pattern 3: Optional Qualitative Pass-through

**What:** All new qualitative fields are optional in generate_report(). If `qualitative=None`, the report renders exactly as today. If present, narrative sections replace/augment mechanical text.

**When:** Adding features to existing output modules without breaking existing behavior.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Rewriting Pipeline Functions to Return Pydantic Models

**What:** Changing parse_csv(), optimize_portfolio(), etc. to return Pydantic models instead of dicts.

**Why bad:** Breaks the existing working pipeline immediately, creates large diff, introduces Pydantic import dependencies into all existing modules, harder to test incrementally.

**Instead:** Keep pipeline functions returning dicts. Validate at integration points in CLAUDE.md workflow using `model_validate()`.

### Anti-Pattern 2: Adding an Anthropic API Client

**What:** Importing `anthropic` library and making direct API calls from qualitative.py for narrative generation.

**Why bad:** Requires API key management in a public repo, adds cost per run, violates the project's stated "out of scope" constraint (Claude IS the AI layer). The PROJECT.md explicitly excludes this.

**Instead:** Claude generates the qualitative output in-conversation. qualitative.py only prepares the structured input data; Claude produces the output.

### Anti-Pattern 3: Storing Pydantic Models in Pickle Cache

**What:** Caching OptimizationSummary or QualitativeAnalysis Pydantic objects in the existing pickle cache.

**Why bad:** Pickle of Pydantic models is version-sensitive. If schemas change (which they will during development), cached files silently load stale/incompatible models.

**Instead:** Cache only raw dicts (as today). Convert to Pydantic models fresh on each run after cache load.

---

## Suggested Build Order

Dependencies between new components determine this order:

1. **Fix deprecated pandas API** (no dependencies, unblocks clean baseline)
   - Fix `reindex(..., method='ffill')` in market_data.py or macro_analysis.py

2. **Add Excel input support** (extends Input Layer only, no new dependencies)
   - Add `parse_xlsx()` to parse_portfolio.py
   - Add openpyxl to requirements.txt
   - Update CLAUDE.md Phase 1 to offer XLSX option

3. **Add schemas.py** (depends on stable dict contracts, which step 1 validates)
   - Define all Pydantic models
   - Add pydantic to requirements.txt
   - No changes to existing modules yet

4. **Validate pipeline with schemas** (depends on schemas.py)
   - Add model_validate() calls in CLAUDE.md workflow phases
   - Smoke test with sample_portfolio.csv to confirm dict shapes match models

5. **Add qualitative.py** (depends on schemas.py models)
   - prepare_qualitative_prompt() function
   - Returns formatted dict ready for Claude to act on

6. **Extend report.py for qualitative output** (depends on schemas.py QualitativeAnalysis)
   - Add optional `qualitative` parameter to generate_report()
   - Insert narrative sections when present

7. **Update CLAUDE.md** (depends on all above)
   - Add Phase 2.5: Schema validation step
   - Add Phase 4.5: Qualitative generation step
   - Document the self-validation pattern

---

## Cowork Execution Constraints

**Confidence: MEDIUM** -- based on training data knowledge of Claude Desktop architecture, unverified against current Cowork release notes.

Claude Desktop (Cowork) executes Python scripts by running them in the local Python environment. Scripts import from the project directory normally. Key constraints that affect the new components:

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| No Anthropic API key available | Cannot use `anthropic` client library | Use Claude-as-generator pattern |
| Python sandbox may limit network calls | macro_analysis.py's Multpl.com scraping may be restricted | Existing fallback to stale cache handles this |
| Script output is text-only to Claude | Pydantic ValidationError messages must be cp1252-safe | Use `[ERROR]` prefix, no Unicode in error strings |
| Pydantic v2 required for model_validate() | Pydantic v1 uses .parse_obj() instead | Pin `pydantic>=2.0` in requirements.txt |

---

## Scalability Considerations

This is a single-user desktop tool. Scalability concerns are about complexity management, not load:

| Concern | Current | After Milestone |
|---------|---------|----------------|
| Schema drift | No validation, silent failures | Pydantic catches at integration points |
| Report maintainability | Mechanical string formatting | Narrative sections isolated in QualitativeAnalysis |
| Adding new data sources | Must thread new keys through all downstream dicts | Add field to Pydantic model first, pipeline follows |
| Testing | No test suite | schemas.py models are independently testable with sample dicts |

---

## Sources

- Direct codebase inspection: `scripts/report.py`, `scripts/optimize.py`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/PROJECT.md`
- Pydantic v2 documentation (training data, HIGH confidence for BaseModel/model_validate patterns)
- Claude Cowork execution model (training data, MEDIUM confidence -- verify against current Claude Desktop release notes before implementation)
- Anthropic structured outputs API (training data, HIGH confidence that `response_format` / tool_use JSON schema enforcement exists; MEDIUM confidence on exact syntax as of 2026)
