# Roadmap: PortfolioAnalysis

## Overview

This milestone transforms a working but fragile pipeline into a polished, Cowork-native tool. Starting from the existing 6-module Python pipeline, four phases deliver in dependency order: clean the baseline so new code runs reliably, add Excel input so users can upload standard broker exports, lock down structured output schemas as the hard dependency for LLM features, then wire in the qualitative narrative layer that fulfills the tool's core value proposition.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Stability and Cowork Hardening** - Fix pre-existing bugs and guarantee clean execution in Cowork
- [ ] **Phase 2: Input Expansion** - Add Excel upload support, include-list, and custom benchmark
- [ ] **Phase 3: Structured Output Schema Layer** - Define Pydantic schemas and wire validation into pipeline
- [ ] **Phase 4: Qualitative Narrative Layer** - Wire Claude's in-conversation LLM generation into the report

## Phase Details

### Phase 1: Stability and Cowork Hardening
**Goal**: The pipeline runs cleanly on current Python/pandas installs and Claude Cowork can execute it without manual intervention
**Depends on**: Nothing (first phase)
**Requirements**: STAB-01, STAB-02, STAB-03, COWK-01, COWK-02
**Success Criteria** (what must be TRUE):
  1. Running the pipeline against sample_portfolio.csv produces no pandas deprecation warnings or reindex-related AttributeError
  2. A cache write failure produces a visible log warning instead of silently swallowing the error
  3. Chart generation completes without RuntimeError in a headless environment (no display attached)
  4. A new Cowork user can run a preflight check that confirms all required packages are importable before starting the workflow
  5. requirements.txt installs openpyxl and pydantic while python-dotenv has been removed
**Plans**: TBD

### Phase 2: Input Expansion
**Goal**: Users can upload any standard broker file and control which tickers enter the optimization
**Depends on**: Phase 1
**Requirements**: INPT-01, INPT-02, INPT-03
**Success Criteria** (what must be TRUE):
  1. A user uploading a .xlsx brokerage export receives the same parsed holdings table as a CSV user
  2. A user can name specific tickers that must appear in the optimized portfolio (they are not zeroed out)
  3. A user can specify a benchmark ticker other than VTI and see that benchmark used in all comparison outputs
**Plans**: TBD

### Phase 3: Structured Output Schema Layer
**Goal**: Pipeline outputs are validated against stable Pydantic schemas that Claude can reliably produce and consume as structured JSON
**Depends on**: Phase 2
**Requirements**: SOUT-01, SOUT-02, SOUT-03, SOUT-04
**Success Criteria** (what must be TRUE):
  1. Calling model_validate() on a pipeline output dict succeeds without manual type coercion by the user
  2. numpy float64 and pandas Series values in pipeline outputs are coerced cleanly rather than raising Pydantic validation errors
  3. Claude produces a structured JSON block during a Cowork session that passes schema validation
  4. CLAUDE.md workflow shows users exactly where to call validation and which schema to use at each pipeline step
**Plans**: TBD

### Phase 4: Qualitative Narrative Layer
**Goal**: Every analysis session produces plain-language macro interpretation and per-holding commentary that reflects the actual quantitative outputs
**Depends on**: Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, COWK-03
**Success Criteria** (what must be TRUE):
  1. The report includes a macro-regime narrative paragraph that cites the actual ERP value and P/E in its reasoning
  2. Any holding with a weight change greater than 5% receives a commentary note in the report
  3. When CAPM, Mean Historical, and EMA methods disagree materially, the report discloses the spread and labels it as lower confidence
  4. The report narrative includes a disclaimer that distinguishes educational analysis from investment advice
  5. README gives a new Cowork user step-by-step setup instructions (clone, link project, upload portfolio)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stability and Cowork Hardening | 0/TBD | Not started | - |
| 2. Input Expansion | 0/TBD | Not started | - |
| 3. Structured Output Schema Layer | 0/TBD | Not started | - |
| 4. Qualitative Narrative Layer | 0/TBD | Not started | - |
