"""
US Macro Analysis - Equity Risk Premium Calculator
===================================================
Calculates ERP using the Fed Model approach:
    ERP = Earnings Yield - 10-Year Treasury Yield
    where Earnings Yield = (1 / P/E Ratio) x 100

Data Sources:
- 10-Year Treasury Yield: FRED (DGS10 - Daily)
- S&P 500 Trailing P/E: Multpl.com (web scrape)
"""

import pandas as pd
import numpy as np
from pandas_datareader import data as pdr
import requests
from bs4 import BeautifulSoup
import re
import os
import pickle
import datetime
from datetime import timedelta
from pathlib import Path
import time


DEFAULT_CACHE_DIR = 'data_cache'
FRED_CACHE_TTL_HOURS = 4
PE_CACHE_TTL_HOURS = 12

MULTPL_PE_URL = 'https://www.multpl.com/s-p-500-pe-ratio'


def get_macro_context(cache_dir=DEFAULT_CACHE_DIR):
    """
    Get current macro context: ERP, Treasury yield, P/E, interpretation.

    Parameters
    ----------
    cache_dir : str
        Directory for pickle cache files.

    Returns
    -------
    dict
        {
            'pe_ratio': float,
            'earnings_yield': float,
            'treasury_yield': float,
            'erp': float,
            'interpretation': str,
            'stats': dict,
            'erp_history': pd.DataFrame or None
        }
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    print("Fetching macro data...")

    # Fetch data
    pe_ratio = fetch_sp500_pe(cache_path)
    treasury_df = fetch_treasury_yield(cache_path)

    if pe_ratio is None:
        print("  [ERROR] Could not fetch P/E ratio")
        return _empty_result("P/E ratio unavailable")

    if treasury_df.empty:
        print("  [ERROR] Could not fetch Treasury yield")
        return _empty_result("Treasury yield unavailable")

    # Current treasury yield
    treasury_yield = treasury_df.iloc[-1, 0]
    if pd.isna(treasury_yield):
        treasury_df = treasury_df.ffill()
        treasury_yield = treasury_df.iloc[-1, 0]

    # Calculate ERP
    earnings_yield = (1 / pe_ratio) * 100
    erp = earnings_yield - treasury_yield

    # Track P/E history for trend analysis
    _add_to_pe_history(pe_ratio, cache_path)

    # Build historical timeseries
    erp_df = _build_erp_timeseries(treasury_df, cache_path)
    stats = _calculate_stats(erp_df)

    # Generate interpretation
    interpretation = _get_interpretation(erp, stats)

    print(f"\n  Macro Analysis Results:")
    print(f"    S&P 500 P/E Ratio:      {pe_ratio:>8.2f}")
    print(f"    Earnings Yield:          {earnings_yield:>8.2f}%")
    print(f"    10Y Treasury Yield:      {treasury_yield:>8.2f}%")
    print(f"    Equity Risk Premium:     {erp:>8.2f}%")
    print(f"    Interpretation: {interpretation}")

    return {
        'pe_ratio': pe_ratio,
        'earnings_yield': earnings_yield,
        'treasury_yield': treasury_yield,
        'erp': erp,
        'interpretation': interpretation,
        'stats': stats,
        'erp_history': erp_df
    }


def fetch_treasury_yield(cache_path, start_date='2000-01-01'):
    """
    Fetch 10-Year Treasury Yield from FRED (DGS10 daily rate).

    Parameters
    ----------
    cache_path : Path
        Cache directory.
    start_date : str
        How far back to fetch.

    Returns
    -------
    pd.DataFrame
        Treasury yield timeseries.
    """
    cache_file = cache_path / 'treasury_DGS10.pkl'

    # Check cache
    cached = _load_cache(cache_file, FRED_CACHE_TTL_HOURS)
    if cached is not None:
        print(f"  [OK] Treasury yield from cache")
        return cached

    print("  -> Fetching Treasury yield from FRED...")
    try:
        data = pdr.get_data_fred('DGS10', start=start_date)
        if data.empty:
            raise ValueError("No data returned")
        data = data.ffill()  # Fill weekends/holidays
        _save_cache(cache_file, data)
        print(f"  [OK] Treasury yield ({len(data)} data points)")
        return data
    except Exception as e:
        print(f"  [FAILED] FRED fetch: {e}")
        # Try loading stale cache as fallback
        stale = _load_cache(cache_file, max_age_hours=None)
        if stale is not None:
            print(f"  [FALLBACK] Using stale cache")
            return stale
        return pd.DataFrame()


def fetch_sp500_pe(cache_path, max_retries=3):
    """
    Fetch current S&P 500 trailing P/E from Multpl.com.

    Parameters
    ----------
    cache_path : Path
        Cache directory.
    max_retries : int
        Number of retry attempts.

    Returns
    -------
    float or None
        Current P/E ratio.
    """
    cache_file = cache_path / 'multpl_pe.pkl'

    # Check cache
    cached = _load_cache(cache_file, PE_CACHE_TTL_HOURS)
    if cached is not None:
        print(f"  [OK] P/E ratio from cache: {cached:.2f}")
        return cached

    print("  -> Fetching P/E ratio from Multpl.com...")

    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36')
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(MULTPL_PE_URL, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            current_div = soup.find('div', {'id': 'current'})

            if current_div:
                div_text = current_div.get_text()
                pe_match = re.search(r':\s*([\d.]+)', div_text)
                if pe_match:
                    pe = float(pe_match.group(1))
                    if 5 < pe < 100:  # Sanity check
                        print(f"  [OK] P/E ratio: {pe:.2f} (Multpl.com)")
                        _save_cache(cache_file, pe)
                        return pe

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  [RETRY] Request failed, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [WARN] Web scrape failed: {e}")
        except Exception as e:
            print(f"  [WARN] Parse error: {e}")

    # Fallback to P/E history
    pe_history = _load_pe_history(cache_path)
    if pe_history:
        last_pe = pe_history[-1]['pe_ratio']
        print(f"  [FALLBACK] Using cached P/E: {last_pe:.2f}")
        return last_pe

    print("  [FAILED] Unable to fetch P/E ratio")
    return None


def _build_erp_timeseries(treasury_df, cache_path):
    """Build ERP timeseries from treasury yields and P/E history."""
    if treasury_df.empty:
        return pd.DataFrame()

    pe_history = _load_pe_history(cache_path)
    if not pe_history:
        return pd.DataFrame()

    pe_df = pd.DataFrame(pe_history)
    pe_df['date'] = pd.to_datetime(pe_df['date'])
    pe_df = pe_df.sort_values('date').set_index('date')

    treasury_aligned = treasury_df.loc[treasury_df.index >= pe_df.index.min()]
    if treasury_aligned.empty:
        return pd.DataFrame()

    pe_aligned = pe_df['pe_ratio'].reindex(treasury_aligned.index).ffill()
    earnings_yield = (1 / pe_aligned) * 100
    treasury_values = treasury_aligned.iloc[:, 0]
    erp = earnings_yield - treasury_values

    result = pd.DataFrame({
        'earnings_yield': earnings_yield,
        'treasury_yield': treasury_values,
        'erp': erp
    })

    return result.dropna()


def _calculate_stats(erp_df):
    """Calculate historical ERP statistics."""
    if erp_df.empty or 'erp' not in erp_df.columns:
        return {}

    erp_series = erp_df['erp']
    stats = {
        'mean': erp_series.mean(),
        'median': erp_series.median(),
        'std': erp_series.std(),
        'min': erp_series.min(),
        'max': erp_series.max(),
        'p25': erp_series.quantile(0.25),
        'p75': erp_series.quantile(0.75),
    }

    if len(erp_series) > 0:
        current = erp_series.iloc[-1]
        stats['current'] = current
        stats['percentile'] = (erp_series <= current).sum() / len(erp_series) * 100

    return stats


def _get_interpretation(erp_value, stats):
    """Generate plain-English interpretation of ERP."""
    if erp_value is None or not stats:
        return "Insufficient historical data for comparison"

    pct = stats.get('percentile', 50)

    if pct < 25:
        return (f"Low ({pct:.0f}th percentile) - Stocks appear expensive "
                "relative to bonds. Expect lower forward equity returns.")
    elif pct < 50:
        return (f"Below average ({pct:.0f}th percentile) - Stocks slightly "
                "expensive vs. historical norms.")
    elif pct < 75:
        return (f"Above average ({pct:.0f}th percentile) - Stocks fairly "
                "valued relative to bonds.")
    else:
        return (f"High ({pct:.0f}th percentile) - Stocks appear attractive "
                "relative to bonds. Higher expected forward returns.")


def _add_to_pe_history(pe_ratio, cache_path):
    """Append current P/E to history."""
    history = _load_pe_history(cache_path)
    history.append({
        'date': datetime.datetime.now(),
        'pe_ratio': pe_ratio
    })
    hist_file = cache_path / 'sp500_pe_history.pkl'
    try:
        with open(hist_file, 'wb') as f:
            pickle.dump(history, f)
    except Exception as e:
        print(f"  [WARN] PE history save failed: {e}")


def _load_pe_history(cache_path):
    """Load P/E history from cache."""
    hist_file = cache_path / 'sp500_pe_history.pkl'
    if hist_file.exists():
        try:
            with open(hist_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"  [WARN] PE history load failed: {e}")
    return []


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


def _empty_result(reason):
    """Return empty result dict with error message."""
    return {
        'pe_ratio': None,
        'earnings_yield': None,
        'treasury_yield': None,
        'erp': None,
        'interpretation': reason,
        'stats': {},
        'erp_history': pd.DataFrame()
    }


if __name__ == '__main__':
    result = get_macro_context()
    if result['erp'] is not None:
        print(f"\nERP: {result['erp']:.2f}%")
        print(f"Interpretation: {result['interpretation']}")
