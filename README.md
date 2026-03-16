# PortfolioAnalysis

<p align="center">
  <img src="assets/banner.png" alt="Portfolio Optimizer" width="800">
</p>

Portfolio optimization and US macro analysis tool powered by Claude. Provide your holdings, get optimized allocation recommendations grounded in current economic conditions.

## What It Does

- Parses your portfolio from CSV (E-Trade, Schwab, or generic format), Excel, or plain text
- Downloads historical price data via Yahoo Finance
- Calculates optimal allocation using 3 expected return methods (CAPM, Mean Historical, EMA) with Ledoit-Wolf covariance shrinkage
- Fetches key US economic indicators from FRED (interest rates, unemployment, inflation, GDP, corporate profits, S&P 500)
- Validates all outputs with Pydantic schemas
- Generates 6 charts and a markdown report with rebalancing recommendations and macro-portfolio synthesis

## Prerequisites

- Python 3.10+
- [Claude Desktop](https://claude.ai/download) (Cowork mode) or [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Installation

### Option A -- Install as a skill (recommended)

```bash
npx add-skill sk2977/PortfolioAnalysis-Public --skill portfolio-analysis
```

Then install Python dependencies:
```bash
pip install -r .claude/skills/portfolio-analysis/scripts/requirements.txt
```

### Option B -- Clone the full repository

```bash
git clone https://github.com/sk2977/PortfolioAnalysis-Public.git
cd PortfolioAnalysis-Public
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Getting Started

### Claude Desktop (Cowork)

1. Open Claude Desktop and switch to the Cowork tab
2. Select "Work in a folder" and choose the project directory
3. Upload your CSV/XLSX file or describe your holdings in plain text
4. Type: "Run portfolio analysis" and Claude handles the rest

### Claude Code

1. Run `claude` from the project directory
2. Tell Claude about your portfolio (file path, or describe in text)
3. Claude walks you through configuration and runs the full pipeline

## Usage Examples

**Use the sample portfolio:**
> "Run portfolio analysis using the sample portfolio"

**Provide your own CSV:**
> "Analyze my portfolio from my_holdings.csv"

**Describe holdings in plain text:**
> "Analyze my portfolio: 40% VTI, 25% QQQ, 15% BND, 10% SCHD, 10% VYM"

## CSV Format

The simplest format:

```csv
Symbol,Shares,Price
AAPL,50,175.00
MSFT,30,380.00
VTI,100,220.00
```

E-Trade and Schwab CSV/Excel exports are also auto-detected.

## How It Works

The `portfolio-analysis` skill orchestrates a 7-phase pipeline:

1. **Portfolio Input** -- Parses holdings from CSV, Excel, or text. Auto-detects broker format.
2. **Configuration** -- Asks 6 questions one at a time: risk tolerance, max/min allocation, guaranteed tickers, benchmark, exclusions. (Or runs with moderate defaults in auto-run mode.)
3. **Data Download** -- Fetches historical prices from Yahoo Finance with local pickle caching (4-hour TTL).
4. **Analysis** -- Runs macro analysis (8 FRED indicators) and mean-variance optimization (3 return methods weighted 34/33/33).
5. **Validation** -- Pydantic schemas normalize numpy/pandas types and catch structural issues.
6. **Visualization** -- Generates 6 charts: allocation comparison, efficient frontiers (4-panel), correlation matrix, price history, and two macro dashboards.
7. **Narrative & Report** -- Claude generates qualitative commentary (macro interpretation, holding-level analysis, macro-portfolio synthesis, confidence warnings), then assembles a markdown report.

No API keys required -- Claude provides the AI layer directly.

## Project Structure

```
PortfolioAnalysis-Public/
├── CLAUDE.md                  # Points Claude to the skill
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── .claude/
│   └── skills/
│       └── portfolio-analysis/    # The skill (source of truth)
│           ├── SKILL.md           # Full workflow instructions
│           ├── scripts/           # All Python source code
│           ├── assets/            # Sample portfolio CSV
│           ├── evals/             # Skill evaluation definitions
│           └── references/        # Narrative generation guide
├── scripts/                   # Import proxy for tests
├── tests/                     # Test suite (pytest)
├── data_cache/                # (gitignored) Pickle cache for API data
└── output/                    # (gitignored) Generated reports and charts
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.

## License

[MIT](LICENSE)
