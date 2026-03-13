# Conventions

## Code Style

- **Python 3.x**, no type annotations used
- **Docstrings**: NumPy-style with Parameters/Returns sections on all public functions
- **Imports**: stdlib first, then third-party, no relative imports
- **Line length**: No enforced limit, generally ~80-100 chars
- **No linter/formatter** configured (no pyproject.toml, no ruff/black/flake8)

## Naming Patterns

- Public functions: `verb_noun` pattern (e.g., `parse_csv`, `download_prices`, `optimize_portfolio`, `generate_report`)
- Private helpers: `_verb_noun` (e.g., `_detect_format`, `_load_cache`, `_run_single_optimization`)
- Constants: `UPPER_SNAKE_CASE` at module top level
- Dict keys: `snake_case` strings (e.g., `'risk_free_rate'`, `'format_detected'`)

## Error Handling

- **Console output**: `[OK]`, `[ERROR]`, `[WARN]`, `[FAILED]`, `[SKIP]`, `[RETRY]`, `[FALLBACK]` -- never Unicode/emoji
- **Try/except**: Broad `except Exception` used frequently, with user-friendly messages
- **Silent failures**: Cache operations silently swallow exceptions (`except Exception: pass`)
- **Fallback chains**: Multiple fallback paths (fresh fetch -> stale cache -> history -> None)
- **Validation**: `ValueError` raised for critical failures (no tickers found, all downloads failed)

## Function Signatures

- All public functions accept keyword arguments with sensible defaults
- Configuration passed as plain dicts, not classes or dataclasses
- Return values are always dicts with string keys
- Optional parameters use `None` default with internal defaulting

## Console Output

- Progress reporting during long operations (download progress, optimization steps)
- Indented with 2 spaces for sub-operations
- Format: `  [STATUS] Message` pattern throughout
- Windows cp1252 safe -- ASCII only in all print statements

## File I/O

- All reads/writes use `encoding='utf-8'` parameter
- Paths handled via `pathlib.Path` (most modules) or string paths
- Directories created with `mkdir(parents=True, exist_ok=True)`
- Charts saved at 150 DPI as PNG with `bbox_inches='tight'`

## Data Patterns

- **pandas-centric**: DataFrames and Series are the primary data structures
- **Dict contracts**: All module boundaries use plain dicts
- **No classes**: Entire codebase is functional -- no OOP, no classes, no inheritance
- **Immutable inputs**: Functions don't mutate input data (create new DataFrames/Series)

## Dependencies

- No dependency management beyond `requirements.txt`
- No virtual environment config committed (user creates their own)
- No pinned versions -- uses `>=` minimum version constraints
- `python-dotenv` listed but unused in actual code
