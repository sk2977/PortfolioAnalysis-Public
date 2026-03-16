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

Always ask all 6 configuration questions. Do NOT offer to skip them or present a "quick mode" option.

## Output

The final deliverable is a self-contained HTML report (`output/report.html`) with all chart images embedded as base64 data URIs. No external image files are needed to view the report. A markdown copy (`output/report.md`) is also saved for reference. When sharing results with the user, link to the HTML file.
