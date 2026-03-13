# Testing

## Current State

**No test suite exists.** No test files, no test framework configured, no CI/CD pipeline.

## Test Infrastructure

- No `tests/` directory
- No `pytest`, `unittest`, or other test framework in `requirements.txt`
- No `pyproject.toml`, `setup.cfg`, or test configuration
- No CI/CD (no GitHub Actions, no `.github/` directory)

## Manual Testing

Each module has `if __name__ == '__main__':` blocks for ad-hoc testing:
- `parse_portfolio.py`: Accepts CSV path as CLI arg, prints parsed holdings
- `market_data.py`: Downloads AAPL, MSFT, VTI and prints shape
- `macro_analysis.py`: Fetches and prints current ERP
- `optimize.py`: Prints risk preset configurations

`sample_portfolio.csv` serves as the test fixture for manual runs.

## Testing Priorities (if adding tests)

1. **CRITICAL**: CSV parsing -- multiple formats, edge cases (missing columns, bad data, options filtering)
2. **CRITICAL**: Web scraping -- Multpl.com HTML parser is brittle and will break when site changes
3. **HIGH**: Market data download -- yfinance API changes, empty responses, rate limiting
4. **HIGH**: Optimization edge cases -- single ticker, identical returns, zero volatility
5. **MEDIUM**: Cache TTL logic -- expiry, stale fallback, corrupt pickle files
6. **MEDIUM**: Report generation -- missing data fields, empty comparison DataFrames
7. **LOW**: Visualization -- chart generation doesn't crash (visual correctness hard to test)

## Mocking Needs

If tests are added, these external calls need mocking:
- `yfinance.download()` and `yfinance.Ticker().fast_info` -- network calls
- `pandas_datareader.get_data_fred()` -- FRED API
- `requests.get()` for Multpl.com -- web scraping
- File system operations for cache read/write
