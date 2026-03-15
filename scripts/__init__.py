"""
PortfolioAnalysis-Public: Portfolio optimization and US macro analysis toolkit.

Modules:
    parse_portfolio - Parse portfolio CSVs (generic, E-Trade, Schwab formats)
    market_data     - Download and cache historical price data via yfinance
    macro_analysis  - Key economic indicators from FRED (rates, employment, inflation, growth)
    optimize        - Portfolio optimization using pyportfolioopt (3 methods)
    visualize       - Generate matplotlib charts (PNGs)
    report          - Generate markdown summary reports
"""

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
