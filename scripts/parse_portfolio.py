"""
Portfolio CSV Parser
====================
Parses portfolio holdings from CSV files in multiple formats:
- Generic: Symbol, Shares, Price (or Symbol, Weight%)
- E-Trade: PortfolioDownload.csv export
- Schwab: Positions export

Returns normalized portfolio data for optimization.
"""

import os
import pandas as pd
import numpy as np
import re
import yfinance as yf
import time


def parse_csv(file_path, exclude_tickers=None):
    """
    Parse portfolio from CSV file. Auto-detects format.

    Parameters
    ----------
    file_path : str
        Path to CSV file.
    exclude_tickers : list, optional
        Tickers to exclude from analysis.

    Returns
    -------
    dict
        {
            'tickers': list of str,
            'allocations': pd.Series (index=ticker, values=weight 0-1),
            'raw_data': pd.DataFrame,
            'format_detected': str
        }
    """
    if exclude_tickers is None:
        exclude_tickers = []

    # Read raw to detect format.  E-Trade exports have multi-section
    # headers with different column counts, so pd.read_csv may fail.
    try:
        raw = pd.read_csv(file_path, nrows=15, dtype=str, encoding='utf-8')
    except (pd.errors.ParserError, Exception):
        raw = pd.DataFrame()  # empty DF; _detect_format falls back to line scan
    fmt = _detect_format(raw, file_path)
    print(f"  Detected CSV format: {fmt}")

    if fmt == 'etrade':
        return _parse_etrade(file_path, exclude_tickers)
    elif fmt == 'schwab':
        return _parse_schwab(file_path, exclude_tickers)
    else:
        return _parse_generic(file_path, exclude_tickers)


def _detect_format(df, file_path):
    """Detect CSV format from headers and content."""
    cols = [c.strip().lower() for c in df.columns]

    # E-Trade: has many columns, often starts with junk rows
    # Check if file has >10 skiprows of header content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:15]
        for line in lines:
            if 'e*trade' in line.lower() or 'etrade' in line.lower():
                return 'etrade'
            if '% of portfolio' in line.lower():
                return 'etrade'
    except Exception as e:
        print(f"  [WARN] Format detection read failed: {e}")

    # Schwab: typically has "Symbol", "Description", "Quantity", "Price", "Market Value"
    if 'description' in cols and 'market value' in cols:
        return 'schwab'

    return 'generic'


def _detect_format_from_df(df):
    """
    Detect broker format from a DataFrame's column names.
    Unlike _detect_format(), this does not open any files.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with column names already stripped.

    Returns
    -------
    str
        One of: 'etrade', 'schwab', 'generic'
    """
    cols_lower = [c.strip().lower() for c in df.columns]

    # E-Trade signal: any column containing '% of portfolio'
    if any('% of portfolio' in c for c in cols_lower):
        return 'etrade'

    # Schwab signal: has both 'description' and 'market value'
    if 'description' in cols_lower and 'market value' in cols_lower:
        return 'schwab'

    return 'generic'


def _parse_generic_df(df, exclude_tickers, format_label='generic'):
    """
    Parse a generic-format DataFrame into a portfolio dict.
    Shared logic for both CSV and Excel generic parsing.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns already stripped.
    exclude_tickers : list
        Tickers to exclude.
    format_label : str
        Value to set in 'format_detected' field of returned dict.

    Returns
    -------
    dict
        Standard portfolio dict.
    """
    # Find symbol column
    symbol_col = _find_column(df, ['symbol', 'ticker', 'stock', 'name'])
    if symbol_col is None:
        raise ValueError("Cannot find symbol/ticker column. "
                         "Expected column named: Symbol, Ticker, or Stock")

    # Find quantity or weight column
    shares_col = _find_column(df, ['shares', 'quantity', 'qty', 'units'])
    weight_col = _find_column(df, ['weight', 'allocation', 'alloc', '% of portfolio', 'pct'])
    price_col = _find_column(df, ['price', 'last price', 'current price', 'close'])

    tickers = []
    values = []
    use_weights = shares_col is None and weight_col is not None

    for _, row in df.iterrows():
        symbol = str(row[symbol_col]).strip().upper()

        # Skip invalid rows
        if not symbol or symbol in ('NAN', '', 'CASH', 'TOTAL') or len(symbol) > 10:
            continue
        if _is_option(symbol):
            print(f"  Filtered out option/derivative: {symbol}")
            continue
        if symbol in [t.upper() for t in exclude_tickers]:
            print(f"  User excluded: {symbol}")
            continue

        if use_weights:
            try:
                val = float(str(row[weight_col]).replace('%', '').replace(',', ''))
                if val > 0:
                    tickers.append(symbol)
                    values.append(val)
            except (ValueError, TypeError):
                continue
        elif shares_col is not None:
            try:
                shares = float(str(row[shares_col]).replace(',', ''))
                if price_col:
                    price = float(str(row[price_col]).replace('$', '').replace(',', ''))
                    val = shares * price
                else:
                    val = shares  # Use share count as proxy
                if val > 0:
                    tickers.append(symbol)
                    values.append(val)
            except (ValueError, TypeError):
                continue

    if not tickers:
        raise ValueError("No valid tickers found!")

    # Normalize to weights summing to 1.0
    total = sum(values)
    allocations = pd.Series([v / total for v in values], index=tickers)
    raw_data = pd.DataFrame({'ticker': tickers, 'allocation': allocations.values})

    print(f"  Loaded {len(tickers)} securities: {', '.join(tickers)}")

    return {
        'tickers': tickers,
        'allocations': allocations,
        'raw_data': raw_data,
        'format_detected': format_label
    }


def _parse_schwab_df(df, exclude_tickers):
    """
    Parse a Schwab-format DataFrame into a portfolio dict.
    Shared logic for both CSV and Excel Schwab parsing.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns already stripped.
    exclude_tickers : list
        Tickers to exclude.

    Returns
    -------
    dict
        Standard portfolio dict with format_detected='schwab'.
    """
    symbol_col = _find_column(df, ['symbol'])
    qty_col = _find_column(df, ['quantity', 'shares'])
    mv_col = _find_column(df, ['market value'])

    if symbol_col is None:
        raise ValueError("Cannot find Symbol column in Schwab data")

    tickers = []
    values = []

    for _, row in df.iterrows():
        symbol = str(row[symbol_col]).strip().upper()

        if not symbol or symbol in ('NAN', '', 'CASH', 'TOTAL', 'ACCOUNT TOTAL'):
            continue
        if len(symbol) > 10 or _is_option(symbol):
            continue
        if symbol in [t.upper() for t in exclude_tickers]:
            print(f"  User excluded: {symbol}")
            continue

        try:
            if mv_col:
                val = float(str(row[mv_col]).replace('$', '').replace(',', ''))
            elif qty_col:
                val = float(str(row[qty_col]).replace(',', ''))
            else:
                continue

            if val > 0:
                tickers.append(symbol)
                values.append(val)
        except (ValueError, TypeError):
            continue

    if not tickers:
        raise ValueError("No valid tickers found in Schwab data!")

    total = sum(values)
    alloc_series = pd.Series([v / total for v in values], index=tickers)
    raw_data = pd.DataFrame({'ticker': tickers, 'allocation': alloc_series.values})

    print(f"  Loaded {len(tickers)} securities: {', '.join(tickers)}")

    return {
        'tickers': tickers,
        'allocations': alloc_series,
        'raw_data': raw_data,
        'format_detected': 'schwab'
    }


def _parse_generic(file_path, exclude_tickers):
    """
    Parse generic CSV with columns like Symbol, Shares, Price or Symbol, Weight%.
    Thin wrapper around _parse_generic_df().
    """
    df = pd.read_csv(file_path, dtype=str, encoding='utf-8')
    df.columns = [c.strip() for c in df.columns]
    return _parse_generic_df(df, exclude_tickers)


def _parse_etrade(file_path, exclude_tickers):
    """Parse E-Trade PortfolioDownload.csv format."""
    # E-Trade CSVs have ~10 header rows before data
    df = pd.read_csv(file_path, skiprows=10, dtype=str,
                     on_bad_lines='skip', encoding='utf-8')

    symbol_col = df.columns[0]
    allocation_col = df.columns[4]  # "% of Portfolio"

    tickers = []
    allocations = []
    options_pattern = r'(Call|Put|call|put|\d{2}\s\'\d{2}|Option)'

    for _, row in df.iterrows():
        symbol = str(row[symbol_col]).strip()
        alloc_str = str(row[allocation_col]).strip()

        # Stop at footer rows
        if (symbol.upper() in ['CASH', 'TOTAL', 'NAN', ''] or
                'GENERATED' in symbol.upper()):
            break

        if len(symbol) > 10:
            continue

        # Filter options
        if re.search(options_pattern, symbol):
            print(f"  Filtered out option: {symbol}")
            continue

        if symbol.upper() in [t.upper() for t in exclude_tickers]:
            print(f"  User excluded: {symbol}")
            continue

        try:
            val = float(alloc_str.replace('%', '').replace(',', ''))
            if val > 0:
                tickers.append(symbol)
                allocations.append(val)
        except (ValueError, AttributeError):
            continue

    if not tickers:
        raise ValueError("No valid tickers found in E-Trade CSV!")

    total = sum(allocations)
    alloc_series = pd.Series([a / total for a in allocations], index=tickers)
    raw_data = pd.DataFrame({'ticker': tickers, 'allocation': alloc_series.values})

    print(f"  Loaded {len(tickers)} securities: {', '.join(tickers)}")

    return {
        'tickers': tickers,
        'allocations': alloc_series,
        'raw_data': raw_data,
        'format_detected': 'etrade'
    }


def _parse_schwab(file_path, exclude_tickers):
    """
    Parse Schwab positions export format.
    Thin wrapper around _parse_schwab_df().
    """
    df = pd.read_csv(file_path, dtype=str, encoding='utf-8')
    df.columns = [c.strip() for c in df.columns]
    return _parse_schwab_df(df, exclude_tickers)


def parse_excel(file_path, exclude_tickers=None, sheet_name=0):
    """
    Parse portfolio from Excel (.xlsx) file. Auto-detects broker format.

    Parameters
    ----------
    file_path : str
        Path to .xlsx file.
    exclude_tickers : list, optional
        Tickers to exclude from analysis.
    sheet_name : int or str, optional
        Sheet to read (default 0 = first sheet).

    Returns
    -------
    dict
        {
            'tickers': list of str,
            'allocations': pd.Series (index=ticker, values=weight 0-1),
            'raw_data': pd.DataFrame,
            'format_detected': str
        }

    Raises
    ------
    FileNotFoundError
        If file_path does not exist.
    """
    if exclude_tickers is None:
        exclude_tickers = []
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot find file: {file_path}")
    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]
    fmt = _detect_format_from_df(df)
    print(f"  Detected Excel format: {fmt}")
    if fmt == 'etrade':
        print("  [WARN] E-Trade Excel format not verified -- falling back to generic parser")
        return _parse_generic_df(df, exclude_tickers, format_label='excel_etrade_fallback')
    elif fmt == 'schwab':
        return _parse_schwab_df(df, exclude_tickers)
    else:
        return _parse_generic_df(df, exclude_tickers, format_label='excel_generic')


def validate_tickers(tickers):
    """
    Validate tickers exist on Yahoo Finance.

    Parameters
    ----------
    tickers : list of str

    Returns
    -------
    dict
        {'valid': list, 'invalid': list}
    """
    valid = []
    invalid = []

    print("Validating tickers...")
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            if hasattr(info, 'last_price') and info.last_price is not None:
                valid.append(ticker)
                print(f"  [OK] {ticker}")
            else:
                invalid.append(ticker)
                print(f"  [INVALID] {ticker} - no price data")
        except Exception:
            invalid.append(ticker)
            print(f"  [INVALID] {ticker}")
        time.sleep(0.5)

    return {'valid': valid, 'invalid': invalid}


def _find_column(df, candidates):
    """Find first matching column name (case-insensitive)."""
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def _is_option(symbol):
    """Check if symbol looks like an option/derivative."""
    return bool(re.search(r'(Call|Put|call|put|\d{2}\s\'\d{2}|Option)', symbol))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        result = parse_csv(sys.argv[1])
        print(f"\nParsed {len(result['tickers'])} holdings:")
        for ticker, alloc in result['allocations'].items():
            print(f"  {ticker:6s}  {alloc:.1%}")
    else:
        print("Usage: python parse_portfolio.py <csv_file>")
