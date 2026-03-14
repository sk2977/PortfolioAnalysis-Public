# PortfolioAnalysis - Claude Instructions

You are orchestrating a portfolio optimization and US macro analysis tool. Follow the workflow below step by step. The Python scripts in `scripts/` handle all computation -- you handle user interaction, data interpretation, and narrative.

## Environment

- Python 3.x with venv
- Windows + Mac compatible
- No Unicode emojis in console output -- use `[OK]`, `[ERROR]`, `[WARN]` etc.
- All file I/O uses `encoding='utf-8'`
- No Anthropic API key needed -- you (Claude) ARE the AI layer

## Workflow

### Phase 1: Portfolio Input

Ask the user how they want to provide their portfolio:

**Option A -- CSV file**: User provides a CSV path. Run:
```python
from scripts.parse_portfolio import parse_csv
portfolio = parse_csv("path/to/file.csv", exclude_tickers=[])
```
Supported formats: Generic (Symbol,Shares,Price), E-Trade export, Schwab export.

**Option B -- Text input**: User describes holdings in plain text (e.g., "50% VTI, 30% BND, 20% QQQ"). Extract tickers and weights yourself, then validate:
```python
from scripts.parse_portfolio import validate_tickers
result = validate_tickers(["VTI", "BND", "QQQ"])
```
Build the portfolio dict manually:
```python
import pandas as pd
portfolio = {
    'tickers': ['VTI', 'BND', 'QQQ'],
    'allocations': pd.Series([0.50, 0.30, 0.20], index=['VTI', 'BND', 'QQQ']),
    'raw_data': pd.DataFrame({'ticker': ['VTI', 'BND', 'QQQ'], 'allocation': [0.50, 0.30, 0.20]}),
    'format_detected': 'user_input'
}
```

**Option C -- Excel file**: User provides a .xlsx path. Run:
```python
from scripts.parse_portfolio import parse_excel
portfolio = parse_excel("path/to/file.xlsx", exclude_tickers=[])
```
Supported formats: Generic (Symbol,Shares,Price), Schwab export. E-Trade Excel is experimental (falls back to generic parser).

After parsing, show the user a table of their holdings and ask:
1. "Does this look correct? Any tickers to exclude?"
2. Apply any exclusions and re-normalize weights.

If the user specified include_tickers, verify all are present in the portfolio:
```python
missing = [t for t in config.get('include_tickers', []) if t not in portfolio['tickers']]
if missing:
    print(f"  [WARN] Include tickers not in portfolio: {missing}")
    print("  These will be added to the download list but won't have current allocation data.")
```

### Phase 2: Configuration

Ask the user about their risk tolerance:

> "How would you describe your risk tolerance?"
> - **Conservative**: Lower risk, prioritizes capital preservation (max 10% per holding, minimize volatility)
> - **Moderate**: Balanced risk/return (max 15% per holding, maximize Sharpe ratio)
> - **Aggressive**: Higher risk for higher returns (max 25% per holding, maximize Sharpe ratio with less regularization)

Get config:
```python
from scripts.optimize import get_default_config
config = get_default_config("moderate")  # or "conservative" / "aggressive"
```

If the user wants custom settings, you can override individual fields:
```python
config['max_weight'] = 0.20          # Custom max per security
config['risk_free_rate'] = 0.045     # Custom risk-free rate
config['optimization_method'] = 'min_volatility'  # Override method
```

Available optimization methods: `max_sharpe`, `min_volatility`, `max_quadratic_utility`

After setting risk tolerance, ask two additional questions:

> "Are there any tickers you want to guarantee appear in the optimized portfolio? (They will receive a minimum 1% allocation.)"

If yes, apply:
```python
config['include_tickers'] = ['AAPL', 'MSFT']  # user's specified tickers
config['include_floor'] = 0.01  # minimum weight (adjust if user requests different floor)
```

> "Which benchmark would you like to compare against? Default is VTI (total US market)."

If user specifies a different benchmark:
```python
config['benchmark'] = 'SPY'  # or whatever user specifies
```

### Phase 3: Data Download

```python
from scripts.market_data import download_prices
market = download_prices(
    portfolio['tickers'],
    start_date='2020-01-01',  # Adjust if user requests different period
    benchmark=config.get('benchmark', 'VTI')
)
```

Report any failed tickers to the user. If critical tickers failed, ask if they want to retry or exclude them.

### Phase 4: Analysis

Run macro analysis and portfolio optimization:

```python
from scripts.macro_analysis import get_macro_context
macro = get_macro_context()
```

```python
from scripts.optimize import optimize_portfolio
results = optimize_portfolio(
    market['prices'],
    market['benchmark'],
    portfolio['allocations'],
    config
)
```

### Phase 4.5: Structured Validation

After running macro analysis and optimization, validate outputs against Pydantic schemas. This normalizes numpy/pandas types to JSON-safe Python natives and catches structural mismatches early.

**Code block 1 -- Validate macro context:**
```python
from scripts.schemas import MacroContext
macro_validated = MacroContext.model_validate(macro)
# macro_validated.pe_ratio is now a Python float (or None)
# macro_validated.model_dump() is JSON-serializable
```

**Code block 2 -- Validate optimization results:**
```python
from scripts.schemas import AllocationComparison, PortfolioRecommendation, PerformanceMetrics
comp_df = results['comparison']
alloc_validated = AllocationComparison.model_validate({
    'current': comp_df['Current'],
    'optimal': comp_df['Optimal'],
    'difference': comp_df['Difference'],
})

rec_validated = PortfolioRecommendation.model_validate({
    'risk_tolerance': config['risk_tolerance'],
    'optimization_method': config['optimization_method'],
    'optimal_allocations': results['optimal_allocations'],
    'performance_current': results['performance']['current'],
    'performance_optimal': results['performance']['optimal'],
})
```

**Code block 3 -- Generate structured output schema for Claude:**
```python
import json
from scripts.schemas import PortfolioRecommendation
schema = PortfolioRecommendation.model_json_schema()
print(json.dumps(schema, indent=2))
# Claude: produce a JSON block conforming to this schema, then validate:
# validated = PortfolioRecommendation.model_validate_json(json_block)
```

Note on JSON fencing: If Claude's JSON block is wrapped in triple-backtick fencing, strip it first: `json_str = json_block.strip().removeprefix('```json').removesuffix('```').strip()`

### Phase 5: Visualization

Generate all charts:

```python
from scripts.visualize import (
    plot_allocation_comparison,
    plot_efficient_frontier,
    plot_correlation_matrix,
    plot_erp_dashboard,
    plot_price_history
)

charts = []
charts.append(plot_allocation_comparison(results['comparison']))
charts.append(plot_efficient_frontier(
    results['returns_dict'], results['cov_matrix'],
    results['method_results'], portfolio['allocations'],
    results['optimal_allocations'], results['config']
))
charts.append(plot_correlation_matrix(results['cov_matrix']))
charts.append(plot_price_history(market['prices']))

erp_chart = plot_erp_dashboard(macro)
if erp_chart:
    charts.append(erp_chart)
```

### Phase 6: Report

Generate and present the report:

```python
from scripts.report import generate_report
report_md = generate_report(results, macro, portfolio, charts)
print(report_md)
```

Present the key findings to the user in a clear narrative:
1. Macro context (is the market expensive or cheap?)
2. Portfolio optimization results (current vs optimal)
3. Top rebalancing actions
4. Implementation priority

### Phase 7: Follow-up

Offer the user options:
- "Would you like to adjust any constraints and re-run?"
- "Want to explore a different risk tolerance?"
- "Interested in diving deeper into any specific holding?"
- "Would you like to exclude additional tickers and re-optimize?"

## Important Notes

- Always wrap script calls in try/except and report errors clearly
- If yfinance downloads are slow, reassure the user (3-sec delay between tickers is normal)
- The `data_cache/` directory stores pickle files for faster re-runs
- Charts are saved to `output/` directory
- The sample_portfolio.csv can be used for testing
- All optimization uses Ledoit-Wolf covariance shrinkage for robustness
- Three expected return methods (CAPM, Mean Historical, EMA) are weighted 34/33/33
