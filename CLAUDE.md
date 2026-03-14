# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Portfolio optimization and US macro analysis tool. Claude orchestrates the pipeline -- Python scripts in `scripts/` handle computation; Claude handles user interaction, data interpretation, and narrative generation. No Anthropic API key needed.

## Commands

```bash
# Setup
python -m venv venv && source venv/Scripts/activate  # Windows (Git Bash)
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_stab.py -v

# Run a specific test
python -m pytest tests/test_stab.py::test_reindex_ffill -v
```

## Architecture

**Claude-as-orchestrator pattern**: This is NOT a standalone CLI app. Claude reads CLAUDE.md, follows the phased workflow below, executes Python code blocks via tool use, and presents results conversationally. The scripts are libraries, not entry points.

**Data flow**: CSV/text input -> `parse_portfolio` -> `market_data` (yfinance + pickle cache) -> `macro_analysis` (ERP/PE/yields) -> `optimize` (pyportfolioopt) -> `schemas` (Pydantic validation) -> Claude generates narratives -> `visualize` (matplotlib PNGs) -> `report` (markdown assembly)

**Key design decisions**:
- Three expected return methods (CAPM, Mean Historical, EMA) weighted 34/33/33 and optimized independently, then combined
- Ledoit-Wolf covariance shrinkage for robustness
- Pydantic schemas validate at integration points only ("wrap, don't rewrite" -- pipeline functions return plain dicts)
- `data_cache/` stores pickle files with 4-hour TTL; `output/` stores charts and reports (both gitignored)
- yfinance downloads use 3-second delays between tickers to avoid rate limiting

## Environment

- Python 3.10+ with venv
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

After setting risk tolerance, ask about max allocation:

> "Would you like to cap the maximum allocation per holding? (Default: 10% conservative, 15% moderate, 25% aggressive -- or specify a custom cap like 12%, 20%)"

If user specifies a custom cap:
```python
config['max_weight'] = 0.20  # user's specified cap
```

Then ask two additional questions:

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

### Phase 5.5: Qualitative Narrative

Before calling generate_report(), generate three narrative strings. You (Claude) produce these by reading the structured data -- no API call needed.

**1. Macro narrative (macro_narrative):**
Read macro['erp'], macro['pe_ratio'], macro['treasury_yield'], and macro['interpretation'].
Write 2-3 sentences interpreting the current macro regime in plain language.
You MUST cite the actual ERP value and P/E ratio in your text.

Example style:
> "At a P/E of 27.4, the S&P 500 earnings yield is 3.6%, below the 10Y Treasury at 4.3%, producing an ERP of -0.7%. This negative premium suggests equities offer no compensation over risk-free bonds at current valuations."

**2. Holding commentary (holding_commentary):**
From results['comparison'], identify tickers where abs(Difference) > 0.05 (5 percentage points).
For each, write one sentence explaining the direction and magnitude of the recommended change.
Return as a dict: {"TICKER": "commentary sentence"}.
Only include material changes -- skip tickers with smaller shifts.

Do NOT use investment advice language ("you should buy/sell"). Use observational language ("the optimizer suggests increasing", "the model recommends reducing").

**3. Method spread note (method_spread_note):**
From results['returns_dict'], compare CAPM, mean historical, and EMA expected returns per ticker.
If any ticker's spread (max - min across methods) exceeds 5 percentage points (0.05):

Set method_spread_note to a string like:
> "[TICKER]'s expected return ranges from X.X% (CAPM) to Y.Y% (EMA) -- a spread of Z.Zpp. Treat this ticker's recommendation as lower confidence."

If multiple tickers exceed the threshold, mention each.
If no ticker exceeds the threshold, set method_spread_note = None.

Store all three as Python variables for the next step.

### Phase 6: Report

Generate and present the report:

```python
from scripts.report import generate_report
report_md = generate_report(results, macro, portfolio, charts,
                             macro_narrative=macro_narrative,
                             holding_commentary=holding_commentary,
                             method_spread_note=method_spread_note)
print(report_md)
```

Present the key findings to the user in a clear narrative:
1. Macro context (is the market expensive or cheap?)
2. Portfolio optimization results (current vs optimal)
3. Top rebalancing actions
4. Implementation priority
5. Qualitative commentary (macro interpretation, holding notes, confidence indicators)

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
