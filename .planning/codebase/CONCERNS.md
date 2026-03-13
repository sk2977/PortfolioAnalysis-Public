# Concerns

## Tech Debt

### Silent Exception Swallowing
- `scripts/macro_analysis.py` lines 312-313, 349-350: Cache save/load uses `except Exception: pass`
- `scripts/market_data.py` lines 163-165: Cache load silently returns None on any error
- **Risk**: Masks real bugs (disk full, permission errors, corrupt data)

### Brittle Web Scraping
- `scripts/macro_analysis.py` lines 154-222: Scrapes `https://www.multpl.com/s-p-500-pe-ratio`
- Relies on specific HTML structure (`div#current`, regex `:\s*([\d.]+)`)
- **Risk**: Any Multpl.com redesign breaks P/E fetching entirely

### Pickle Caching
- All cache files use `pickle.load()` which is insecure if cache files are tampered with
- Pickle is Python-version sensitive -- cache files not portable across Python versions
- No cache size limits -- `data_cache/` grows indefinitely

### Unused Dependency
- `python-dotenv` in `requirements.txt` but never imported or used in any module

## Known Bugs

### Deprecated pandas API
- `scripts/macro_analysis.py` line 242: `pe_df['pe_ratio'].reindex(treasury_aligned.index, method='ffill')`
- `method` parameter in `reindex()` deprecated in pandas 2.x, will be removed in future version
- **Fix**: Use `.reindex(...).ffill()` instead

### Hardcoded Benchmark
- `scripts/market_data.py` line 24: Default benchmark is `'VTI'`
- No validation or fallback if VTI is delisted or unavailable
- CLAUDE.md workflow also hardcodes VTI as benchmark

### Division by Zero Edge Case
- `scripts/optimize.py` line 264: `sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0`
- Returns 0 for zero-volatility portfolio, which may misrepresent risk-free assets

## Security Concerns

### No Input Sanitization
- Ticker symbols from CSV files are used directly in yfinance API calls and report output
- No validation against injection patterns (relevant if report markdown is rendered in web context)

### Static User-Agent
- `scripts/macro_analysis.py` lines 180-183: Hardcoded Chrome user-agent for Multpl.com scraping
- May be blocked if site implements bot detection

## Performance Bottlenecks

### Sequential Downloads with Mandatory Delay
- `scripts/market_data.py` lines 70-92: Downloads tickers one at a time with 3-second delay
- 20-ticker portfolio takes ~60 seconds minimum
- yfinance supports batch downloads (`yf.download(tickers_list)`) but not used

### No Covariance Caching
- `scripts/optimize.py` line 105: Covariance matrix recalculated on every run
- For same price data, Ledoit-Wolf shrinkage result is deterministic

## Fragile Areas

### CSV Format Detection
- `scripts/parse_portfolio.py` lines 56-77: Format detection is heuristic-based
- E-Trade detection checks first 15 lines for "e*trade" string -- may false-positive/negative
- Schwab detection relies on "description" + "market value" columns
- E-Trade parser hardcodes `skiprows=10` and `columns[4]` for allocation

### Optimization Fallback
- `scripts/optimize.py` lines 218-235: If selected method fails, falls back to max_sharpe
- Fallback creates a new EfficientFrontier but if that also fails, exception propagates unhandled

## Scaling Limits

- **Portfolio size**: No upper bound validation. >100 tickers would cause very slow downloads and large correlation matrices
- **Cache accumulation**: No cleanup mechanism for old pickle files in `data_cache/`
- **P/E history**: Append-only list in pickle, grows one entry per run indefinitely
- **Memory**: Full price DataFrame held in memory (fine for <100 tickers, problematic for hundreds)

## Missing Capabilities

- No automated test suite
- No rebalancing transaction list (buy/sell X shares)
- No tax-lot awareness or tax-loss harvesting
- No multi-period or rolling-window analysis
- No custom constraint support beyond max weight
- No sector/asset-class exposure analysis
- No drawdown or tail risk metrics
