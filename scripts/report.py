"""
Report Generator
================
Generates a markdown summary report from optimization and economic indicator results.
"""

import datetime
from pathlib import Path


OUTPUT_DIR = 'output'


def _compute_method_spread(returns_dict, threshold=0.05):
    """
    Compute per-ticker expected return spread across methods.

    Parameters
    ----------
    returns_dict : dict
        Mapping of method name -> pd.Series of expected returns, indexed by ticker.
        E.g. {'capm': Series, 'mean': Series, 'ema': Series}.
    threshold : float
        Spread threshold above which a ticker is flagged (default 0.05 = 5pp).

    Returns
    -------
    max_spread : float
        Largest spread observed across all tickers.
    flagged : dict
        Mapping of ticker -> spread (float) for tickers exceeding threshold.
    """
    import math as _math

    if not returns_dict:
        return 0.0, {}

    # Collect all series into a list for iteration
    series_list = list(returns_dict.values())
    tickers = series_list[0].index.tolist()

    max_spread = 0.0
    flagged = {}

    for ticker in tickers:
        values = []
        for s in series_list:
            if ticker in s.index:
                v = s[ticker]
                if not _math.isnan(float(v)):
                    values.append(float(v))
        if len(values) < 2:
            continue
        spread = max(values) - min(values)
        if spread > max_spread:
            max_spread = spread
        if spread > threshold:
            flagged[ticker] = spread

    return max_spread, flagged


def generate_report(optimization_results, macro_context, portfolio_info,
                    chart_paths=None, output_dir=OUTPUT_DIR,
                    macro_narrative=None, holding_commentary=None,
                    method_spread_note=None, returns_dict=None):
    """
    Generate a markdown report summarizing the analysis.

    Parameters
    ----------
    optimization_results : dict
        Output from optimize.optimize_portfolio().
    macro_context : dict
        Output from macro_analysis.get_macro_context().
    portfolio_info : dict
        Output from parse_portfolio.parse_csv().
    chart_paths : list of str, optional
        Paths to generated chart PNGs.
    output_dir : str
        Directory to save report.
    macro_narrative : str or None
        2-3 sentence qualitative macro interpretation (Phase 5.5 output).
    holding_commentary : dict or None
        Mapping of ticker -> commentary sentence for material allocation changes.
    method_spread_note : str or None
        Confidence note for tickers with high expected return spread across methods.
        If None and returns_dict is provided, a note is auto-computed via
        _compute_method_spread().
    returns_dict : dict or None
        {'capm': pd.Series, 'mean': pd.Series, 'ema': pd.Series} -- used to
        auto-compute method_spread_note when caller does not supply one.

    Returns
    -------
    str
        Markdown report content.
    """
    if chart_paths is None:
        chart_paths = []

    # Auto-compute method_spread_note from returns_dict if not explicitly provided
    if method_spread_note is None and returns_dict is not None:
        max_spread, flagged = _compute_method_spread(returns_dict)
        if flagged:
            ticker_list = ', '.join(
                f"{t} ({s:.1%})" for t, s in flagged.items()
            )
            method_spread_note = (
                f"Return estimate spread > 5pp for: {ticker_list}. "
                f"Max spread: {max_spread:.1%}. "
                f"Results may vary across estimation methods."
            )

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    config = optimization_results.get('config', {})
    perf = optimization_results.get('performance', {})
    comparison = optimization_results.get('comparison')

    lines = []
    lines.append(f"# Portfolio Analysis Report")
    lines.append(f"")
    lines.append(f"Generated: {now}")
    lines.append(f"")

    # Portfolio Summary
    lines.append(f"## Portfolio Summary")
    lines.append(f"")
    lines.append(f"- **Holdings**: {len(portfolio_info.get('tickers', []))} securities")
    lines.append(f"- **Securities**: {', '.join(portfolio_info.get('tickers', []))}")
    lines.append(f"- **Risk Tolerance**: {config.get('risk_tolerance', 'N/A')}")
    lines.append(f"- **Optimization Method**: {config.get('optimization_method', 'N/A')}")
    lines.append(f"- **Max Weight Per Security**: {config.get('max_weight', 0):.0%}")
    lines.append(f"")

    # Macro Context
    lines.append(f"## US Economic Indicators")
    lines.append(f"")
    indicators = macro_context.get('indicators', {})
    if indicators:
        lines.append(f"| Indicator | Value | YoY% | Date |")
        lines.append(f"|-----------|-------|------|------|")
        indicator_labels = {
            'bbb_yield': 'BBB Corporate Bonds',
            'fed_funds': 'Fed Funds Rate',
            'ten_year': '10Y Treasury',
            'unemployment': 'Unemployment Rate',
            'inflation': 'Consumer Price Index',
            'gdp': 'GDP ($B)',
            'corporate_profits': 'Corporate Profits ($B)',
            'sp500': 'S&P 500',
        }
        for name, info in indicators.items():
            if info.get('value') is not None:
                label = indicator_labels.get(name, name)
                yoy_str = f"{info['yoy']:+.2f}%" if info.get('yoy') is not None else "N/A"
                lines.append(f"| {label} | {info['value']:.2f} | {yoy_str} | {info.get('date', 'N/A')} |")
        lines.append(f"")
        lines.append(f"**Interpretation**: {macro_context.get('interpretation', 'N/A')}")
    else:
        lines.append(f"Macro data unavailable: {macro_context.get('interpretation', 'Error')}")
    lines.append(f"")

    # Performance Comparison
    lines.append(f"## Performance Comparison")
    lines.append(f"")
    curr = perf.get('current', {})
    opt = perf.get('optimal', {})

    lines.append(f"| Metric | Current | Optimal | Change |")
    lines.append(f"|--------|---------|---------|--------|")

    if curr and opt:
        ret_diff = opt.get('return', 0) - curr.get('return', 0)
        vol_diff = opt.get('volatility', 0) - curr.get('volatility', 0)
        sr_diff = opt.get('sharpe', 0) - curr.get('sharpe', 0)

        lines.append(f"| Expected Return | {curr.get('return', 0):.2%} | "
                     f"{opt.get('return', 0):.2%} | {ret_diff:+.2%} |")
        lines.append(f"| Volatility | {curr.get('volatility', 0):.2%} | "
                     f"{opt.get('volatility', 0):.2%} | {vol_diff:+.2%} |")
        lines.append(f"| Sharpe Ratio | {curr.get('sharpe', 0):.3f} | "
                     f"{opt.get('sharpe', 0):.3f} | {sr_diff:+.3f} |")
    lines.append(f"")

    # Allocation Comparison
    if comparison is not None:
        lines.append(f"## Allocation: Current vs Optimal")
        lines.append(f"")
        lines.append(f"| Ticker | Current | Optimal | Change |")
        lines.append(f"|--------|---------|---------|--------|")

        for ticker, row in comparison.iterrows():
            if row['Current'] > 0.001 or row['Optimal'] > 0.001:
                lines.append(f"| {ticker} | {row['Current']:.1%} | "
                             f"{row['Optimal']:.1%} | {row['Difference']:+.1%} |")
        lines.append(f"")

        # Top rebalancing actions
        increases = comparison[comparison['Difference'] > 0.01].head(5)
        decreases = comparison[comparison['Difference'] < -0.01].tail(5).iloc[::-1]

        if len(increases) > 0:
            lines.append(f"### Top Increases")
            lines.append(f"")
            for ticker, row in increases.iterrows():
                lines.append(f"- **{ticker}**: {row['Current']:.1%} -> "
                             f"{row['Optimal']:.1%} ({row['Difference']:+.1%})")
            lines.append(f"")

        if len(decreases) > 0:
            lines.append(f"### Top Decreases")
            lines.append(f"")
            for ticker, row in decreases.iterrows():
                lines.append(f"- **{ticker}**: {row['Current']:.1%} -> "
                             f"{row['Optimal']:.1%} ({row['Difference']:+.1%})")
            lines.append(f"")

    # Implementation Priority
    if curr and opt:
        sharpe_improvement = opt.get('sharpe', 0) - curr.get('sharpe', 0)
        return_improvement = opt.get('return', 0) - curr.get('return', 0)

        lines.append(f"## Implementation Priority")
        lines.append(f"")

        if sharpe_improvement > 0.3 or return_improvement > 0.03:
            lines.append(f"**HIGH** - Significant optimization opportunity identified.")
        elif sharpe_improvement > 0.1 or return_improvement > 0.01:
            lines.append(f"**MODERATE** - Meaningful improvements available.")
        else:
            lines.append(f"**LOW** - Portfolio is reasonably well-optimized.")
        lines.append(f"")

    # Charts
    if chart_paths:
        lines.append(f"## Charts")
        lines.append(f"")
        for path in chart_paths:
            name = Path(path).stem.replace('_', ' ').title()
            lines.append(f"![{name}]({path})")
            lines.append(f"")

    # Qualitative Narrative (Phase 5.5 output)
    if macro_narrative:
        lines.append(f"### Macro Interpretation")
        lines.append(f"")
        lines.append(macro_narrative)
        lines.append(f"")

    if holding_commentary:
        lines.append(f"### Holding Commentary")
        lines.append(f"")
        for ticker, note in holding_commentary.items():
            lines.append(f"- **{ticker}**: {note}")
        lines.append(f"")

    if method_spread_note:
        lines.append(f"### Confidence Note")
        lines.append(f"")
        lines.append(method_spread_note)
        lines.append(f"")

    # Disclaimer
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"**Disclaimer**: This analysis is for educational and informational "
                 f"purposes only. It does not constitute financial advice. Past performance "
                 f"does not guarantee future results. Always consult a qualified financial "
                 f"advisor before making investment decisions.")

    report = '\n'.join(lines)

    # Save to file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = str(Path(output_dir) / 'report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  [OK] Report saved: {report_path}")

    return report
