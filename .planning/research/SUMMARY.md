# Project Research Summary

**Project:** PortfolioAnalysis-Public
**Domain:** LLM-orchestrated portfolio optimization toolkit (Claude Cowork, public GitHub)
**Researched:** 2026-03-13
**Confidence:** MEDIUM

## Executive Summary

This is a brownfield enhancement milestone on an existing 6-module Python pipeline. The core computation stack (pandas, pyportfolioopt, yfinance, matplotlib) is not changing. The milestone adds four capabilities to a working tool: Excel input support, Pydantic-based structured outputs, Cowork execution hardening, and an LLM qualitative narrative layer. The recommended approach is purely additive -- thin wrappers and new modules layered over the existing pipeline without rewriting it. The only new dependencies are `openpyxl` and `pydantic>=2.0.0`. All LLM narrative generation stays in-process (Claude-as-generator in Cowork), with no Anthropic API key or SDK required.

The recommended build order is dictated by dependency structure: fix the pre-existing pandas deprecation bug first to establish a clean baseline, then add Excel parsing, then define Pydantic schemas, then wire up the qualitative layer. The schema layer is the critical dependency blocker -- all LLM narrative features depend on it being stable before any prompt templates are written. Attempting to write qualitative commentary prompts before the structured output contracts are finalized is the most likely source of rework.

The primary risks are (1) Cowork's Python execution environment not resolving the project venv, which causes complete pipeline failure on first run; (2) numpy/pandas types being rejected by Pydantic v2 at runtime, after all expensive computation has completed; and (3) LLM qualitative commentary contradicting the quantitative results if the prompt data contract is loose. All three are preventable with explicit mitigation steps that must be built before the feature code, not after.

---

## Key Findings

### Recommended Stack

The milestone requires exactly two new packages. `openpyxl>=3.1.0` is the only viable Excel engine for `.xlsx` files -- `xlrd` dropped `.xlsx` support in v2.0 and `xlwings` requires Microsoft Excel installed. `pydantic>=2.0.0` is the standard for Python data validation and is already used by the Anthropic SDK itself; v1 is deprecated and should not be introduced. No other new dependencies are warranted -- LangChain, the `anthropic` SDK, and `instructor` are all explicitly out of scope because the project's design premise is Claude-as-AI-layer via Cowork, not API calls.

One non-dependency code fix is required: `matplotlib.use('Agg')` must be set at the top of `visualize.py` before any other matplotlib import. Without this, chart generation will fail silently or raise in Cowork's headless execution context.

**Core technologies (additions only):**
- `openpyxl>=3.1.0`: Excel `.xlsx` read engine -- only viable choice for modern brokerage exports
- `pydantic>=2.0.0`: JSON validation and schema definition for structured outputs -- v2 is faster (Rust core) and required for `model_validate()` API
- `matplotlib Agg backend`: Non-interactive backend -- required for headless/Cowork execution, code fix not a new dependency

**Remove from requirements.txt:**
- `python-dotenv>=1.0.0`: never imported; confirmed unused

### Expected Features

The feature landscape divides cleanly into what is blocking user success (table stakes) and what fulfills the stated value proposition (differentiators).

**Must have (table stakes):**
- Excel `.xlsx` upload -- most brokers export `.xlsx`; users will try this and fail silently today
- LLM qualitative narrative -- the tool's stated premise is "AI-powered analysis"; a mechanical report with no prose fails the value prop
- Readable rebalancing output (buy/sell list) -- users need share counts, not weight deltas
- Fix deprecated pandas 2.x `reindex(method=...)` API -- breaks on current Python installs

**Should have (differentiators):**
- Structured output schema (Pydantic/JSON) -- enables consistent, parseable Claude output; dependency blocker for all LLM features
- Confidence/uncertainty disclosure -- surfaces disagreement between CAPM/Mean/EMA methods; data already exists, logic only
- Cache status reporting -- users in Cowork have no visibility into data freshness
- User-specified include list -- forces floor weights; `pyportfolioopt` supports this via `weight_bounds`

**Defer to a later milestone:**
- Rebalancing buy/sell list (requires collecting portfolio dollar value -- changes Phase 1 interaction model)
- Sector concentration flags (new data dependency; yfinance per-ticker slowness compounds download time)
- Fidelity CSV format support (nice to have; current three formats cover most US retail)
- Multi-broker file merge (useful but niche)

**Anti-features (do not build):**
- Anthropic API key / direct API calls -- violates core design, creates credential management problem in a public repo
- Web UI or dashboard -- scope creep; Cowork is already the conversational interface
- Backtesting, real-time prices, tax-lot tracking, automated trade execution

### Architecture Approach

The architecture is a sequential pipeline with Claude as the controller. No server, no CLI entry point. The new milestone adds a Schema Layer (`scripts/schemas.py` with Pydantic models) and a Qualitative Layer (`scripts/qualitative.py`) between the existing Analysis Layer and Presentation Layer. The key architectural decision is to wrap, not rewrite: pipeline functions continue returning plain Python dicts, and `model_validate()` is called at integration points in the CLAUDE.md workflow to validate and type those dicts. This avoids rewriting 1,400 lines of working code while adding type safety at the boundaries that matter.

**Major components:**
1. Input Layer (`parse_portfolio.py` + new `parse_xlsx()`) -- accept CSV or XLSX, normalize to portfolio dict, validate tickers
2. Data Layer (`market_data.py`) -- unchanged; yfinance price download with 4-hour pickle cache
3. Analysis Layer (`macro_analysis.py`, `optimize.py`) -- unchanged; produces macro and results dicts
4. Schema Layer (`scripts/schemas.py`, NEW) -- Pydantic models that wrap and validate the four pipeline dicts; defines the JSON schema Claude uses for structured output generation
5. Qualitative Layer (`scripts/qualitative.py`, NEW) -- prepares structured prompt data; Claude generates QualitativeAnalysis JSON block; `model_validate()` enforces the schema
6. Presentation Layer (`visualize.py`, `report.py` extended) -- report.py gains optional `qualitative` parameter; renders narrative sections when present, falls back to mechanical output when absent

### Critical Pitfalls

1. **NumPy/pandas types rejected by Pydantic v2** -- `optimize_portfolio()` returns `pd.Series`, `np.float64`, and `NaN` values that Pydantic v2 rejects without coercion. Add a `to_serializable()` utility that normalizes all pipeline dicts (cast numpy floats, convert Series to dict, replace NaN with None) before any schema validation is called.

2. **Cowork Python environment is not the project venv** -- Cowork does not auto-activate the project venv; imports will fail with `ModuleNotFoundError` for most users on first run. Add a preflight check script (`scripts/check_env.py`) and make venv activation the first step in CLAUDE.md, not buried in README.

3. **LLM qualitative commentary contradicts quantitative results** -- if the prompt passed to Claude for narrative does not include the actual numeric outputs (ERP value, Sharpe ratios, specific correlation values), Claude will generate plausible-sounding but potentially incorrect analysis. Pass ALL key numeric outputs explicitly in every qualitative prompt; never let Claude reason from labels alone.

4. **Excel cells arrive as wrong types** -- brokerage Excel exports format percentage and currency cells inconsistently; openpyxl may return `"0.25"` (string) or `0.25` (float) depending on cell format. Normalize all Excel-sourced numeric fields with `pd.to_numeric(errors='coerce')` after stripping `$`, `,`, `%` before any arithmetic.

5. **Investment advice framing in LLM output** -- qualitative templates that use "you should rebalance to..." or "this allocation is inappropriate for..." constitute investment recommendations on a public educational tool. Define framing guidelines and disclaimer injection before writing any prompt templates.

---

## Implications for Roadmap

Based on research, the dependency graph is clear and dictates a 4-phase structure. The schema layer is the hard dependency blocker in the middle; phases on either side of it are largely independent.

### Phase 1: Prerequisite Cleanup and Cowork Hardening
**Rationale:** Three pre-existing issues will corrupt new development if left unaddressed: the pandas deprecation bug, silent exception swallowing in cache write paths, and the venv-not-activated problem. These are zero-new-scope fixes that establish the reliable baseline all subsequent phases depend on.
**Delivers:** Clean baseline with reliable execution on modern Python/pandas installs; preflight environment check for Cowork users
**Addresses:** Table stakes "Working on current Python/pandas" fix; cache corruption risk (PITFALLS #5)
**Avoids:** Pitfall 2 (Cowork venv not activated), Pitfall 9 (deprecated pandas API), Pitfall 5 (pickle cache corruption)

### Phase 2: Excel Input Support
**Rationale:** Independent of the schema layer; extends the Input Layer only. Can be built and tested against real brokerage exports before the more complex phases begin. Resolves the most common user first-run failure (uploading a `.xlsx` file).
**Delivers:** `parse_xlsx()` function in `parse_portfolio.py`; openpyxl in requirements.txt; updated CLAUDE.md Phase 1 offering XLSX option
**Uses:** `openpyxl>=3.1.0`
**Implements:** Input Layer extension (thin wrapper reusing existing format-detection logic)
**Avoids:** Pitfall 3 (Excel numeric type coercion -- normalize before parsing), Pitfall 7 (Cowork file path resolution -- test path accessibility first), Pitfall 10 (Windows cp1252 encoding on non-ASCII cell values)

### Phase 3: Structured Output Schema Layer
**Rationale:** This is the dependency blocker. All LLM qualitative features require stable Pydantic models before any prompt templates are written. Building schemas after the pipeline is verified clean (Phase 1) means the dict shapes are known and the models can be written to match reality. Introducing Pydantic before fixing the pipeline would mean validating against a broken baseline.
**Delivers:** `scripts/schemas.py` with `MacroContext`, `OptimizationSummary`, `AllocationChange`, `QualitativeAnalysis` models; pydantic in requirements.txt; `to_serializable()` normalization utility; schema validation calls wired into CLAUDE.md workflow phases
**Uses:** `pydantic>=2.0.0`
**Implements:** Schema Layer (new)
**Avoids:** Pitfall 1 (numpy/pandas type rejection -- `to_serializable()` runs before `model_validate()`), Pitfall 6 (schemas too tightly coupled to current dict shape -- use `extra='ignore'`, validate only LLM-needed fields, add `schema_version`)

### Phase 4: LLM Qualitative Narrative Layer
**Rationale:** Depends on Phase 3 (stable schemas). This phase wires Claude's in-conversation generation into the pipeline via the Claude-as-generator pattern. The `qualitative.py` module prepares the structured prompt data; Claude generates the `QualitativeAnalysis` JSON block; `report.py` consumes it.
**Delivers:** `scripts/qualitative.py` with `prepare_qualitative_prompt()` function; extended `generate_report()` with optional `qualitative` parameter; updated CLAUDE.md with Phase 2.5 (schema validation) and Phase 4.5 (qualitative generation); disclaimer injection
**Uses:** Pydantic schemas from Phase 3; `matplotlib Agg backend` fix in `visualize.py`
**Implements:** Qualitative Layer (new); Presentation Layer extension
**Avoids:** Pitfall 4 (LLM narrative contradicts quant results -- pass all numeric outputs in prompt), Pitfall 8 (investment advice framing -- establish framing guidelines and disclaimer injection before writing templates)

### Phase Ordering Rationale

- Phase 1 before everything: the pandas deprecation bug and venv issue will cause failures in every subsequent phase's test runs if not fixed first
- Phase 2 before Phase 3: Excel is independent and its test results confirm the dict contract shapes that schemas must mirror
- Phase 3 before Phase 4: the qualitative layer has zero value without reliable schemas; writing prompt templates without schema enforcement produces inconsistent Claude output that breaks downstream report generation
- The `to_serializable()` utility and framing guidelines must be written at the start of their respective phases, not bolted on after feature code

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (LLM qualitative layer):** The exact Cowork execution model for Claude's structured JSON generation (whether mid-conversation self-validation via `model_validate()` works reliably) is MEDIUM confidence. Needs a small proof-of-concept in the actual Cowork environment before committing to the full implementation.
- **Phase 2 (Excel):** Cowork file path resolution for user-uploaded files is MEDIUM confidence. Test with a real `.xlsx` upload in Cowork before writing the parser.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Prerequisite cleanup):** All fixes are well-documented; pandas deprecation fix is a one-liner; preflight script is a standard pattern.
- **Phase 3 (Schema layer):** Pydantic v2 `BaseModel` / `model_validate()` patterns are HIGH confidence; `to_serializable()` normalization is a standard pattern for numpy/pandas interop.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | openpyxl and pydantic v2 are well-established, widely documented; Cowork Agg backend is standard practice for headless matplotlib |
| Features | MEDIUM | Table stakes grounded in codebase audit and CONCERNS.md; user expectation claims (broker export formats) unverified against real user data |
| Architecture | MEDIUM | Brownfield pipeline patterns are HIGH confidence; Cowork Python execution model (venv resolution, mid-conversation model_validate) is MEDIUM -- limited public documentation |
| Pitfalls | HIGH | numpy/pandas type issues, openpyxl cell type inconsistency, and LLM grounding failures are well-documented in literature; Cowork-specific issues are MEDIUM |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Cowork venv resolution:** How Cowork activates (or fails to activate) the project venv is not fully documented publicly. Validate with a `python -c "import pypfopt"` check in the actual Cowork environment before Phase 1 is marked complete.
- **Mid-conversation `model_validate()` pattern:** Whether Claude can reliably call `QualitativeAnalysis.model_validate({...})` on its own JSON output in a Cowork session needs a proof-of-concept. If it fails, the fallback is regex extraction of the JSON block with manual validation in `report.py`.
- **Cowork file path for uploads:** Verify how Cowork exposes a user-uploaded `.xlsx` file to Python's `open()` call before implementing `parse_xlsx()`. Document the supported method (e.g., "place file in project root") in README before shipping.
- **`pydantic` field constraints on lists:** `max_items` validator syntax in Pydantic v2 for list fields differs from v1; verify against current pydantic v2 docs before shipping `schemas.py`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase audit: all files in `scripts/`, `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/INTEGRATIONS.md`
- openpyxl documentation (training data): `.xlsx` engine selection, cell type behavior, numeric coercion patterns
- Pydantic v2 documentation (training data): `BaseModel`, `model_validate()`, `ConfigDict`, `Literal`, field constraints

### Secondary (MEDIUM confidence)
- Claude Desktop / Cowork execution model (training data, August 2025 cutoff): Python sandbox behavior, file path resolution, venv activation
- Anthropic structured outputs pattern (training data): JSON schema enforcement via tool_use / `response_format`; exact syntax may have changed post-cutoff

### Tertiary (LOW confidence)
- Fidelity as third most common broker format: domain expertise only, no verified source
- yfinance `Ticker.info` sector field availability: known as of training cutoff; yfinance API is unstable and changes frequently

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
