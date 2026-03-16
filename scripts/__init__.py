"""
scripts -- thin proxy package that re-exports from .claude/skills/portfolio-analysis/scripts/.

The canonical source code lives in the skill directory. This package exists so that
tests and CLAUDE.md can use `from scripts.X import ...` while the skill owns the code.
"""

import importlib
import sys
from pathlib import Path

# Resolve the skill's scripts directory
_SKILL_SCRIPTS = str(
    Path(__file__).resolve().parent.parent
    / '.claude' / 'skills' / 'portfolio-analysis' / 'scripts'
)
if _SKILL_SCRIPTS not in sys.path:
    sys.path.insert(0, _SKILL_SCRIPTS)

# ---------------------------------------------------------------------------
# Preflight check (tested by test_cowk.py)
# ---------------------------------------------------------------------------

_REQUIRED_PACKAGES = [
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('matplotlib', 'matplotlib'),
    ('seaborn', 'seaborn'),
    ('yfinance', 'yfinance'),
    ('pypfopt', 'pyportfolioopt'),
    ('pandas_datareader', 'pandas-datareader'),
    ('sklearn', 'scikit-learn'),
    ('openpyxl', 'openpyxl'),
    ('pydantic', 'pydantic'),
]


def _preflight_check():
    missing = []
    for import_name, pip_name in _REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        for pkg in missing:
            print(f"[ERROR] Missing: {pkg}. Run: pip install -r requirements.txt")
        raise SystemExit(1)


_preflight_check()

# ---------------------------------------------------------------------------
# Eagerly register skill submodules as scripts.X in sys.modules
# ---------------------------------------------------------------------------

_SUBMODULES = [
    'parse_portfolio', 'market_data', 'macro_analysis',
    'optimize', 'schemas', 'visualize', 'report',
]

for _name in _SUBMODULES:
    _mod = importlib.import_module(_name)
    sys.modules[f'scripts.{_name}'] = _mod
    globals()[_name] = _mod
