"""
Market Data Downloader
======================
Downloads historical price data from Yahoo Finance with:
- Sequential downloads to avoid rate limiting
- Pickle-based caching with configurable TTL
- Coverage reporting and validation
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
import pickle
import datetime
import time
from pathlib import Path


DEFAULT_CACHE_DIR = 'data_cache'
DEFAULT_CACHE_TTL_HOURS = 4


def download_prices(tickers, start_date='2020-01-01', benchmark='VTI',
                    cache_dir=DEFAULT_CACHE_DIR, delay=3):
    """
    Download historical close prices for a list of tickers.

    Parameters
    ----------
    tickers : list of str
        Ticker symbols to download.
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    benchmark : str
        Benchmark ticker for CAPM calculations.
    cache_dir : str
        Directory for pickle cache files.
    delay : int
        Seconds between downloads to avoid rate limiting.

    Returns
    -------
    dict
        {
            'prices': pd.DataFrame (columns=tickers, index=dates),
            'benchmark': pd.Series,
            'failed': list of str,
            'coverage': dict (ticker -> float pct)
        }
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Check cache
    cache_file = cache_path / _cache_key(tickers, start_date)
    cached = _load_cache(cache_file)
    if cached is not None:
        print(f"  [OK] Loaded {len(cached['prices'].columns)} tickers from cache")
        return cached

    print(f"Downloading price data for {len(tickers)} securities...")
    print(f"  Start date: {start_date}")
    print(f"  Benchmark: {benchmark}")
    print(f"  Estimated time: ~{len(tickers) * delay} seconds\n")

    series_list = []
    failed = []

    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{len(tickers)}] {ticker}...", end=' ')

        try:
            data = yf.download(ticker, start=start_date, auto_adjust=True,
                               progress=False)
            if not data.empty and 'Close' in data.columns:
                close = data['Close']
                # Handle MultiIndex columns from newer yfinance
                if hasattr(close, 'columns'):
                    close = close.iloc[:, 0]
                close.name = ticker
                series_list.append(close)
                print(f"[OK] ({len(data)} days)")
            else:
                failed.append(ticker)
                print("[FAILED] No data")
        except Exception as e:
            failed.append(ticker)
            print(f"[FAILED] {str(e)[:50]}")

        if i < len(tickers):
            time.sleep(delay)

    if not series_list:
        raise ValueError("All downloads failed. Check tickers or try again later.")

    # Combine into DataFrame
    prices = pd.concat(series_list, axis=1)
    prices = prices.dropna(how='all')

    # Download benchmark
    print(f"\n  [Benchmark] {benchmark}...", end=' ')
    time.sleep(delay)

    try:
        bench_data = yf.download(benchmark, start=start_date, auto_adjust=True,
                                 progress=False)
        if bench_data.empty:
            raise ValueError("Benchmark download returned empty")
        benchmark_prices = bench_data['Close']
        if hasattr(benchmark_prices, 'columns'):
            benchmark_prices = benchmark_prices.iloc[:, 0]
        print(f"[OK] ({len(bench_data)} days)")
    except Exception as e:
        raise ValueError(f"Benchmark download failed: {e}")

    # Coverage report
    print(f"\n  Data Summary:")
    print(f"  Successfully downloaded: {len(series_list)} securities")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"  Date range: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"  Data points: {len(prices):,} days")

    coverage = {}
    for ticker in prices.columns:
        cov_pct = (1 - prices[ticker].isna().sum() / len(prices)) * 100
        coverage[ticker] = cov_pct
        status = "[OK]" if cov_pct > 95 else "[WARN]"
        print(f"    {status} {ticker}: {cov_pct:.1f}%")

    result = {
        'prices': prices,
        'benchmark': benchmark_prices,
        'failed': failed,
        'coverage': coverage
    }

    # Save to cache
    _save_cache(cache_file, result)

    return result


def _cache_key(tickers, start_date):
    """Generate cache filename from tickers and start date."""
    ticker_hash = '_'.join(sorted(tickers))[:100]
    return f"prices_{ticker_hash}_{start_date}.pkl"


def _load_cache(cache_file):
    """Load from cache if fresh."""
    if not cache_file.exists():
        return None
    try:
        mtime = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.datetime.now() - mtime
        if age > datetime.timedelta(hours=DEFAULT_CACHE_TTL_HOURS):
            return None
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
            print(f"  Cache hit ({mtime.strftime('%m/%d %H:%M')})")
            return data
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
    # Quick test
    result = download_prices(['AAPL', 'MSFT', 'VTI'], start_date='2023-01-01')
    print(f"\nPrices shape: {result['prices'].shape}")
    print(f"Failed: {result['failed']}")
