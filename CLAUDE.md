# CLAUDE.md

## Overview

Portfolio optimization and US macro analysis tool powered by the **portfolio-analysis** skill. No Anthropic API key needed -- Claude IS the AI layer.

## Commands

```bash
# Setup
python -m venv venv && source venv/Scripts/activate  # Windows (Git Bash)
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v
```

## Environment

- Python 3.10+ with venv
- Windows + Mac compatible
- No Unicode emojis in console output -- use `[OK]`, `[ERROR]`, `[WARN]` etc.
- All file I/O uses `encoding='utf-8'`

## Workflow

Invoke the **portfolio-analysis** skill whenever the user wants to analyze, optimize, or rebalance a portfolio. The skill handles everything: parsing, configuration, data download, optimization, validation, visualization, and report generation.

**Auto-run (Cowork mode)**: If the user provides a CSV/XLSX file or pastes portfolio holdings without explicit configuration instructions, invoke the skill with moderate defaults and skip the 6 configuration questions. The user can customize and re-run afterward.
