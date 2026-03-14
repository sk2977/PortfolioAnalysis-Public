# PortfolioAnalysis

## What This Is

A public portfolio optimization and US macro analysis toolkit for Claude Cowork. Users clone the repo, link it in Cowork, upload their portfolio (CSV or Excel), and receive quantitative optimization recommendations paired with AI-generated market commentary and per-holding rebalancing notes.

## Core Value

Users get actionable, data-driven portfolio rebalancing recommendations that combine quantitative optimization (pyportfolioopt) with LLM-generated qualitative analysis -- all within Claude Cowork without leaving the conversation.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] CSV portfolio parsing (generic, E-Trade, Schwab formats) -- existing
- [x] Portfolio optimization via pyportfolioopt (CAPM, Mean Historical, EMA weighted) -- existing
- [x] Three risk tolerance presets (conservative, moderate, aggressive) -- existing
- [x] User can exclude tickers and set max holding weight -- existing
- [x] Historical price data download via yfinance with pickle caching -- existing
- [x] US macro analysis: Equity Risk Premium from FRED treasury yields + S&P 500 P/E -- existing
- [x] Matplotlib chart generation (allocation comparison, efficient frontier, correlation, ERP dashboard, price history) -- existing
- [x] Markdown report generation with performance comparison -- existing
- [x] Ledoit-Wolf covariance shrinkage for robustness -- existing
- [x] STAB-01/02/03: Deprecated pandas API fixed, silent exceptions replaced with warnings, matplotlib Agg backend -- v1.0
- [x] COWK-01/02: Preflight import checks, requirements.txt updated -- v1.0
- [x] INPT-01: Excel (.xlsx) file upload with auto-format detection -- v1.0
- [x] INPT-02: Forced-include tickers with configurable weight floor -- v1.0
- [x] INPT-03: Custom benchmark selection -- v1.0
- [x] SOUT-01/02: Pydantic v2 schemas with numpy/pandas type coercion -- v1.0
- [x] SOUT-03/04: JSON schema generation for structured output, CLAUDE.md workflow -- v1.0
- [x] QUAL-01/02/03/04: Macro narrative, per-holding commentary, method spread disclosure, integrated report -- v1.0
- [x] COWK-03: README with Cowork setup instructions -- v1.0

### Active

<!-- Current scope. Building toward these. -->

- [ ] Rebalancing buy/sell list with share counts (requires portfolio dollar value input)
- [ ] Sector/asset class concentration flags with warnings
- [ ] Cache status reporting (data freshness visibility)
- [ ] Fidelity CSV format support
- [ ] Multi-broker file merge (aggregate across accounts)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Anthropic API key / direct API calls -- Claude IS the AI layer (runs in Cowork)
- Web UI or standalone app -- this is a Cowork-native tool
- Real-time trading or brokerage integration -- educational/informational only
- Tax-lot awareness or tax-loss harvesting -- too user-specific for public tool
- Mobile app -- Cowork desktop only
- Backtesting / strategy simulator -- separate problem domain
- Custom factor models (Fama-French) -- expert interpretation required, misuse risk

## Context

- **Current state**: v1.0 shipped (2026-03-13), 3,075 Python LOC, 36 automated tests
- **Tech stack**: Python 3.x, pandas, pyportfolioopt, yfinance, pydantic v2, matplotlib
- **Distribution**: Public GitHub repo, users clone and link in Claude Cowork
- **Execution environment**: Claude Cowork runs Python scripts directly
- **Codebase map**: `.planning/codebase/` contains architecture, stack, conventions, and concerns
- **Known tech debt**: Brittle Multpl.com web scraping, pickle caching security concerns

## Constraints

- **Encoding**: Windows cp1252 safe -- no Unicode emojis, Greek letters, or math symbols in console output
- **File I/O**: All reads/writes use `encoding='utf-8'`
- **Dependencies**: Minimal -- users install via `requirements.txt`, no complex build steps
- **Public repo**: No secrets, API keys, or credentials in code
- **Cowork execution**: Scripts must work within Cowork's Python sandbox capabilities

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Functional architecture (no classes) | Simplicity for single-purpose tool | Good -- keeps codebase accessible |
| Three expected return methods weighted equally | Reduces single-method bias | Good -- method spread disclosure added in v1.0 |
| Pickle caching with TTL | Fast re-runs without re-downloading | Good -- revisit security in v2 |
| Pydantic v2 schemas (wrap, don't rewrite) | Pipeline functions keep returning plain dicts | Good -- backward compat preserved |
| Duck-typed coercion (hasattr) over numpy imports | Keeps schemas.py dependency-light | Good -- clean separation |
| Claude generates narrative, report.py assembles | No LLM library needed, Claude IS the AI layer | Good -- zero new dependencies |

---
*Last updated: 2026-03-14 after v1.0 milestone*
