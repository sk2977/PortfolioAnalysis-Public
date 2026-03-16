"""
Key Economic Indicators from FRED
==================================
Fetches and caches key US economic indicators from the Federal Reserve
Economic Data (FRED) API via pandas-datareader:
- Interest Rates: BBB Corporate Bonds, Fed Funds Rate, 10Y Treasury
- Employment: Unemployment Rate
- Inflation: Consumer Price Index (CPI)
- Growth: GDP, Corporate Profits After Tax
- Markets: S&P 500

Data Sources:
- All indicators: FRED (Federal Reserve Bank of St. Louis)
"""

import pandas as pd
import numpy as np
from pandas_datareader import data as pdr
import os
import pickle
import datetime
from datetime import timedelta
from pathlib import Path


DEFAULT_CACHE_DIR = 'data_cache'
DEFAULT_CACHE_TTL_HOURS = 4

FRED_SYMBOLS = {
    'bbb_yield': 'BAMLC0A4CBBBEY',
    'fed_funds': 'FEDFUNDS',
    'ten_year': 'GS10',
    'unemployment': 'UNRATE',
    'inflation': 'CPIAUCSL',
    'gdp': 'GDP',
    'corporate_profits': 'CPATAX',
    'sp500': 'SP500',
}

INDICATOR_META = {
    'bbb_yield':         ('Interest Rates', 'BBB Corporate Bonds', '%'),
    'fed_funds':         ('Interest Rates', 'Fed Funds Rate', '%'),
    'ten_year':          ('Interest Rates', '10Y Treasury', '%'),
    'unemployment':      ('Employment', 'Unemployment Rate', '%'),
    'inflation':         ('Inflation', 'Consumer Price Index', 'Index'),
    'gdp':               ('Growth', 'GDP', '$B'),
    'corporate_profits': ('Markets', 'Corporate Profits', '$B'),
    'sp500':             ('Markets', 'S&P 500', 'Index'),
}


def get_macro_context(cache_dir=DEFAULT_CACHE_DIR, start_date='2022-01-01'):
    """
    Fetch key US economic indicators from FRED.

    Parameters
    ----------
    cache_dir : str
        Directory for pickle cache files.
    start_date : str
        How far back to fetch data (YYYY-MM-DD).

    Returns
    -------
    dict
        {
            'indicators': dict of name -> {value, yoy, date, symbol},
            'summary_df': pd.DataFrame with columns
                          [Category, Indicator, Value, Unit, YoY%, Date],
            'data': dict of name -> pd.DataFrame (raw timeseries),
            'interpretation': str
        }
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    print("Fetching economic indicators from FRED...")

    data_dict = {}
    indicators = {}
    summary_rows = []

    for name, symbol in FRED_SYMBOLS.items():
        df = _fetch_indicator(symbol, cache_path, start_date)
        data_dict[name] = df

        if df.empty:
            indicators[name] = {
                'value': None, 'yoy': None,
                'date': None, 'symbol': symbol,
            }
            continue

        current_value = float(df.iloc[-1, 0])
        last_date = df.index[-1].strftime('%Y-%m-%d')
        yoy = _calculate_yoy_change(df)

        indicators[name] = {
            'value': current_value,
            'yoy': yoy,
            'date': last_date,
            'symbol': symbol,
        }

        category, label, unit = INDICATOR_META[name]
        summary_rows.append({
            'Category': category,
            'Indicator': label,
            'Value': f"{current_value:.2f}",
            'Unit': unit,
            'YoY%': f"{yoy:+.2f}" if yoy is not None else 'N/A',
            'Date': last_date,
        })

    summary_df = pd.DataFrame(summary_rows)

    # Print summary
    print(f"\n  Economic Indicators Summary:")
    for name, info in indicators.items():
        if info['value'] is not None:
            _, label, unit = INDICATOR_META[name]
            yoy_str = f"YoY: {info['yoy']:+.2f}%" if info['yoy'] is not None else ""
            print(f"    {label:.<30} {info['value']:>10.2f} {unit:<5}  {yoy_str}")
        else:
            _, label, _ = INDICATOR_META[name]
            print(f"    {label:.<30} [FAILED]")

    interpretation = _generate_interpretation(indicators)
    print(f"  Interpretation: {interpretation}")

    return {
        'indicators': indicators,
        'summary_df': summary_df,
        'data': data_dict,
        'interpretation': interpretation,
    }


def _fetch_indicator(symbol, cache_path, start_date, max_retries=3):
    """
    Fetch a single FRED indicator with caching.

    Parameters
    ----------
    symbol : str
        FRED series ID (e.g. 'GS10').
    cache_path : Path
        Cache directory.
    start_date : str
        Start date for data fetch.
    max_retries : int
        Number of retry attempts.

    Returns
    -------
    pd.DataFrame
        Timeseries data, or empty DataFrame on failure.
    """
    cache_file = cache_path / f'fred_{symbol}.pkl'

    # Check cache
    cached = _load_cache(cache_file, DEFAULT_CACHE_TTL_HOURS)
    if cached is not None:
        mtime = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
        print(f"  [OK] {symbol} from cache ({mtime.strftime('%m/%d %H:%M')})")
        return cached

    print(f"  -> Fetching {symbol} from FRED...", end=' ')
    for attempt in range(max_retries):
        try:
            data = pdr.get_data_fred(symbol, start=start_date)
            if data.empty:
                raise ValueError(f"No data for {symbol}")
            _save_cache(cache_file, data)
            print(f"[OK] ({len(data)} points)")
            return data
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[FAILED] {str(e)[:60]}")

    # Try stale cache as fallback
    stale = _load_cache(cache_file, max_age_hours=None)
    if stale is not None:
        print(f"  [WARN] Using stale cache for {symbol}")
        return stale

    return pd.DataFrame()


def _calculate_yoy_change(data):
    """
    Calculate year-over-year percentage change for the most recent data point.

    Parameters
    ----------
    data : pd.DataFrame
        Timeseries with a single column.

    Returns
    -------
    float or None
        YoY change as percentage, or None if insufficient data.
    """
    if data.empty or len(data) < 2:
        return None

    freq = pd.infer_freq(data.index)
    periods = 4 if freq and freq.startswith('Q') else 12

    if len(data) <= periods:
        return None

    yoy = data.pct_change(periods=periods).iloc[-1, 0] * 100
    if np.isnan(yoy):
        return None
    return float(yoy)


def _generate_interpretation(indicators):
    """
    Generate plain-English interpretation from current indicator values.

    Parameters
    ----------
    indicators : dict
        Mapping of name -> {value, yoy, date, symbol}.

    Returns
    -------
    str
        Brief interpretation of the economic environment.
    """
    parts = []

    fed = indicators.get('fed_funds', {})
    ten_yr = indicators.get('ten_year', {})
    if fed.get('value') is not None and ten_yr.get('value') is not None:
        spread = ten_yr['value'] - fed['value']
        if spread < 0:
            parts.append(f"Yield curve inverted (10Y-FF spread: {spread:+.2f}pp)")
        else:
            parts.append(f"Yield curve normal (10Y-FF spread: {spread:+.2f}pp)")

    unemp = indicators.get('unemployment', {})
    if unemp.get('value') is not None:
        rate = unemp['value']
        if rate < 4.0:
            parts.append(f"Tight labor market ({rate:.1f}%)")
        elif rate < 5.5:
            parts.append(f"Moderate unemployment ({rate:.1f}%)")
        else:
            parts.append(f"Elevated unemployment ({rate:.1f}%)")

    infl = indicators.get('inflation', {})
    if infl.get('yoy') is not None:
        yoy = infl['yoy']
        if yoy > 4.0:
            parts.append(f"Inflation elevated ({yoy:.1f}% YoY)")
        elif yoy > 2.5:
            parts.append(f"Inflation above target ({yoy:.1f}% YoY)")
        else:
            parts.append(f"Inflation near target ({yoy:.1f}% YoY)")

    if not parts:
        return "Insufficient data for interpretation"

    return ". ".join(parts) + "."


def _load_cache(cache_file, max_age_hours):
    """Load pickle cache if still fresh."""
    if not cache_file.exists():
        return None
    try:
        if max_age_hours is not None:
            mtime = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.datetime.now() - mtime
            if age > timedelta(hours=max_age_hours):
                return None
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  [WARN] Cache load failed: {e}")
        return None


def _save_cache(cache_file, data):
    """Save data to pickle cache."""
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"  [WARN] Cache save failed: {e}")


if __name__ == '__main__':
    result = get_macro_context()
    print(f"\n{result['summary_df'].to_string(index=False)}")
