# Technology Stack

**Analysis Date:** 2026-03-13

## Languages

**Primary:**
- Python 3.10+ - Core application logic, financial analysis, data processing

## Runtime

**Environment:**
- Python with venv (virtual environment per project)
- Cross-platform: Windows 11, Mac/Linux compatible

**Package Manager:**
- pip (requirements.txt lockfile present)
- Lockfile: `requirements.txt` with pinned versions

## Frameworks & Core Libraries

**Data & Analysis:**
- pandas 2.0.0+ - DataFrame operations, CSV parsing, financial data manipulation
- numpy 1.24.0+ - Numerical computations, matrix operations, covariance calculations
- scikit-learn 1.2.0+ - Covariance shrinkage (Ledoit-Wolf), statistical operations

**Portfolio Optimization:**
- pyportfolioopt 1.5.0+ - Efficient frontier construction, Sharpe ratio maximization, volatility minimization
- EfficientFrontier class for constraint-based optimization
- L2 regularization via objective_functions.L2_reg

**Visualization:**
- matplotlib 3.7.0+ - Chart generation, rendered to PNG files
- seaborn 0.12.0+ - Heatmap styling, correlation visualizations
- pypfopt.plotting - Efficient frontier visualization helpers

**Market Data:**
- yfinance 0.2.32+ - Historical price downloads from Yahoo Finance
- pandas-datareader 0.10.0+ - FRED API integration for Treasury yields (DGS10)

**Web Scraping:**
- requests 2.31.0+ - HTTP requests to Multpl.com for S&P 500 P/E ratio
- beautifulsoup4 4.12.0+ - HTML parsing for P/E data extraction

**Environment & Configuration:**
- python-dotenv 1.0.0+ - Load environment variables from .env files

## Key Dependencies

**Critical:**
- pyportfolioopt 1.5.0 - Portfolio optimization engine. Provides Efficient Frontier solver with Sharpe ratio, min volatility, and quadratic utility methods. Without this, optimization cannot run.
- pandas 2.0.0 - Data manipulation backbone. Handles all tabular data operations, CSV parsing, and Series operations. Foundation for all numerical work.
- yfinance 0.2.32 - Market data source. Downloads historical price data from Yahoo Finance. Only source for historical OHLC data.

**Infrastructure:**
- numpy 1.24.0 - Matrix operations for covariance, portfolio performance calculations
- scikit-learn 1.2.0 - Ledoit-Wolf covariance shrinkage. Improves covariance matrix robustness with small sample sizes
- matplotlib 3.7.0 - Chart rendering engine. Generates all PNG visualizations

## Configuration

**Environment:**
- Configuration via risk tolerance presets: conservative, moderate, aggressive
- Presets define:
  - max_weight (0.10, 0.15, 0.25 per holding)
  - optimization_method ('min_volatility' or 'max_sharpe')
  - gamma (L2 regularization parameter: 0.10, 0.05, 0.02)
  - risk_free_rate (default 0.04 / 4%)
  - method_weights (34% CAPM, 33% Mean, 33% EMA)

**Build/Development:**
- No build system needed - pure Python scripts
- No tsconfig, eslint, or formatter configs
- Entry points are individual Python scripts in `scripts/` directory

**Caching:**
- Pickle-based local cache in `data_cache/` directory (gitignored)
- FRED Treasury data: 4-hour TTL
- S&P 500 P/E data: 12-hour TTL
- Historical prices: 4-hour TTL per ticker set
- Cache files: `treasury_DGS10.pkl`, `multpl_pe.pkl`, `sp500_pe_history.pkl`, `prices_*.pkl`

## Platform Requirements

**Development:**
- Python 3.10 or higher
- Virtual environment (venv)
- Windows 11 or Mac/Linux with bash

**Runtime Dependencies:**
- Yahoo Finance API (yfinance downloads)
- FRED API (via pandas-datareader)
- Multpl.com web scrape (S&P 500 P/E source)
- No authentication required for any external service

**Deployment:**
- CLI-based Python scripts
- Designed for Claude AI orchestration (Claude Desktop Cowork mode or Claude Code)
- Outputs to `output/` directory (gitignored)

## Output Artifacts

**Generated Files:**
- Chart PNGs: `output/allocation_comparison.png`, `output/efficient_frontiers.png`, `output/correlation_matrix.png`, `output/erp_dashboard.png`, `output/price_history.png`
- Report: `output/report.md` (markdown summary with embedded chart references)

---

*Stack analysis: 2026-03-13*
