# Domain Pitfalls

**Domain:** Portfolio optimization toolkit with LLM orchestration, structured outputs, Excel support, Claude Cowork integration
**Researched:** 2026-03-13
**Confidence note:** HIGH confidence on Python/pandas/openpyxl patterns (well-established). MEDIUM confidence on Cowork-specific execution details (limited public documentation). LOW confidence on Anthropic structured output schema specifics in Cowork context (verify during implementation).

---

## Critical Pitfalls

Mistakes that cause rewrites or major regressions.

### Pitfall 1: Structured Output Schema Mismatch with Actual Data

**What goes wrong:** Pydantic models or JSON schemas are designed at planning time against idealized data shapes. During runtime, pyportfolioopt returns pandas Series/DataFrames with float64 numpy dtypes, NaN values, and index labels -- none of which serialize cleanly into JSON schema validators.

**Why it happens:** Python dicts passed from `optimize_portfolio()` contain `pd.Series` (not plain dicts), `np.float64` (not Python float), and sometimes `None` where schema expects a numeric type. Pydantic v2 is stricter than v1 and will reject numpy scalars without coercion.

**Consequences:** Schema validation failures at report generation time, after all expensive computation has already completed. Either the whole pipeline crashes at the last step, or silent coercion produces wrong types (e.g., `np.nan` serialized as `null` in JSON, breaking downstream field access).

**Prevention:**
- Run all data dicts through explicit normalization before schema validation: cast numpy floats with `float(x)`, convert Series to `dict`, replace NaN with `None` or sentinel values
- Add a `to_serializable()` utility function that normalizes the pipeline's four data contracts (`portfolio`, `market`, `macro`, `results`) before they ever touch schema validation
- Use `model_config = ConfigDict(arbitrary_types_allowed=False)` in Pydantic models to catch violations at definition time, not runtime

**Detection (warning signs):**
- `ValidationError: value is not a valid float` despite looking like a number
- `Object of type float64 is not JSON serializable` in tracebacks
- Tests pass with synthetic Python dicts but fail with real pipeline output

**Phase:** Structured outputs phase. Add normalization layer before writing schemas.

---

### Pitfall 2: Claude Cowork Python Environment is Not the User's venv

**What goes wrong:** The CLAUDE.md workflow calls `from scripts.parse_portfolio import parse_csv` as if Claude executes inside the project's virtual environment. In Claude Cowork (Claude Desktop), Python execution happens in whatever environment Cowork has access to -- which may be system Python, a Cowork-managed environment, or user's default `python3`. The project venv (`venv/`, `.venv/`) is not auto-activated.

**Why it happens:** Cowork does not source shell profiles or activate virtual environments before running Python. If a user clones the repo and runs without explicit venv activation, imports of `pyportfolioopt`, `pandas-datareader`, `openpyxl`, etc. will fail with `ModuleNotFoundError`.

**Consequences:** Complete pipeline failure on first run for most users. Error message will be cryptic (`No module named 'pypfopt'`) rather than "activate your venv".

**Prevention:**
- Add a preflight check script (`scripts/check_env.py`) that tests all required imports and prints actionable instructions if any fail
- Document venv activation as Step 0 in CLAUDE.md, not buried in README
- Consider a `requirements-check` function Claude can call before Phase 1 to validate the environment
- The Cowork workflow instruction in CLAUDE.md should begin with: verify `python -c "import pypfopt"` succeeds before proceeding

**Detection:**
- `ModuleNotFoundError` on any `scripts/` import
- User reports "worked yesterday, broken today" (system Python upgrade changed defaults)

**Phase:** Cowork compatibility phase. Must be the first thing addressed.

---

### Pitfall 3: Excel Parsing Assumes Numeric Types that Arrive as Strings

**What goes wrong:** When users upload an Excel file with portfolio data, openpyxl reads cells differently depending on whether the Excel file was formatted as Number, Currency, Accounting, or General. A cell showing "1,234.56" formatted as Accounting arrives as a string `"1,234.56"` or float `1234.56` depending on openpyxl version and cell format. Similarly, percentage cells (10%) arrive as `0.10` (float) in some formatters and `"10%"` (string) in others.

**Why it happens:** Excel cell formatting is a display layer separate from the underlying value type. openpyxl exposes the underlying value, but legacy Excel files and files exported from brokerage platforms often bake the formatting into the value (especially .xls files converted to .xlsx).

**Consequences:** Silent wrong data. A portfolio weight of `"0.25"` (string) passes ticker validation but causes `pd.Series` arithmetic to fail or silently produce NaN during allocation normalization. The existing CSV parsing code assumes clean numeric inputs and will not handle this.

**Prevention:**
- Normalize all Excel-sourced numeric fields through a coerce function: `pd.to_numeric(val, errors='coerce')` after stripping `$`, `,`, `%`
- Explicit test cases for the three brokerage export formats (E-Trade, Schwab, generic) in Excel form
- Treat Excel parsing as a separate code path from CSV parsing -- do not try to unify them behind a single regex-based format detector
- Add a `format_detected: 'excel_generic'` variant to the portfolio dict contract

**Detection:**
- Allocation weights summing to a wildly wrong number (e.g., 25.0 instead of 0.25 if percentages parsed as whole numbers)
- `TypeError: unsupported operand type(s) for +: 'float' and 'str'` during normalization

**Phase:** Excel support phase. Define the normalization layer before writing any brokerage-specific parsers.

---

### Pitfall 4: LLM Qualitative Narrative Contradicts Quantitative Results

**What goes wrong:** Claude generates qualitative commentary ("This portfolio is well-diversified across sectors") that directly contradicts what the quantitative analysis shows (correlation matrix shows 0.95 correlation between half the holdings). This happens when the LLM prompt does not include the actual numeric results, only high-level summaries.

**Why it happens:** Report generation tempts a pattern where Claude summarizes qualitatively from narrative context rather than from the structured `results` and `macro` dicts. If the prompt passed to Claude for qualitative commentary omits key metrics (actual ERP value, actual Sharpe ratio, actual correlation clusters), Claude will hallucinate plausible-sounding but potentially wrong interpretations.

**Consequences:** Users receive confident-sounding recommendations that are wrong. For a public tool used for financial decisions, this is a serious credibility and trust problem. Users may act on incorrect analysis.

**Prevention:**
- The qualitative commentary prompt must include ALL key numeric outputs as explicit data, not just labels: pass actual ERP value, actual current vs optimal weights, actual Sharpe ratios, actual top-N correlations
- Structure the prompt as: "Given these specific numbers: [data], provide interpretation" -- not "analyze this portfolio"
- Add a consistency check step where Claude is asked to confirm: "Does the following qualitative statement contradict these numbers: [statement] vs [data]?"
- Never allow qualitative narrative to make claims about diversification, risk level, or expected returns without grounding in the actual computed values

**Detection:**
- Qualitative section says "low correlation" while correlation matrix shows high correlation
- Commentary references sectors when the tool has no sector data
- Narrative is identical between very different portfolios (sign that real data was not passed to the prompt)

**Phase:** LLM qualitative layer phase. Define the data-to-prompt contract before writing any commentary templates.

---

## Moderate Pitfalls

### Pitfall 5: Pickle Cache Corruption Breaks Cold Starts for New Users

**What goes wrong:** Users who clone the repo and run it for the first time have no cache. If any of the cache-write code paths fail silently (see `CONCERNS.md`: silent `except Exception: pass`), the tool proceeds but leaves the cache directory in a partially written state. On the next run, the cache loader finds a corrupt or zero-byte pickle file and either crashes or returns None, causing the live fetch path to also be triggered -- potentially hammering the rate-limited yfinance API.

**Prevention:**
- Fix the silent exception swallowing in cache write paths (already flagged in CONCERNS.md) as a prerequisite to the Excel/structured outputs milestone
- Add atomic cache writes: write to `.tmp` file, then rename to final filename (prevents partial writes)
- Add a cache integrity check on load: `try: data = pickle.load(f)` followed by a type assertion, not just existence check
- Document `data_cache/` as user-owned state that can be safely deleted to reset

**Phase:** Can be fixed as a prerequisite cleanup before any new feature phase.

---

### Pitfall 6: Structured Output Schemas Encode Current Pipeline Shape -- Breaking on Future Changes

**What goes wrong:** If Pydantic schemas are written to exactly match today's `results` dict structure (with fields like `method_results`, `comparison`, `performance`), any future change to those dict keys (e.g., adding a new expected return method, renaming a key) silently breaks schema validation or produces incomplete structured outputs.

**Prevention:**
- Keep schemas shallow: validate only the fields the LLM qualitative layer actually needs, not the entire pipeline output
- Use `model_config = ConfigDict(extra='ignore')` so schemas tolerate extra keys added later
- Version the schema: `schema_version: str = "1.0"` field in the root model so breakage is detectable

**Phase:** Structured outputs phase. Write schemas after the pipeline data contracts are confirmed stable.

---

### Pitfall 7: Excel Upload in Cowork is Not a Standard File Path

**What goes wrong:** The current CLAUDE.md workflow assumes the user provides a file path string (e.g., `"path/to/file.csv"`). In Cowork, a user "uploading" a file may provide a temporary path, a drag-and-drop attachment reference, or a path relative to a workspace that Claude cannot resolve via standard `open()` calls.

**Why it happens:** Cowork file handling is environment-specific. A file "uploaded" in a chat may land in a temp directory that Claude's Python execution context cannot access with the path as provided.

**Prevention:**
- Test file path resolution explicitly in the Cowork environment before implementing Excel parsing
- Add path validation as the first step in any file-parsing function: `if not os.path.exists(path): raise FileNotFoundError(f"Cannot find: {path}")`
- Document supported file-provision methods for Cowork users (e.g., "place file in project root and provide relative path") in README
- Do not assume `~/Downloads/portfolio.xlsx` is accessible from Cowork's Python execution context

**Phase:** Excel support phase and Cowork compatibility phase must coordinate on this.

---

### Pitfall 8: Qualitative Commentary Template Hardcodes Investment Advice Framing

**What goes wrong:** LLM commentary templates written during development use phrasing like "You should rebalance to..." or "This allocation is inappropriate for..." These are investment recommendations, not educational analysis. For a public tool distributed on GitHub, this creates legal/compliance exposure.

**Prevention:**
- Establish commentary framing guidelines before writing any LLM prompt templates: use "the optimization suggests..." and "historical analysis indicates..." not "you should..." or "this is too risky"
- Add a disclaimer injection step in `generate_report()` that prepends standard educational-use language
- Review all LLM output templates against a simple test: "Would a compliance officer flag this as investment advice?"

**Phase:** LLM qualitative layer phase. Define framing rules before writing prompts.

---

## Minor Pitfalls

### Pitfall 9: Deprecated pandas `reindex(..., method='ffill')` in New Pipeline Code

**What goes wrong:** The existing bug (CONCERNS.md: `macro_analysis.py` line 242) uses deprecated pandas 2.x API. If any new code added during the Excel or structured output phases copies this pattern (e.g., aligning Excel-sourced data to a price index), the same deprecation warning will appear and eventually break on pandas 3.x.

**Prevention:**
- Fix the existing deprecated call before adding new code that might copy the pattern
- Add a linting note to CONVENTIONS.md: always use `.reindex(index).ffill()` chain, never `reindex(method=...)`

**Phase:** Fix as prerequisite cleanup in first active phase.

---

### Pitfall 10: Windows cp1252 Encoding Breaks When Excel Files Contain Non-ASCII

**What goes wrong:** brokerage-exported Excel files sometimes contain non-ASCII characters in company names (e.g., "Berkshire Hathaway" in some locales, or accented characters in international holdings). openpyxl reads strings as Unicode natively, but if any code path writes these strings to a file using default encoding, Windows cp1252 encoding will raise `UnicodeEncodeError` on characters outside the cp1252 range.

**Prevention:**
- All file writes use `encoding='utf-8'` (already in project conventions -- enforce this for any new report or log output)
- Strip or replace non-ASCII ticker symbols early in the parsing pipeline; they are not valid ticker symbols anyway
- Company names in reports should be treated as display-only strings, not used as dict keys or file paths

**Phase:** Excel support phase.

---

### Pitfall 11: Indefinitely Growing P/E History Pickle Corrupts Over Time

**What goes wrong:** `sp500_pe_history.pkl` appends one entry per run indefinitely (CONCERNS.md). Over many runs, this file grows large. More critically, if openpyxl or pandas is upgraded between runs, the pickle format may be incompatible, causing silent load failures that fall back to stale data with no warning.

**Prevention:**
- Cap the P/E history list at a configurable maximum (e.g., 90 days of daily entries)
- Add a version tag to the pickle payload so mismatches are detectable
- Consider migrating P/E history to a simple CSV append file -- human-readable, not format-sensitive

**Phase:** Can be addressed in any cleanup pass; not blocking for active features.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Excel support | Numeric type coercion (strings vs floats from brokerage exports) | Normalize all numeric fields with `pd.to_numeric(errors='coerce')` before any arithmetic |
| Excel support | Cowork file path resolution for uploaded files | Test path accessibility in Cowork before parsing; document supported file provision method |
| Structured outputs | NumPy/pandas types rejected by Pydantic validation | Add `to_serializable()` normalization utility before any schema validation |
| Structured outputs | Schemas encode current dict shape too tightly | Use `extra='ignore'`, validate only fields the LLM layer needs, add schema version field |
| Cowork compatibility | venv not activated, missing dependencies | Preflight check script; Step 0 in CLAUDE.md workflow |
| LLM qualitative layer | Commentary contradicts quantitative results | Pass all key numeric outputs explicitly in every qualitative prompt |
| LLM qualitative layer | Investment advice framing creates compliance exposure | Define framing guidelines before writing prompt templates |
| Any new phase | Copies deprecated `reindex(method=...)` pattern | Fix existing bug first; add linting note to CONVENTIONS.md |

---

## Sources

- Direct codebase analysis: `.planning/codebase/CONCERNS.md`, `ARCHITECTURE.md`, `INTEGRATIONS.md`, `PROJECT.md`
- openpyxl cell type behavior: established pattern from openpyxl documentation (training data, HIGH confidence)
- Pydantic v2 numpy type handling: established pattern (training data, HIGH confidence)
- Anthropic structured outputs / Cowork Python execution specifics: MEDIUM-LOW confidence; verify actual Cowork behavior during implementation phase
- pandas 2.x deprecation of `reindex(method=...)`: confirmed in CONCERNS.md, pandas changelog (HIGH confidence)
- LLM hallucination in grounded generation tasks: well-documented pattern (HIGH confidence)
