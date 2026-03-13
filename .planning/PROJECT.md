# PortfolioAnalysis

## What This Is

A public portfolio optimization and US macro analysis toolkit designed to run inside Claude Cowork (Claude Desktop). Users download the repo from GitHub, link it in Cowork, upload their stock portfolio as CSV or Excel, and receive AI-powered optimization recommendations paired with qualitative market commentary.

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

### Active

<!-- Current scope. Building toward these. -->

- [ ] Excel (.xlsx) file upload support alongside CSV
- [ ] Structured outputs using Anthropic structured output schemas (Pydantic models / JSON schemas)
- [ ] Claude Cowork compatibility -- ensure all scripts execute within Cowork's Python environment
- [ ] LLM qualitative narrative layer -- Claude provides market interpretation and actionable commentary beyond mechanical report output
- [ ] User can specify stocks to include (not just exclude)
- [ ] Fix deprecated pandas `reindex(..., method='ffill')` API usage

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Anthropic API key / direct API calls -- Claude IS the AI layer (runs in Cowork)
- Web UI or standalone app -- this is a Cowork-native tool
- Real-time trading or brokerage integration -- educational/informational only
- Tax-lot awareness or tax-loss harvesting -- too user-specific for public tool
- Mobile app -- Cowork desktop only

## Context

- **Brownfield project**: 6 Python modules in `scripts/`, functional end-to-end pipeline
- **Distribution model**: Public GitHub repo, users clone and link in Claude Cowork
- **Execution environment**: Claude Cowork runs Python scripts directly
- **Codebase map**: `.planning/codebase/` contains full architecture, stack, conventions, and concerns documentation
- **Key dependency**: pyportfolioopt (https://github.com/PyPortfolio/PyPortfolioOpt) for optimization math
- **Known tech debt**: Silent exception handling, brittle Multpl.com web scraping, pickle caching security, no test suite (see `.planning/codebase/CONCERNS.md`)

## Constraints

- **Encoding**: Windows cp1252 safe -- no Unicode emojis, Greek letters, or math symbols in console output
- **File I/O**: All reads/writes use `encoding='utf-8'`
- **Dependencies**: Minimal -- users install via `requirements.txt`, no complex build steps
- **Public repo**: No secrets, API keys, or credentials in code
- **Cowork execution**: Scripts must work within Cowork's Python sandbox capabilities

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Functional architecture (no classes) | Simplicity for single-purpose tool | -- Pending |
| Three expected return methods weighted equally | Reduces single-method bias | -- Pending |
| Pickle caching with TTL | Fast re-runs without re-downloading | -- Pending |
| Structured outputs via Anthropic format | Cowork-native, reliable parsing | -- Pending |

---
*Last updated: 2026-03-13 after initialization*
