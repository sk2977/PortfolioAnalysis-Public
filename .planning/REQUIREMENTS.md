# Requirements: PortfolioAnalysis

**Defined:** 2026-03-13
**Core Value:** Users get actionable portfolio rebalancing recommendations combining quantitative optimization with LLM qualitative analysis -- all within Claude Cowork.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Stability

- [x] **STAB-01**: Deprecated pandas `reindex(..., method='ffill')` replaced with `.reindex(...).ffill()` across all modules
- [x] **STAB-02**: Silent `except Exception: pass` in cache operations replaced with logged warnings
- [x] **STAB-03**: matplotlib Agg backend explicitly set before any pyplot imports for headless Cowork execution

### Input

- [ ] **INPT-01**: User can upload Excel (.xlsx) files from any supported broker format
- [x] **INPT-02**: User can specify tickers to include in optimization (forced floor weight via pyportfolioopt weight_bounds)
- [x] **INPT-03**: User can choose a custom benchmark ticker (not hardcoded to VTI)

### Structured Outputs

- [ ] **SOUT-01**: Pydantic v2 schema defined for portfolio analysis results (MacroContext, PortfolioRecommendation, AllocationComparison)
- [ ] **SOUT-02**: Pipeline output dicts validated against Pydantic schemas with numpy/pandas type normalization
- [ ] **SOUT-03**: Claude produces structured JSON output block conforming to schema during Cowork sessions
- [ ] **SOUT-04**: CLAUDE.md workflow updated with structured output instructions and schema references

### Qualitative Analysis

- [ ] **QUAL-01**: Claude generates macro-regime narrative interpreting ERP, treasury yields, and P/E in plain language
- [ ] **QUAL-02**: Claude generates per-holding commentary for material rebalancing actions (>5% weight change)
- [ ] **QUAL-03**: Claude discloses method disagreement (CAPM vs Mean vs EMA spread) as confidence indicator
- [ ] **QUAL-04**: Qualitative sections integrated into report output alongside mechanical tables

### Cowork Compatibility

- [x] **COWK-01**: All scripts execute successfully in Claude Cowork Python environment
- [x] **COWK-02**: Requirements.txt updated: +openpyxl, +pydantic; -python-dotenv
- [ ] **COWK-03**: README updated with Cowork setup instructions (clone, link, upload portfolio)

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Enhanced Output

- **EOUT-01**: Rebalancing buy/sell list with share counts (requires portfolio dollar value input)
- **EOUT-02**: Sector/asset class concentration flags with warnings
- **EOUT-03**: Cache status reporting (data freshness visibility)

### Expanded Input

- **XINP-01**: Fidelity CSV format support
- **XINP-02**: Multi-broker file merge (aggregate across accounts)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Anthropic API key / direct API calls | Claude IS the AI layer via Cowork; no credentials needed |
| Web UI or dashboard | Cowork is the interface; Flask/Streamlit adds maintenance burden |
| Real-time / streaming prices | Daily close is sufficient; real-time requires paid APIs |
| Tax-lot tracking / tax-loss harvesting | User-specific, requires data not available from CSV exports |
| Automated trade execution | Regulatory risk, requires brokerage OAuth |
| Backtesting / strategy simulator | Separate problem domain from current-portfolio optimization |
| Custom factor models (Fama-French) | Expert interpretation required; misuse risk for public audience |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STAB-01 | Phase 1 | Complete |
| STAB-02 | Phase 1 | Complete |
| STAB-03 | Phase 1 | Complete |
| COWK-01 | Phase 1 | Complete |
| COWK-02 | Phase 1 | Complete |
| INPT-01 | Phase 2 | Pending |
| INPT-02 | Phase 2 | Complete |
| INPT-03 | Phase 2 | Complete |
| SOUT-01 | Phase 3 | Pending |
| SOUT-02 | Phase 3 | Pending |
| SOUT-03 | Phase 3 | Pending |
| SOUT-04 | Phase 3 | Pending |
| QUAL-01 | Phase 4 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 4 | Pending |
| QUAL-04 | Phase 4 | Pending |
| COWK-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after roadmap creation*
