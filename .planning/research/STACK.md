# Technology Stack: Milestone Additions

**Project:** PortfolioAnalysis-Public
**Scope:** Additions only -- Excel support, structured outputs, Cowork compatibility, LLM qualitative layer
**Researched:** 2026-03-13
**Confidence note:** Bash, WebSearch, and Context7 MCP tools were unavailable in this research session. Findings are based on training data (knowledge cutoff August 2025). Version claims are flagged by confidence level. Verify pinned versions before shipping.

---

## What Is NOT Changing

The existing stack (pandas, numpy, yfinance, pyportfolioopt, matplotlib, seaborn, scikit-learn, requests, beautifulsoup4, pandas-datareader) is not in scope. This document covers only the four new capability areas:

1. Excel (.xlsx) file input
2. Structured outputs via Anthropic/Pydantic schemas
3. Claude Cowork (Claude Desktop) Python environment compatibility
4. LLM qualitative narrative layer

---

## 1. Excel Support

### Recommended Library

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openpyxl | 3.1.x | Read `.xlsx` files via `pd.read_excel()` | Confidence: HIGH |

**Rationale:**

`pandas.read_excel()` already exists in the codebase's pandas dependency. It requires an Excel engine as a backend. Two engines exist: `openpyxl` (reads `.xlsx`, the modern format) and `xlrd` (reads `.xls`, the legacy pre-2003 format).

Use `openpyxl`. It is the pandas-recommended engine for `.xlsx` files as of pandas 1.2+. `xlrd` removed `.xlsx` support in version 2.0 (2020) after a security decision -- it now only reads the old binary `.xls` format. Since brokerage exports (E-Trade, Schwab, Fidelity) all produce `.xlsx`, `openpyxl` is the only sensible choice.

`openpyxl` is also the engine `pandas.ExcelWriter` uses for output, so it covers both read and write if export is ever needed.

**What NOT to use:**
- `xlrd >= 2.0` -- intentionally removed `.xlsx` support; using it for `.xlsx` will raise an error
- `xlwings` -- requires Excel to be installed on the machine; not portable
- `pyxlsb` -- reads `.xlsb` (binary Excel), not `.xlsx`

**Integration pattern for `parse_portfolio.py`:**

The cleanest approach is a thin `parse_excel()` wrapper that detects sheet structure and hands off to the existing `_parse_generic()` / `_parse_etrade()` / `_parse_schwab()` logic after normalizing the DataFrame. `pd.read_excel()` returns the same DataFrame type as `pd.read_csv()`, so format-detection and row-parsing logic is reusable.

```python
# detect and dispatch (to add to parse_portfolio.py)
def parse_excel(file_path, exclude_tickers=None, sheet_name=0):
    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine='openpyxl')
    # Then reuse existing _detect_format / _parse_generic logic
```

**Requirements.txt addition:**
```
openpyxl>=3.1.0
```

---

## 2. Structured Outputs (Pydantic Models for Claude)

### Context

This project runs inside Claude Cowork. Claude IS the AI layer -- no Anthropic API key is used. "Structured outputs" here means: Claude returns JSON that Python parses into typed Pydantic models, enabling reliable downstream computation (not the Anthropic API's `response_format` parameter, which requires direct API access).

The pattern: Claude produces a JSON block in its response, Python extracts and validates it with Pydantic.

### Recommended Library

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pydantic | 2.x | Schema definition, JSON validation, typed output parsing | Confidence: HIGH |

**Rationale:**

Pydantic v2 (released stable June 2023, widely adopted by mid-2024) is the standard for Python data validation. It is significantly faster than v1 (Rust core via `pydantic-core`), has cleaner model syntax, and is used throughout the Python ecosystem (FastAPI, LangChain, the Anthropic SDK itself).

Use Pydantic v2 (not v1). The `model_validate()` and `model_json_schema()` APIs are cleaner and better supported going forward.

**What NOT to use:**
- `dataclasses` -- no JSON validation, no schema generation
- `marshmallow` -- more verbose, less ecosystem traction than Pydantic for this use case
- Anthropic SDK's `parse()` / structured output API -- requires direct API access with an API key, which is out of scope per PROJECT.md
- Raw `json.loads()` with dict access -- no type safety, no validation, brittle

**Cowork integration pattern:**

Claude produces a fenced JSON block in its response. The Python script extracts it, validates with Pydantic:

```python
import json
import re
from pydantic import BaseModel
from typing import Optional

class QualitativeAnalysis(BaseModel):
    macro_interpretation: str
    erp_signal: str          # "attractive" | "neutral" | "expensive"
    top_risks: list[str]     # max 3 items
    rebalancing_priority: str  # "high" | "moderate" | "low"
    narrative: str

def parse_llm_output(text: str) -> Optional[QualitativeAnalysis]:
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return QualitativeAnalysis.model_validate(data)
    except Exception:
        return None
```

The CLAUDE.md workflow instructs Claude to emit structured JSON, and `parse_llm_output()` in `scripts/report.py` (or a new `scripts/llm_analysis.py`) validates the response.

**Requirements.txt addition:**
```
pydantic>=2.0.0
```

---

## 3. Claude Cowork Compatibility

### What Cowork Is

Claude Desktop with a project folder linked. Claude reads files in the project directory, runs Python scripts by calling them through the conversation (not a subprocess -- Claude executes code directly in its tool-use environment).

### Constraints

| Constraint | Implication | Confidence |
|------------|-------------|------------|
| Python version: 3.10+ available in Cowork tool environment | Use `match/case`, `X | Y` union types, `list[str]` generics -- all safe | MEDIUM |
| No interactive stdin | Scripts must not use `input()` -- all interactivity is in the Claude conversation | HIGH |
| No display GUI | `matplotlib.pyplot.show()` must never be called -- use `savefig()` only | HIGH |
| File paths: absolute or relative to project root | Use `pathlib.Path` with `__file__`-relative paths | HIGH |
| Encoding: UTF-8 safe in tool environment, but cp1252 for console output display | Already handled by current codebase conventions | HIGH |
| Network access: available | yfinance, FRED, Multpl.com calls will work | MEDIUM |
| No pip install at runtime | All dependencies must be pre-installed in the venv | HIGH |

### No New Libraries Required

Cowork compatibility is achieved through code conventions, not new dependencies. Key rules already followed by the codebase:

- `savefig()` used everywhere in `visualize.py` -- no `show()` calls present
- `encoding='utf-8'` on all file I/O
- No `input()` calls in any script
- Scripts are stateless functions, callable by Claude as tools

**One addition needed -- Cowork-safe matplotlib backend:**

```python
# At top of visualize.py, before any other matplotlib import
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend, safe for headless/Cowork execution
import matplotlib.pyplot as plt
```

If `matplotlib.use('Agg')` is not set and a GUI backend is attempted in the Cowork environment, chart generation will fail silently or raise. This is a code fix, not a dependency addition.

**Requirements.txt: no additions for this area.**

---

## 4. LLM Qualitative Narrative Layer

### Pattern

Claude, running in Cowork, receives the structured analysis results (macro dict, results dict) and produces qualitative commentary. The output is a Pydantic-validated JSON block (see Section 2). A new `scripts/llm_analysis.py` module defines the schemas and parsing logic.

### No New External Libraries Required

The qualitative layer is purely in-process: Claude produces text, Python parses it. The only dependency is Pydantic (already covered in Section 2).

**What NOT to use:**
- LangChain -- heavyweight, unnecessary dependency for single-model in-process parsing
- `anthropic` SDK -- requires API key, out of scope
- `openai` SDK -- wrong provider, out of scope
- `instructor` library -- wraps the Anthropic SDK, also requires API key

### Recommended Schema Design

Define schemas in a new `scripts/llm_analysis.py` module. Keep schemas flat and simple -- deeply nested structures are harder for LLMs to reliably populate.

```python
from pydantic import BaseModel, Field
from typing import Literal

class MacroSignal(BaseModel):
    erp_signal: Literal["attractive", "neutral", "expensive"]
    market_commentary: str = Field(max_length=500)
    key_risk_factors: list[str] = Field(max_items=3)

class PortfolioNarrative(BaseModel):
    overall_assessment: str = Field(max_length=300)
    top_rebalancing_rationale: str = Field(max_length=400)
    implementation_guidance: str = Field(max_length=300)
    confidence_note: str = Field(max_length=200)

class FullQualitativeAnalysis(BaseModel):
    macro: MacroSignal
    portfolio: PortfolioNarrative
```

Use `Literal` types for enumerated fields -- they are self-documenting in the JSON schema and constrain LLM output. Use `max_length` to prevent runaway responses. Keep `list` fields bounded with `max_items`.

**Requirements.txt: no additions beyond pydantic (Section 2).**

---

## Complete Delta: requirements.txt Changes

Current `requirements.txt` additions required for the milestone:

```
openpyxl>=3.1.0
pydantic>=2.0.0
```

Remove (already flagged as unused in CONCERNS.md):
```
# python-dotenv>=1.0.0  -- never imported; remove
```

**Final additions count: 2 packages.** The entire milestone is achievable with two new dependencies plus code changes. This aligns with the project's "minimal dependencies" constraint.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Excel engine | openpyxl | xlrd | xlrd dropped .xlsx support in v2.0; only handles legacy .xls |
| Excel engine | openpyxl | xlwings | Requires Microsoft Excel installed; not portable |
| JSON validation | pydantic v2 | pydantic v1 | v1 is deprecated; v2 is faster (Rust core) and has cleaner API |
| JSON validation | pydantic v2 | marshmallow | Less ecosystem traction; more boilerplate for same outcome |
| JSON validation | pydantic v2 | dataclasses | No validation, no JSON schema generation |
| LLM orchestration | in-process JSON parsing | langchain | Heavyweight framework for a single in-process operation |
| LLM orchestration | in-process JSON parsing | anthropic SDK | Requires API key; project runs Claude as the AI layer, not via API |
| Structured outputs | Pydantic + regex extraction | Anthropic API response_format | Requires direct API access with key; out of scope per PROJECT.md |

---

## Installation

```bash
# Activate project venv first
pip install openpyxl>=3.1.0 pydantic>=2.0.0
```

Or update `requirements.txt` and run:
```bash
pip install -r requirements.txt
```

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| openpyxl as Excel engine | HIGH | Industry standard, well-documented; xlrd's .xlsx removal is a documented fact |
| pydantic v2 recommendation | HIGH | Stable since June 2023; used by Anthropic SDK itself |
| Cowork execution constraints | MEDIUM | Based on known Claude Desktop behavior patterns; verify no-GUI and no-stdin in actual Cowork environment before shipping |
| matplotlib Agg backend requirement | MEDIUM | Standard practice for headless Python; verify in actual Cowork environment |
| No API key required (Cowork model) | HIGH | Confirmed by PROJECT.md out-of-scope constraints |
| pydantic field constraints (max_items) | LOW | Pydantic v2 may use `max_length` validator differently for lists; verify field annotation syntax against pydantic v2 docs before implementing |

---

*Research date: 2026-03-13 | Scope: Milestone additions only | Do not re-research existing stack*
