"""
Visualization Module
====================
Generates matplotlib charts saved as PNG files to output/.
All charts use ASCII-only labels (no Unicode/emoji).
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from pypfopt import EfficientFrontier, objective_functions, plotting
from pathlib import Path


OUTPUT_DIR = 'output'

# Style config
try:
    plt.rcParams['font.family'] = 'Calibri'
except Exception:
    plt.rcParams['font.family'] = 'sans-serif'

COLORS = {
    'primary': '#4472C4',
    'secondary': '#ED7D31',
    'tertiary': '#70AD47',
    'accent': '#FF5733',
    'band': '#D9EAD3',
    'unemployment': '#A5A5A5',
    'inflation': '#FFC000',
    'gdp': '#2CA02C',
    'earnings': '#FF5733',
    'sp500': '#1f77b4',
    'highlight': '#D9EAD3',
}


def _ensure_output_dir(output_dir=OUTPUT_DIR):
    """Create output directory if needed."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)


def plot_allocation_comparison(comparison_df, output_dir=OUTPUT_DIR):
    """
    Bar chart comparing current vs optimal allocations.

    Returns
    -------
    str
        Path to saved PNG.
    """
    _ensure_output_dir(output_dir)

    fig, ax = plt.subplots(figsize=(14, 7))
    comparison_df[['Current', 'Optimal']].plot(kind='bar', ax=ax, width=0.8,
                                                color=[COLORS['primary'], COLORS['secondary']])
    ax.set_title('Portfolio Allocation: Current vs Optimal', fontsize=14, fontweight='bold')
    ax.set_xlabel('Ticker')
    ax.set_ylabel('Allocation')
    ax.legend(['Current', 'Optimal (Weighted Avg)'])
    ax.grid(axis='y', alpha=0.3)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1%}'))
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    path = str(Path(output_dir) / 'allocation_comparison.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path


def plot_efficient_frontier(returns_dict, cov_matrix, method_results,
                            current_alloc, optimal_alloc, config,
                            output_dir=OUTPUT_DIR):
    """
    4-panel efficient frontier: CAPM, Mean, EMA, and Weighted Average.

    Returns
    -------
    str
        Path to saved PNG.
    """
    _ensure_output_dir(output_dir)

    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    axes = axes.flatten()

    methods = ['capm', 'mean', 'ema']

    for i, method in enumerate(methods):
        try:
            mu = returns_dict[method]
            perf = method_results[method]['performance']

            # Current portfolio with this method's returns
            w_curr = current_alloc.reindex(mu.index).fillna(0)
            ret_curr = w_curr.dot(mu)
            vol_curr = np.sqrt(w_curr @ cov_matrix @ w_curr)
            sharpe_curr = (ret_curr - config['risk_free_rate']) / vol_curr if vol_curr > 0 else 0

            # Efficient frontier
            ef = EfficientFrontier(mu, cov_matrix,
                                   weight_bounds=(0, config['max_weight']))
            ef.add_objective(objective_functions.L2_reg, gamma=config['gamma'])
            plotting.plot_efficient_frontier(ef, ax=axes[i], show_assets=True)

            axes[i].scatter(vol_curr, ret_curr, marker='o', s=150, c='blue',
                           label=f'Current (SR={sharpe_curr:.2f})',
                           zorder=3, edgecolors='black', linewidths=1.5)
            axes[i].scatter(perf['volatility'], perf['return'], marker='*', s=300, c='red',
                           label=f'Optimal (SR={perf["sharpe"]:.2f})',
                           zorder=3, edgecolors='black', linewidths=1.5)

            axes[i].set_title(f'Efficient Frontier - {method.upper()}',
                             fontsize=13, fontweight='bold')
            axes[i].legend(loc='best', fontsize=9)
            axes[i].grid(alpha=0.3)

        except Exception as e:
            axes[i].text(0.5, 0.5, f'Error: {str(e)[:50]}',
                        ha='center', va='center', transform=axes[i].transAxes)
            axes[i].set_title(f'{method.upper()} - Error', fontsize=13)

    # Panel 4: Weighted average
    try:
        weighted_mu = sum(
            returns_dict[m] * config['method_weights'][m]
            for m in ['capm', 'mean', 'ema']
        )

        w_opt = optimal_alloc.reindex(weighted_mu.index).fillna(0)
        w_curr = current_alloc.reindex(weighted_mu.index).fillna(0)

        ret_opt = w_opt.dot(weighted_mu)
        vol_opt = np.sqrt(w_opt @ cov_matrix @ w_opt)
        sharpe_opt = (ret_opt - config['risk_free_rate']) / vol_opt if vol_opt > 0 else 0

        ret_curr = w_curr.dot(weighted_mu)
        vol_curr = np.sqrt(w_curr @ cov_matrix @ w_curr)
        sharpe_curr = (ret_curr - config['risk_free_rate']) / vol_curr if vol_curr > 0 else 0

        ef_w = EfficientFrontier(weighted_mu, cov_matrix,
                                 weight_bounds=(0, config['max_weight']))
        ef_w.add_objective(objective_functions.L2_reg, gamma=config['gamma'])
        plotting.plot_efficient_frontier(ef_w, ax=axes[3], show_assets=True)

        axes[3].scatter(vol_curr, ret_curr, marker='o', s=150, c='blue',
                       label=f'Current (SR={sharpe_curr:.2f})',
                       zorder=3, edgecolors='black', linewidths=1.5)
        axes[3].scatter(vol_opt, ret_opt, marker='*', s=300, c='red',
                       label=f'Optimal (SR={sharpe_opt:.2f})',
                       zorder=3, edgecolors='black', linewidths=1.5)

        axes[3].set_title('Efficient Frontier - WEIGHTED AVERAGE',
                         fontsize=13, fontweight='bold')
        axes[3].legend(loc='best', fontsize=9)
        axes[3].grid(alpha=0.3)

    except Exception as e:
        axes[3].text(0.5, 0.5, f'Error: {str(e)[:50]}',
                    ha='center', va='center', transform=axes[3].transAxes)

    plt.tight_layout()
    path = str(Path(output_dir) / 'efficient_frontiers.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path


def plot_correlation_matrix(cov_matrix, output_dir=OUTPUT_DIR):
    """
    Correlation heatmap from covariance matrix.

    Returns
    -------
    str
        Path to saved PNG.
    """
    _ensure_output_dir(output_dir)

    if cov_matrix.empty:
        return None

    # Convert covariance to correlation
    std_devs = np.sqrt(np.diag(cov_matrix))
    corr_matrix = cov_matrix / np.outer(std_devs, std_devs)

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdBu_r',
                center=0, vmin=-1, vmax=1, square=True,
                linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title('Asset Correlation Matrix', fontsize=14, fontweight='bold')
    plt.tight_layout()

    path = str(Path(output_dir) / 'correlation_matrix.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path


def _add_value_annotation(ax, data, color, x_offset=0, y_offset=10):
    """Add current value and date annotation to the last data point."""
    if data.empty:
        return
    last_value = data.iloc[-1, 0]
    last_date = data.index[-1]
    ax.annotate(f'{last_value:.2f}%', xy=(last_date, last_value),
                xytext=(x_offset, y_offset), textcoords='offset points',
                color=color, fontweight='bold')
    ax.annotate(f'{last_date.strftime("%Y-%m-%d")}', xy=(last_date, last_value),
                xytext=(x_offset, y_offset - 25), textcoords='offset points',
                color=color, fontsize=9)


def _add_yoy_highlight(ax, start_date, end_date, yoy_change, metric_name):
    """Add shaded YoY highlight band with label."""
    ax.axvspan(start_date, end_date, color=COLORS['highlight'], alpha=0.5)
    mid_date = start_date + (end_date - start_date) / 2
    y_pos = ax.get_ylim()[1] * 0.95
    ax.text(mid_date, y_pos, f'Previous Year\n{metric_name} YoY: {yoy_change:.2f}%',
            ha='center', va='top', fontsize=10, color='green',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))


def plot_macro_primary(macro_data, output_dir=OUTPUT_DIR):
    """
    3-panel primary economic indicators: Interest Rates, Unemployment, CPI.

    Parameters
    ----------
    macro_data : dict
        Output from macro_analysis.get_macro_context().

    Returns
    -------
    str or None
        Path to saved PNG, or None if insufficient data.
    """
    import datetime as dt

    _ensure_output_dir(output_dir)

    data = macro_data.get('data', {})
    indicators = macro_data.get('indicators', {})

    bbb_yield = data.get('bbb_yield', pd.DataFrame())
    fed_funds = data.get('fed_funds', pd.DataFrame())
    ten_year = data.get('ten_year', pd.DataFrame())
    unemployment = data.get('unemployment', pd.DataFrame())
    inflation = data.get('inflation', pd.DataFrame())

    if all(d.empty for d in [bbb_yield, fed_funds, ten_year, unemployment, inflation]):
        print("  [SKIP] Insufficient data for primary macro dashboard")
        return None

    today = dt.datetime.today()
    one_year_ago = today - dt.timedelta(days=365)

    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(18, 6))

    # Panel 1: Interest Rates
    if not bbb_yield.empty:
        axes[0].plot(bbb_yield, label='BBB Corporate Bonds',
                     color=COLORS['primary'], linewidth=2)
        _add_value_annotation(axes[0], bbb_yield, COLORS['primary'])
    if not fed_funds.empty:
        axes[0].plot(fed_funds, label='Fed Funds Rate',
                     color=COLORS['secondary'], linewidth=2)
        _add_value_annotation(axes[0], fed_funds, COLORS['secondary'])
    if not ten_year.empty:
        axes[0].plot(ten_year, label='10Y Treasury',
                     color=COLORS['tertiary'], linewidth=2)
        _add_value_annotation(axes[0], ten_year, COLORS['tertiary'])

    axes[0].set_title('Interest Rates Comparison', fontsize=14, fontweight='bold')
    axes[0].legend(loc='upper left')
    axes[0].grid(True, alpha=0.3)
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1f}%'))

    bbb_yoy = indicators.get('bbb_yield', {}).get('yoy')
    if bbb_yoy is not None:
        _add_yoy_highlight(axes[0], one_year_ago, today, bbb_yoy, 'BBB Yield')

    # Panel 2: Unemployment
    if not unemployment.empty:
        axes[1].plot(unemployment, label='Unemployment Rate',
                     color=COLORS['unemployment'], linewidth=2)
        axes[1].fill_between(unemployment.index, unemployment.iloc[:, 0],
                             alpha=0.3, color=COLORS['unemployment'])
        _add_value_annotation(axes[1], unemployment, COLORS['unemployment'])

    axes[1].set_title('Unemployment Rate', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    unemp_max = unemployment.max().iloc[0] if not unemployment.empty else 6
    axes[1].set_ylim(bottom=0, top=max(6, unemp_max * 1.1))
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1f}%'))

    unemp_yoy = indicators.get('unemployment', {}).get('yoy')
    if unemp_yoy is not None:
        _add_yoy_highlight(axes[1], one_year_ago, today, unemp_yoy, 'Unemployment')

    # Panel 3: CPI
    if not inflation.empty:
        axes[2].plot(inflation, label='CPI (1982-84=100)',
                     color=COLORS['inflation'], linewidth=2)
        last_value = inflation.iloc[-1, 0]
        last_date = inflation.index[-1]
        axes[2].annotate(f'{last_value:.1f}', xy=(last_date, last_value),
                         xytext=(0, 10), textcoords='offset points',
                         color=COLORS['inflation'], fontweight='bold')
        axes[2].annotate(f'{last_date.strftime("%Y-%m-%d")}', xy=(last_date, last_value),
                         xytext=(0, -15), textcoords='offset points',
                         color=COLORS['inflation'], fontsize=9)

    axes[2].set_title('Consumer Price Index', fontsize=14, fontweight='bold')
    axes[2].set_ylabel('CPI Index')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    infl_min = inflation.min().iloc[0] if not inflation.empty else 100
    axes[2].set_ylim(bottom=max(100, infl_min * 0.95))

    infl_yoy = indicators.get('inflation', {}).get('yoy')
    if infl_yoy is not None:
        _add_yoy_highlight(axes[2], one_year_ago, today, infl_yoy, 'Inflation')

    plt.tight_layout()
    path = str(Path(output_dir) / 'macro_primary.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path


def plot_macro_secondary(macro_data, output_dir=OUTPUT_DIR):
    """
    2-panel secondary indicators: GDP Growth, Corporate Profits vs S&P 500.

    Parameters
    ----------
    macro_data : dict
        Output from macro_analysis.get_macro_context().

    Returns
    -------
    str or None
        Path to saved PNG, or None if insufficient data.
    """
    import datetime as dt

    _ensure_output_dir(output_dir)

    data = macro_data.get('data', {})
    indicators = macro_data.get('indicators', {})

    gdp = data.get('gdp', pd.DataFrame())
    corporate_profits = data.get('corporate_profits', pd.DataFrame())
    sp500 = data.get('sp500', pd.DataFrame())

    if all(d.empty for d in [gdp, corporate_profits, sp500]):
        print("  [SKIP] Insufficient data for secondary macro dashboard")
        return None

    today = dt.datetime.today()
    one_year_ago = today - dt.timedelta(days=365)

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))

    # Panel 1: GDP
    if not gdp.empty:
        axes[0].plot(gdp, label='US GDP', color=COLORS['gdp'], linewidth=2)
        axes[0].fill_between(gdp.index, gdp.iloc[:, 0], alpha=0.3, color=COLORS['gdp'])

        last_value = gdp.iloc[-1, 0]
        last_date = gdp.index[-1]
        axes[0].annotate(f'${last_value / 1000:.1f}T', xy=(last_date, last_value),
                         xytext=(0, 10), textcoords='offset points',
                         color=COLORS['gdp'], fontweight='bold')
        axes[0].annotate(f'{last_date.strftime("%Y-%m-%d")}', xy=(last_date, last_value),
                         xytext=(0, -15), textcoords='offset points',
                         color=COLORS['gdp'], fontsize=9)

        axes[0].set_title('US GDP Growth', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('GDP (Billions USD)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        gdp_yoy = indicators.get('gdp', {}).get('yoy')
        if gdp_yoy is not None:
            _add_yoy_highlight(axes[0], one_year_ago, gdp.index[-1], gdp_yoy, 'GDP')

    # Panel 2: Corporate Profits vs S&P 500
    if not corporate_profits.empty:
        axes[1].plot(corporate_profits, label='Corporate Profits After Tax',
                     color=COLORS['earnings'], linewidth=2)
        axes[1].set_ylabel('Corporate Profits ($B)', color=COLORS['earnings'])
        axes[1].tick_params(axis='y', labelcolor=COLORS['earnings'])

        if not sp500.empty:
            ax2 = axes[1].twinx()
            ax2.plot(sp500, label='S&P 500', color=COLORS['sp500'], linewidth=2)
            ax2.set_ylabel('S&P 500 Index', color=COLORS['sp500'])
            ax2.tick_params(axis='y', labelcolor=COLORS['sp500'])

            if len(corporate_profits) > 1 and len(sp500) > 1:
                corr = corporate_profits.iloc[:, 0].corr(sp500.iloc[:, 0])
                axes[1].text(0.05, 0.95, f'Correlation: {corr:.3f}',
                             transform=axes[1].transAxes, fontsize=10,
                             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        axes[1].set_title('Corporate Profits vs S&P 500', fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = str(Path(output_dir) / 'macro_secondary.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path


def plot_price_history(prices, output_dir=OUTPUT_DIR):
    """
    Normalized price history chart.

    Returns
    -------
    str
        Path to saved PNG.
    """
    _ensure_output_dir(output_dir)

    fig, ax = plt.subplots(figsize=(14, 6))
    normalized = prices / prices.iloc[0] * 100  # Rebase to 100
    normalized.plot(ax=ax, alpha=0.7)
    ax.set_title('Normalized Price History (Rebased to 100)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Normalized Price')
    ax.legend(loc='best', fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()

    path = str(Path(output_dir) / 'price_history.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved: {path}")
    return path
