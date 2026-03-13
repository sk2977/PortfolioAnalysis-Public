# Feature Landscape

**Domain:** LLM-orchestrated portfolio optimization toolkit (Claude Cowork, public GitHub)
**Researched:** 2026-03-13
**Confidence note:** Web search unavailable. Analysis grounded in: codebase audit (all 6 scripts), PROJECT.md, CONCERNS.md, ARCHITECTURE.md, INTEGRATIONS.md. Claims about user expectations are based on domain expertise; flagged LOW confidence where unverified against external sources.

---

## What Already Exists (Baseline)

The tool ships these capabilities today. Features below are evaluated against this baseline.

| Module | What It Does |
|--------|-------------|
| `parse_portfolio.py` | CSV parsing: generic, E-Trade, Schwab; ticker validation via yfinance |
| `market_data.py` | yfinance price download, 4-hour pickle cache, benchmark series |
| `macro_analysis.py` | ERP from FRED treasury + Multpl.com P/E scrape; interpretation string |
| `optimize.py` | pyportfolioopt: CAPM/Mean/EMA weighted, 3 risk presets, Ledoit-Wolf covariance |
| `visualize.py` | 5 matplotlib charts saved as PNG |
| `report.py` | Mechanical markdown report: performance table, allocation diff, top rebalancing actions |

The existing `report.py` produces structured data output (markdown tables) but zero qualitative narrative. Claude's role in the current CLAUDE.md workflow is orchestration and conversational framing -- not deep qualitative analysis.

---

## Table Stakes

Features users expect when they find this repo and try it. Missing any of these causes abandonment or a GitHub issue.

| Feature | Why Expected | Complexity | Status | Notes |
|---------|--------------|------------|--------|-------|
| Excel (.xlsx) upload | Fidelity, TD Ameritrade, and many brokers export .xlsx not CSV. Users will try to upload their file and fail. | Low | Missing (active scope) | openpyxl already available via pandas; parse_portfolio.py needs a thin wrapper |
| Readable rebalancing output (buy/sell list) | Users want "sell 50 shares of AAPL, buy 30 shares of VTI" -- not just weight deltas. The current diff table requires mental math. | Medium | Missing | Requires portfolio value as input; CONCERNS.md lists this explicitly as missing |
| LLM qualitative narrative | The whole premise is "AI-powered." A mechanical report with no prose commentary fails the stated value prop. | Medium | Missing (active scope) | Structured output schema needed so Claude writes consistent narrative |
| Input confirmation with edit loop | User uploads file, sees table, can correct mistakes before running (tickers to exclude, miscategorized rows). | Low | Partially exists | CLAUDE.md Phase 1 asks Claude to confirm, but no structured schema for the confirmation state |
| Clear failure messages for bad tickers | If a user's Schwab export has SWPPX (mutual fund), they need to know why it was dropped, not just silence. | Low | Partially exists | `[FAILED]` prefix exists but silent exception swallowing masks real errors |
| Working on current Python/pandas | Deprecated `reindex(..., method='ffill')` will error on pandas 2.x+ users. | Low | Bug (active scope) | One-line fix; high priority as pandas 2.x is default install |
| Benchmark flexibility | Hard-coded VTI is US equity only. Bonds-heavy portfolios or international users need AGG, SPY, or user-specified. | Low | Missing | CONCERNS.md flags this; one config param |

## Differentiators

Features that go beyond what a plain pyportfolioopt script does. These are the reasons a user forks or stars the repo.

| Feature | Value Proposition | Complexity | Status | Notes |
|---------|-------------------|------------|--------|-------|
| Structured output schema (Pydantic / JSON) | Claude produces consistent, parseable analysis objects -- not free-form text. Enables downstream use: save to JSON, pipe to another tool, display in a structured UI. Critical for reliability in Cowork sessions. | Medium | Missing (active scope) | Anthropic's tool_use / structured outputs pattern; Pydantic models for MacroContext, PortfolioRecommendation, RebalancingAction |
| Macro-regime narrative | Claude interprets ERP in plain language: "At 2.1% ERP, equities are richly valued vs bonds. In this environment, tilting toward low-volatility factors is historically defensive." Current `interpretation` field is a single mechanical string. | Medium | Partially exists | Current `interpretation` is hardcoded string from macro_analysis.py; needs LLM expansion |
| Per-holding qualitative commentary | For each material rebalancing action (increase/decrease >5%), Claude briefly explains the quant driver. "VTI increase: CAPM model assigns it the highest alpha given your current overweight in tech." | High | Missing | Requires LLM to reason over method_results dict per ticker |
| Sector/asset class concentration flags | "Your portfolio is 68% technology sector. Optimization may understate correlation risk during sector drawdowns." | Medium | Missing | Needs yfinance sector metadata or a static ticker-to-sector map |
| Multi-broker file merge | User has accounts at Schwab AND Fidelity. Accepts multiple files, deduplicates and aggregates. | Medium | Missing | parse_portfolio.py would need a merge pass; weight normalization already exists |
| User-specified include list | "I want NVDA in the optimization regardless of what the model says." Active scope, inverse of the existing exclude. | Low | Missing (active scope) | Forces a floor weight; pyportfolioopt supports this via weight_bounds |
| Confidence / uncertainty disclosure | Report states: "Expected return estimates span CAPM 12.4%, Mean 8.1%, EMA 10.2%. High disagreement between methods; treat recommendation with lower confidence." | Low | Missing | method_results dict already has per-method performance; just needs surfacing |
| Cache status reporting | "Using cached prices from 3 hours ago (within 4-hour TTL). Macro data refreshed 11 hours ago (stale, using cached P/E)." Users in Cowork have no visibility into data freshness without this. | Low | Missing | Cache TTL metadata exists in code but never shown to user |
| Fidelity CSV format support | Fidelity is a major broker with a distinct export format. Third most common after Schwab/E-Trade. | Low | Missing | Fidelity exports have header rows and "Account Name" meta-rows; similar to existing Schwab parser |

## Anti-Features

Things to explicitly not build. Inclusion would bloat the tool, create maintenance burden, or violate the project's design constraints.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Anthropic API key / direct API calls | Violates the core design: Claude IS the AI layer via Cowork. Adding API calls creates a credential management problem, breaks the public-repo safety model, and duplicates what Cowork already does for free. | Let Claude's structured output schema drive all qualitative narrative |
| Web UI or dashboard | Scope creep. Users of this tool are running it in Cowork -- they have a conversational interface already. A Flask/Streamlit UI requires hosting, auth, maintenance, and conflicts with the "clone and run" distribution model. | Invest in richer markdown output and cleaner Cowork interaction |
| Real-time / streaming prices | yfinance is daily close data. Building a real-time feed requires paid APIs (Polygon, Alpaca), adds rate-limit complexity, and shifts the tool from "analysis" to "trading." | Keep daily close; note staleness clearly in output |
| Tax-lot tracking and tax-loss harvesting | User-specific (account type, state taxes, acquisition dates). Requires data the tool cannot obtain from a CSV export. Cannot be done correctly without brokerage API access. | Disclaim in report: "Tax implications not modeled" |
| Automated trade execution | Brokerage API integration is account-specific, requires OAuth, creates regulatory risk for a public educational tool. | Output a rebalancing action list for the user to execute manually |
| Backtesting / strategy simulator | Backtesting requires historical rebalancing simulation, transaction cost modeling, and survivorship bias handling. This is a separate problem domain from current-portfolio optimization. | Stick to mean-variance optimization on current holdings |
| Complex CLI entry point | Adding argparse-based CLI creates a separate interface contract to maintain. The Cowork workflow (CLAUDE.md) is the interface. | Keep module-level `if __name__ == '__main__'` for dev testing only |
| Custom factor models (Fama-French, etc.) | Adds significant math complexity, requires data sources (Ken French library), and produces results that need expert interpretation. Misuse risk is high for public audience. | Three-method return averaging (CAPM/Mean/EMA) is already a defensible ensemble |

---

## Feature Dependencies

```
Excel upload support
    -> requires parse_portfolio.py xlsx wrapper
    -> openpyxl already in pandas ecosystem (no new deps)

Rebalancing buy/sell list
    -> requires portfolio dollar value as input (Phase 1 data collection)
    -> requires comparison DataFrame (already exists in results dict)
    -> LLM narrative can generate the list from structured outputs

Structured output schema (Pydantic)
    -> required BEFORE per-holding commentary (LLM needs schema to populate)
    -> required BEFORE macro-regime narrative (consistent field names)
    -> enables all downstream LLM features

Per-holding qualitative commentary
    -> requires structured outputs schema (see above)
    -> requires method_results dict (already exists)
    -> requires sector metadata (new data dependency)

Sector concentration flags
    -> requires ticker-to-sector map
    -> yfinance Ticker.info has sector field but slow (per-ticker API call)
    -> can be built with cached static map for common tickers + live fallback

Confidence / uncertainty disclosure
    -> requires method_results dict (already exists)
    -> zero new data dependencies; logic only

User-specified include list
    -> requires weight_bounds modification in optimize.py
    -> independent of other features

Fidelity CSV support
    -> independent of other features; extends parse_portfolio.py only

Cache status reporting
    -> cache metadata already computed in market_data.py and macro_analysis.py
    -> requires surfacing timestamps to user; no new data dependencies
```

---

## MVP Recommendation for Next Milestone

The active scope in PROJECT.md targets four things. Priority order based on user impact and dependency structure:

1. **Fix deprecated pandas API** (bug, zero new scope, unblocks reliable execution on modern installs)
2. **Excel (.xlsx) upload** (table stakes, low complexity, unblocks users who only have .xlsx exports)
3. **Structured output schema** (differentiator and dependency blocker -- all LLM narrative features depend on this)
4. **LLM qualitative narrative layer** (core value prop, requires #3 to be reliable)
5. **User-specified include list** (active scope, low complexity, independent -- can be parallelized with any of the above)

Defer to a later milestone:
- Rebalancing buy/sell list (requires collecting portfolio dollar value -- changes Phase 1 interaction model)
- Sector concentration flags (new data dependency; yfinance per-ticker slowness compounds download time)
- Fidelity CSV support (nice to have; current three formats cover majority of US retail brokers)
- Multi-broker file merge (useful but niche; adds input complexity)

---

## Confidence Assessment

| Claim | Confidence | Basis |
|-------|------------|-------|
| Excel is table stakes | MEDIUM | Domain expertise; common broker export format; unverified against actual user complaints |
| Rebalancing buy/sell list is expected | MEDIUM | CONCERNS.md explicitly lists it as missing capability |
| Structured outputs pattern for Anthropic | MEDIUM | Known Anthropic feature as of training cutoff (Aug 2025); specific API shape may have changed |
| Fidelity is third most common broker | LOW | Domain expertise only; no source verified |
| yfinance Ticker.info has sector field | MEDIUM | Known behavior as of training cutoff; yfinance API is unstable and changes frequently |

---

## Sources

- Codebase audit: all files in `scripts/`, `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/INTEGRATIONS.md`
- Domain knowledge: Mean-variance optimization conventions, retail broker export formats, LLM-tool integration patterns
- Note: Web search was unavailable during this research session. Claims about competitor tools and community expectations are based on training data (cutoff Aug 2025) and are flagged accordingly.
