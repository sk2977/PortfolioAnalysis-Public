# Portfolio Analysis - Getting Started

Welcome! This tool helps you optimize your stock portfolio allocation and understand the current US macro environment.

## Quick Start

Just tell Claude one of the following:

**Option 1 - Use the sample portfolio:**
> "Run portfolio analysis using sample_portfolio.csv"

**Option 2 - Provide a CSV file:**
> "Analyze my portfolio from [path/to/your/file.csv]"

Your CSV should have columns like `Symbol, Shares, Price` or `Symbol, Weight%`. E-Trade and Schwab exports are also supported automatically.

**Option 3 - Describe your portfolio:**
> "Analyze my portfolio: 40% VTI, 25% QQQ, 15% BND, 10% SCHD, 10% VYM"

## What You'll Get

1. **Macro Context** - Key US economic indicators (interest rates, unemployment, inflation, GDP)

2. **Portfolio Optimization** - Optimal allocation using three methods (CAPM, Mean Historical, EMA), weighted together for robustness

3. **Rebalancing Recommendations** - What to increase, what to decrease, and by how much

4. **Charts** - Efficient frontier, allocation comparison, correlation matrix, price history, economic indicators dashboards

5. **Risk Assessment** - Current vs optimal Sharpe ratio, volatility comparison

## Customization

You can tell Claude your preferences:

- **Risk tolerance**: "I'm conservative" / "I'm moderate" / "I'm aggressive"
- **Exclusions**: "Exclude AAPL and TSLA from the analysis"
- **Max position size**: "No more than 10% in any single stock"
- **Time period**: "Use data from 2018 onwards"
- **Optimization method**: "Minimize volatility instead of maximizing Sharpe"

## Risk Tolerance Presets

| Preset | Max Per Stock | Method | Description |
|--------|--------------|--------|-------------|
| Conservative | 10% | Min Volatility | Capital preservation focus |
| Moderate | 15% | Max Sharpe | Balanced risk/return |
| Aggressive | 25% | Max Sharpe | Higher return potential |

## Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.
