---
name: portfolio-analysis
description: "Analyze and optimize investment portfolios with US macro-economic context. Use this skill whenever the user wants to: analyze a stock portfolio, optimize asset allocation, rebalance holdings, compare current vs optimal weights, run mean-variance optimization, review economic indicators alongside investments, parse brokerage exports (E-Trade, Schwab, CSV, Excel), or asks about Sharpe ratios, efficient frontiers, or expected returns. Also triggers for requests like 'analyze my portfolio', 'optimize my holdings', 'rebalance my stocks', 'what should my allocation be', 'how is my portfolio positioned', 'run the portfolio tool', or any request involving portfolio tickers with allocation percentages. Even if the user just pastes a list of tickers with weights, this skill applies."
---

# Portfolio Analysis & Optimization

You are orchestrating a portfolio optimization pipeline. You read these instructions, execute Python code blocks via tool use, and present results conversationally. The bundled Python scripts are libraries -- you call their functions, not run them as standalone CLI tools. No Anthropic API key is needed -- you ARE the AI layer.

## Architecture

**Data flow**: User input -> `parse_portfolio` -> `market_data` (yfinance + pickle cache) -> `macro_analysis` (FRED indicators) -> `optimize` (pyportfolioopt) -> `schemas` (Pydantic validation) -> You generate narratives -> `visualize` (matplotlib PNGs) -> `report` (markdown assembly)

**Key design decisions**:
- Three expected return methods (CAPM, Mean Historical, EMA) weighted 34/33/33, optimized independently, then combined
- Ledoit-Wolf covariance shrinkage for robustness
- Pydantic schemas validate at integration points only ("wrap, don't rewrite")
- `data_cache/` stores pickle files with 4-hour TTL; `output/` stores charts and reports
- yfinance downloads use 3-second delays between tickers to avoid rate limiting

## Setup

Before running any code, complete these setup steps once per session:

1. **Locate scripts**: The Python modules are in the `scripts/` directory adjacent to this file. Resolve the absolute path to that directory and store it as `SKILL_SCRIPTS_DIR`.

2. **Python environment**: Check if a venv exists in the working directory. If not, create one:
```bash
python -m venv venv && source venv/Scripts/activate  # Windows (Git Bash)
# or: source venv/bin/activate  # macOS/Linux
pip install -r <SKILL_SCRIPTS_DIR>/requirements.txt
```

3. **Add scripts to path**: At the start of every Python execution block, ensure the scripts directory is on `sys.path`:
```python
import sys
sys.path.insert(0, '<SKILL_SCRIPTS_DIR>')  # Replace with resolved absolute path
```

4. **Output directories**: The scripts create `data_cache/` and `output/` automatically. A sample portfolio CSV is at `<SKILL_DIR>/assets/sample_portfolio.csv`.

## Environment Constraints

- No Unicode emojis in console output -- use `[OK]`, `[ERROR]`, `[WARN]`
- Use `->` instead of arrow symbols, `x` instead of multiplication symbols
- All file I/O uses `encoding='utf-8'`

---

## Workflow

### Phase 1: Portfolio Input

Ask the user how they want to provide their portfolio:

**Option A -- CSV file**: User provides a CSV path.
```python
from parse_portfolio import parse_csv
portfolio = parse_csv("path/to/file.csv", exclude_tickers=[])
```
Supported formats: Generic (Symbol, Shares, Price), E-Trade export, Schwab export.

**Option B -- Text input**: User describes holdings in plain text (e.g., "50% VTI, 30% BND, 20% QQQ"). Extract tickers and weights yourself, then validate:
```python
from parse_portfolio import validate_tickers
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

**Option C -- Excel file**: User provides a .xlsx path.
```python
from parse_portfolio import parse_excel
portfolio = parse_excel("path/to/file.xlsx", exclude_tickers=[])
```
Supported formats: Generic (Symbol, Shares, Price), Schwab export. E-Trade Excel is experimental (falls back to generic parser).

After parsing, show the user a table of their holdings and ask:
1. "Does this look correct? Any tickers to exclude?"
2. Apply any exclusions and re-normalize weights.

If the user specified include_tickers later (Q4), verify all are present in the portfolio:
```python
missing = [t for t in config.get('include_tickers', []) if t not in portfolio['tickers']]
if missing:
    print(f"  [WARN] Include tickers not in portfolio: {missing}")
    print("  These will be added to the download list but won't have current allocation data.")
```

### Phase 2: Configuration

**CRITICAL: Ask ALL 6 questions below. Ask them ONE AT A TIME. Wait for the user's answer before asking the next question. Do NOT skip any question. Do NOT combine multiple questions into one message. Do NOT offer to skip questions or present a "quick mode" option. Do NOT proceed to Phase 3 until all 6 questions have been asked and answered.**

After the user confirms their portfolio in Phase 1, begin with Question 1. After they answer, ask Question 2. Continue until all 6 are done.

**Question 1 of 6 -- Risk tolerance:**
> "How would you describe your risk tolerance?
> - Conservative: Lower risk, prioritizes capital preservation
> - Moderate: Balanced risk/return
> - Aggressive: Higher risk for higher returns"

**Question 2 of 6 -- Maximum allocation per holding:**
> "What is the maximum allocation you want for any single holding? This caps position size to control concentration risk. (Default: 10% conservative, 15% moderate, 25% aggressive -- or specify a custom percentage)"

**Question 3 of 6 -- Minimum allocation per holding:**
> "Would you like to set a minimum allocation per holding to ensure every holding keeps at least a small position? Without a minimum, the optimizer may drop holdings entirely. (Default: 0%. Common choices: 1-2% to keep all holdings)"

**Question 4 of 6 -- Guaranteed tickers:**
> "Are there any tickers you want to guarantee appear in the optimized portfolio? (These tickers will be kept even if the optimizer would otherwise drop them, with at least a 1% allocation)"

**Question 5 of 6 -- Benchmark:**
> "Which benchmark would you like to compare against? (Default: VTI -- total US market)"

**Question 6 of 6 -- Exclusions:**
> "Are there any tickers you want to exclude from the optimized portfolio?"

After all 6 answers are collected, apply the configuration:

```python
from optimize import get_default_config
config = get_default_config("moderate")  # or "conservative" / "aggressive" per Q1

# Q2: Max allocation
config['max_weight'] = 0.20  # user's answer

# Q3: Min allocation (ensures every holding keeps at least a small position)
config['min_weight'] = 0.01  # user's answer (0.0 if they said no/default)
# Note: min_weight x number_of_holdings must be <= 100%

# Q4: Guaranteed tickers
config['include_tickers'] = ['AAPL', 'MSFT']  # user's answer ([] if none)
config['include_floor'] = 0.01

# Q5: Benchmark
config['benchmark'] = 'SPY'  # user's answer ('VTI' if default)

# Q6: Exclusions -- remove from ticker list and re-normalize weights
exclude = ['TSLA', 'COIN']  # user's answer ([] if none)
if exclude:
    portfolio['tickers'] = [t for t in portfolio['tickers'] if t not in exclude]
    portfolio['allocations'] = portfolio['allocations'].drop(exclude, errors='ignore')
    portfolio['allocations'] = portfolio['allocations'] / portfolio['allocations'].sum()
```

**Feasibility guard**: After applying exclusions, check that `max_weight * len(portfolio['tickers']) >= 1.0`. If not, the optimizer cannot produce weights summing to 100%. Auto-adjust: `config['max_weight'] = max(config['max_weight'], 1.0 / len(portfolio['tickers']) + 0.05)` and inform the user of the adjustment.

Available optimization methods: `max_sharpe` (Maximum Sharpe Ratio), `min_volatility` (Minimum Volatility), `max_quadratic_utility` (Maximum Utility, Quadratic)

### Phase 3: Data Download

```python
from market_data import download_prices
market = download_prices(
    portfolio['tickers'],
    start_date='2020-01-01',  # Adjust if user requests different period
    benchmark=config.get('benchmark', 'VTI')
)
```

Report any failed tickers to the user. If critical tickers failed, ask if they want to retry or exclude them.

### Phase 4: Analysis

Run economic indicators and portfolio optimization:

```python
from macro_analysis import get_macro_context
macro = get_macro_context()  # Fetches 8 FRED indicators (rates, employment, inflation, growth)
```

```python
from optimize import optimize_portfolio
results = optimize_portfolio(
    market['prices'],
    market['benchmark'],
    portfolio['allocations'],
    config
)
```

### Phase 4.5: Structured Validation

Validate outputs against Pydantic schemas. This normalizes numpy/pandas types to JSON-safe Python natives and catches structural mismatches early.

**Code block 1 -- Validate macro context:**
```python
from schemas import MacroContext
macro_validated = MacroContext.model_validate(macro)
```

**Code block 2 -- Validate optimization results:**
```python
from schemas import AllocationComparison, PortfolioRecommendation, PerformanceMetrics
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

**Code block 3 -- Generate structured output schema:**
```python
import json
from schemas import PortfolioRecommendation
schema = PortfolioRecommendation.model_json_schema()
print(json.dumps(schema, indent=2))
```

Note on JSON fencing: If a JSON block is wrapped in triple-backtick fencing, strip it first: `json_str = json_block.strip().removeprefix('```json').removesuffix('```').strip()`

### Phase 5: Visualization

Generate all charts:

```python
from visualize import (
    plot_allocation_comparison,
    plot_efficient_frontier,
    plot_correlation_matrix,
    plot_macro_primary,
    plot_macro_secondary,
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

macro_chart1 = plot_macro_primary(macro)
if macro_chart1:
    charts.append(macro_chart1)
macro_chart2 = plot_macro_secondary(macro)
if macro_chart2:
    charts.append(macro_chart2)
```

### Phase 5.5: Qualitative Narrative

Before calling `generate_report()`, generate four narrative strings. You produce these by reading the structured data -- no API call needed. Read `references/narrative-guide.md` for detailed generation instructions and examples for each narrative.

The four narratives:
1. **macro_narrative** -- 2-3 sentences interpreting the economic environment with specific indicator values
2. **holding_commentary** -- Dict of ticker -> commentary for tickers where abs(Difference) > 5pp
3. **macro_portfolio_note** -- 2-4 sentences connecting macro conditions to allocation recommendations (the most important narrative)
4. **method_spread_note** -- Confidence warning for tickers with >5pp return estimate spread across methods (None if none exceed threshold)

Use observational language throughout -- never investment advice language ("you should buy/sell").

Store all four as Python variables for the next step.

### Phase 6: Report

Generate and present the report:

```python
from report import generate_report
report_md = generate_report(results, macro, portfolio, charts,
                             macro_narrative=macro_narrative,
                             holding_commentary=holding_commentary,
                             macro_portfolio_note=macro_portfolio_note,
                             method_spread_note=method_spread_note)
print(report_md)
```

`generate_report()` produces two files:
- `output/report.html` -- the **primary deliverable**, a self-contained HTML file with all chart images embedded as base64 data URIs
- `output/report.md` -- a markdown copy for reference

When sharing results with the user, link to the HTML file.

Present key findings to the user in a clear narrative:
1. Macro context (current economic environment)
2. Portfolio optimization results (current vs optimal)
3. Top rebalancing actions
4. Macro-portfolio synthesis (how macro conditions relate to recommended changes)
5. Implementation priority
6. Confidence indicators (method spread warnings)

### Phase 7: Follow-up

Offer the user options:
- "Would you like to adjust any constraints and re-run?"
- "Want to explore a different risk tolerance?"
- "Interested in diving deeper into any specific holding?"
- "Would you like to exclude additional tickers and re-optimize?"

---

## Important Notes

- Always wrap script calls in try/except and report errors clearly
- If yfinance downloads are slow, reassure the user (3-second delay between tickers is normal)
- The `data_cache/` directory stores pickle files for faster re-runs (4-hour TTL)
- Charts are saved to `output/` directory
- All optimization uses Ledoit-Wolf covariance shrinkage for robustness
- Three expected return methods (CAPM, Mean Historical, EMA) are weighted 34/33/33 and combined
