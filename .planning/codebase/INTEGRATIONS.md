# External Integrations

**Analysis Date:** 2026-03-13

## APIs & External Services

**Market Data:**
- Yahoo Finance (yfinance) - Historical price data for any equity ticker
  - SDK/Client: yfinance 0.2.32+
  - Auth: None (public API)
  - Usage: `yf.download(ticker, start=start_date, auto_adjust=True, progress=False)`
  - Data: Daily OHLC prices, splits/dividends auto-adjusted
  - File: `scripts/market_data.py` (download_prices function)

**Macroeconomic Data:**
- Federal Reserve Economic Data (FRED) - 10-Year Treasury Yield (DGS10)
  - SDK/Client: pandas-datareader 0.10.0+
  - Auth: None (public API)
  - Usage: `pdr.get_data_fred('DGS10', start=start_date)`
  - Data: Daily Treasury yields from 2000-present
  - File: `scripts/macro_analysis.py` (fetch_treasury_yield function)

**Market Valuation Data:**
- Multpl.com - S&P 500 Trailing P/E Ratio
  - Method: Web scrape via requests + BeautifulSoup
  - Auth: None (public website, User-Agent header required)
  - URL: https://www.multpl.com/s-p-500-pe-ratio
  - HTML target: `div[id="current"]` for latest P/E value
  - File: `scripts/macro_analysis.py` (fetch_sp500_pe function)
  - Retry logic: 3 attempts with exponential backoff (2^n seconds)

## Data Storage

**Databases:**
- None - No persistent database

**Local Caching:**
- Pickle-based file cache in `data_cache/` directory
  - Cache TTL configurable per data type (4-12 hours)
  - Fallback behavior: Loads stale cache if live fetch fails
  - Files: `treasury_DGS10.pkl`, `multpl_pe.pkl`, `sp500_pe_history.pkl`, `prices_<ticker_hash>_<date>.pkl`

**File Storage:**
- Local filesystem only
- Output directory: `output/` (gitignored)
  - Chart PNGs: allocation_comparison.png, efficient_frontiers.png, correlation_matrix.png, erp_dashboard.png, price_history.png
  - Report: report.md

**Caching:**
- Cache directory: `data_cache/` (gitignored)
- No external caching service (Redis, memcached, etc.)

## Authentication & Identity

**Auth Provider:**
- None - All external APIs are public and require no authentication
- No API keys, OAuth tokens, or credentials needed
- Multpl.com scrape includes User-Agent header to avoid blocking

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service

**Logs:**
- Console output only (print statements)
- Status codes: `[OK]`, `[WARN]`, `[ERROR]`, `[FAILED]`, `[RETRY]`, `[FALLBACK]`
- No file-based logging
- Detailed error messages in try/except blocks with fallback strategies

**Fallback Strategies:**
- FRED fetch failure: Load stale Treasury cache
- Multpl.com scrape failure: Use cached P/E ratio from history
- yfinance download failure: Skip ticker and continue with others
- Missing benchmark: Raise error and ask user to retry

## CI/CD & Deployment

**Hosting:**
- No hosted service - Runs locally as Claude-orchestrated Python scripts
- Designed for Claude Desktop Cowork mode or Claude Code interactive environment

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- None required for basic operation
- All integrations use public APIs

**Optional env vars:**
- .env file support via python-dotenv (if custom configuration needed)
- File location: Project root `.env`
- Never committed (in .gitignore)

**Secrets location:**
- No secrets in codebase - All APIs are public
- .env file would store any future API keys (e.g., proprietary data sources)

## Webhooks & Callbacks

**Incoming:**
- None - No webhook endpoints

**Outgoing:**
- None - No callbacks or push notifications

## Data Flow Architecture

**Input:**
1. User provides portfolio CSV (E-Trade, Schwab, or generic format) or text description
2. `parse_portfolio.py` validates tickers via yfinance

**Processing:**
1. `market_data.py` downloads historical prices from yfinance (cached locally)
2. `macro_analysis.py` fetches:
   - Treasury yield from FRED (cached 4 hours)
   - S&P 500 P/E from Multpl.com web scrape (cached 12 hours)
3. `optimize.py` calculates:
   - Covariance matrix (Ledoit-Wolf shrinkage on prices)
   - Expected returns (3 methods: CAPM, Mean Historical, EMA weighted 34/33/33)
   - Optimal allocation via pyportfolioopt EfficientFrontier solver

**Output:**
1. `visualize.py` generates 5 PNG charts using matplotlib
2. `report.py` generates markdown report with embedded chart paths

## Error Handling & Resilience

**yfinance downloader:**
- Sequential downloads with 3-second delay between tickers to avoid rate limiting
- Partial failures: Continues with successful tickers, reports failed ones
- All downloads fail: Raises ValueError to stop processing
- Cache hit: Skips download, returns cached data immediately

**FRED Treasury fetch:**
- Primary: Live fetch via pdr.get_data_fred()
- Fallback: Loads stale cache (no TTL check) if live fetch fails
- Empty data: Raises error (cannot proceed without rates)

**Multpl.com P/E fetch:**
- Up to 3 retry attempts with exponential backoff
- Sanity check: Rejects P/E outside 5-100 range
- Parse error: Tries next attempt if regex match fails
- Final fallback: Uses cached P/E history if available
- Complete failure: Returns None, optimization handles gracefully

**Portfolio parsing:**
- Filters out: Options, cash, null values, symbols >10 chars
- Invalid CSV: Raises error with guidance on expected columns
- Empty result: Raises error (no valid tickers found)

---

*Integration audit: 2026-03-13*
