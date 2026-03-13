# Structure

## Directory Layout

```
PortfolioAnalysis-Public/
|-- scripts/                    # All Python modules (6 files + __init__.py)
|   |-- __init__.py             # Package docstring, no imports
|   |-- parse_portfolio.py      # CSV parsing + ticker validation
|   |-- market_data.py          # yfinance downloads + pickle cache
|   |-- macro_analysis.py       # ERP calculator (FRED + Multpl.com)
|   |-- optimize.py             # Portfolio optimization (pyportfolioopt)
|   |-- visualize.py            # Matplotlib chart generation
|   |-- report.py               # Markdown report assembly
|
|-- data_cache/                 # [gitignored] Pickle cache files
|-- output/                     # [gitignored] Generated charts (PNG) + reports (MD)
|
|-- sample_portfolio.csv        # Test portfolio for development
|-- requirements.txt            # 11 Python dependencies
|-- CLAUDE.md                   # AI orchestration workflow instructions
|-- README.md                   # Project overview
|-- LICENSE                     # License file
|-- prompt.md                   # Additional prompt context
|-- .gitignore                  # Git ignore rules
```

## Key Locations

| What | Where |
|------|-------|
| All application code | `scripts/` (flat, no subdirectories) |
| Risk tolerance presets | `scripts/optimize.py` lines 17-39 (`RISK_PRESETS` dict) |
| CSV format detection | `scripts/parse_portfolio.py` `_detect_format()` |
| Cache TTL config | `scripts/market_data.py` lines 20-21, `scripts/macro_analysis.py` lines 28-29 |
| Chart color palette | `scripts/visualize.py` lines 27-33 (`COLORS` dict) |
| Workflow definition | `CLAUDE.md` (7 phases) |
| ERP data source URLs | `scripts/macro_analysis.py` line 31 (`MULTPL_PE_URL`) |

## Naming Conventions

- **Files**: `snake_case.py` -- all modules are single-purpose
- **Functions**: `snake_case` -- public functions have docstrings with Parameters/Returns
- **Private functions**: Prefixed with `_` (e.g., `_detect_format`, `_load_cache`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CACHE_DIR`, `RISK_PRESETS`)
- **Output files**: `snake_case.png` for charts, `report.md` for reports

## File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| `parse_portfolio.py` | 333 | Largest -- multi-format CSV parsing |
| `macro_analysis.py` | 371 | ERP calculation + caching + web scraping |
| `visualize.py` | 310 | 5 chart generation functions |
| `optimize.py` | 278 | Optimization pipeline + 3 methods |
| `market_data.py` | 182 | Price downloads + cache management |
| `report.py` | 175 | Markdown report assembly |
| `__init__.py` | 12 | Package docstring only |

## Adding New Code

- New analysis modules go in `scripts/` as flat files
- Follow the dict-based contract pattern (return dicts with documented keys)
- Add corresponding visualization function in `visualize.py`
- Update `CLAUDE.md` workflow if adding a new phase
- Use `[OK]`/`[ERROR]`/`[WARN]` console prefixes, no Unicode
- Use `encoding='utf-8'` for all file I/O
