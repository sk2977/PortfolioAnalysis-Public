# CLAUDE.md

## Overview

Portfolio optimization and US macro analysis tool powered by a Claude Code skill. Python scripts in `.claude/skills/portfolio-analysis/scripts/` handle computation; Claude handles user interaction, data interpretation, and narrative generation. No Anthropic API key needed.

## Commands

```bash
# Setup
python -m venv venv && source venv/Scripts/activate  # Windows (Git Bash)
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_stab.py -v
```

## Environment

- Python 3.10+ with venv
- Windows + Mac compatible
- No Unicode emojis in console output -- use `[OK]`, `[ERROR]`, `[WARN]` etc.
- All file I/O uses `encoding='utf-8'`

## Workflow

This project uses the **portfolio-analysis** skill at `.claude/skills/portfolio-analysis/SKILL.md`. Invoke it whenever the user wants to analyze, optimize, or rebalance a portfolio. The skill handles the full 7-phase pipeline: parsing, configuration, data download, optimization, validation, visualization, and report generation.

**Auto-run (Cowork mode)**: If the user provides a CSV/XLSX file or pastes portfolio holdings without explicit configuration instructions, invoke the skill with these defaults and skip the 6 configuration questions:
- Risk tolerance: moderate
- Max allocation: 15%, Min allocation: 0%
- No guaranteed tickers or exclusions
- Benchmark: VTI

The user can request changes or re-run with custom settings afterward.

## Architecture

**Data flow**: User input -> `parse_portfolio` -> `market_data` (yfinance + pickle cache) -> `macro_analysis` (FRED indicators) -> `optimize` (pyportfolioopt, 3 return methods weighted 34/33/33) -> `schemas` (Pydantic validation) -> Claude generates narratives -> `visualize` (matplotlib PNGs) -> `report` (markdown assembly)

All source code lives in `.claude/skills/portfolio-analysis/scripts/`. The top-level `scripts/` package is a thin proxy that redirects imports there (so tests can use `from scripts.X import ...`).
