# Architecture

## Pattern

**Sequential Pipeline** -- Linear 7-phase workflow orchestrated by Claude (the AI layer), calling stateless Python modules in sequence.

No web framework, no server, no CLI entry point. Claude acts as the controller, calling functions from `scripts/` and presenting results conversationally.

## Layers

```
[User] <-> [Claude AI (orchestrator)]
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

### Layer Details

| Layer | Module(s) | Responsibility |
|-------|-----------|---------------|
| Input | `scripts/parse_portfolio.py` | CSV parsing (generic, E-Trade, Schwab), ticker validation via yfinance |
| Data | `scripts/market_data.py` | Historical price download via yfinance, pickle caching (4hr TTL) |
| Macro | `scripts/macro_analysis.py` | ERP calculation from FRED treasury yields + Multpl.com P/E scraping |
| Optimization | `scripts/optimize.py` | Portfolio optimization via pyportfolioopt (CAPM/Mean/EMA weighted) |
| Visualization | `scripts/visualize.py` | Matplotlib chart generation (5 chart types), saved as PNG |
| Report | `scripts/report.py` | Markdown report assembly from all results |

## Data Flow

```
CSV/Text Input
    -> parse_csv() -> portfolio dict {tickers, allocations, raw_data, format_detected}
    -> download_prices(tickers) -> market dict {prices, benchmark, failed, coverage}
    -> get_macro_context() -> macro dict {pe_ratio, earnings_yield, treasury_yield, erp, ...}
    -> optimize_portfolio(prices, benchmark, allocations, config) -> results dict {optimal_allocations, comparison, performance, ...}
    -> plot_*() functions -> list of PNG paths
    -> generate_report() -> markdown string + saved report.md
```

## Data Contracts

All inter-module communication uses **plain dicts** with documented keys. Key contracts:

- **portfolio dict**: `tickers` (list), `allocations` (pd.Series), `raw_data` (DataFrame), `format_detected` (str)
- **market dict**: `prices` (DataFrame), `benchmark` (Series), `failed` (list), `coverage` (dict)
- **macro dict**: `pe_ratio`, `earnings_yield`, `treasury_yield`, `erp` (all float/None), `interpretation` (str), `stats` (dict), `erp_history` (DataFrame)
- **results dict**: `optimal_allocations` (Series), `comparison` (DataFrame), `performance` (dict of dicts), `method_results` (dict), `cov_matrix` (DataFrame), `config` (dict)

## Entry Points

No standalone entry point. Each module has `if __name__ == '__main__':` blocks for testing:
- `parse_portfolio.py`: Parse a CSV file from command line arg
- `market_data.py`: Quick test downloading AAPL, MSFT, VTI
- `macro_analysis.py`: Fetch and print current macro context
- `optimize.py`: Print risk preset configs

The primary entry point is **Claude following `CLAUDE.md` workflow** phases 1-7.

## Caching Strategy

Pickle-based caching in `data_cache/` with TTL-based invalidation:
- Price data: 4-hour TTL, key = sorted tickers + start date
- Treasury yield (FRED): 4-hour TTL
- S&P 500 P/E (Multpl.com): 12-hour TTL
- P/E history: Append-only, no TTL (grows indefinitely)

Fallback pattern: if fresh fetch fails, load stale cache (treasury yields only).

## Error Handling

- **Graceful degradation**: Failed ticker downloads are reported but don't halt the pipeline
- **Fallback chain**: Web scrape failure -> stale cache -> P/E history -> None
- **Optimization fallback**: If selected method fails, falls back to max_sharpe
- **User reporting**: All errors printed with `[ERROR]`, `[WARN]`, `[FAILED]` prefixes (no Unicode)
