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


def plot_erp_dashboard(macro_data, output_dir=OUTPUT_DIR):
    """
    2-panel ERP dashboard: timeseries + components.

    Parameters
    ----------
    macro_data : dict
        Output from macro_analysis.get_macro_context().

    Returns
    -------
    str or None
        Path to saved PNG, or None if insufficient data.
    """
    _ensure_output_dir(output_dir)

    erp_df = macro_data.get('erp_history')
    stats = macro_data.get('stats', {})

    if erp_df is None or erp_df.empty:
        print("  [SKIP] Insufficient data for ERP dashboard")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Panel 1: ERP timeseries
    ax1 = axes[0]
    if stats.get('p25') is not None and stats.get('p75') is not None:
        ax1.axhspan(stats['p25'], stats['p75'], alpha=0.2,
                    color=COLORS['band'], label='25-75 Percentile')
    if stats.get('mean') is not None:
        ax1.axhline(stats['mean'], color='gray', linestyle='--', alpha=0.5, label='Mean')

    ax1.plot(erp_df.index, erp_df['erp'], color=COLORS['primary'],
            linewidth=2.5, label='ERP', marker='o', markersize=4)

    if len(erp_df) > 0:
        last_date = erp_df.index[-1]
        last_erp = erp_df['erp'].iloc[-1]
        ax1.annotate(f'{last_erp:.2f}%', xy=(last_date, last_erp),
                    xytext=(0, 15), textcoords='offset points',
                    color=COLORS['accent'], fontweight='bold', fontsize=11, ha='center')

    ax1.set_title('Equity Risk Premium Over Time', fontsize=13, fontweight='bold')
    ax1.set_ylabel('ERP (%)', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1f}%'))

    # Panel 2: Components
    ax2 = axes[1]
    ax2.plot(erp_df.index, erp_df['earnings_yield'], color=COLORS['secondary'],
            linewidth=2.5, label='Earnings Yield', marker='s', markersize=4)
    ax2.plot(erp_df.index, erp_df['treasury_yield'], color=COLORS['tertiary'],
            linewidth=2.5, label='10Y Treasury Yield', marker='^', markersize=4)

    if len(erp_df) > 0:
        last_date = erp_df.index[-1]
        ax2.annotate(f'{erp_df["earnings_yield"].iloc[-1]:.2f}%',
                    xy=(last_date, erp_df['earnings_yield'].iloc[-1]),
                    xytext=(0, 15), textcoords='offset points',
                    color=COLORS['secondary'], fontweight='bold', fontsize=10, ha='center')
        ax2.annotate(f'{erp_df["treasury_yield"].iloc[-1]:.2f}%',
                    xy=(last_date, erp_df['treasury_yield'].iloc[-1]),
                    xytext=(0, -20), textcoords='offset points',
                    color=COLORS['tertiary'], fontweight='bold', fontsize=10, ha='center')

    ax2.set_title('ERP Components: Earnings Yield vs Treasury Yield',
                  fontsize=13, fontweight='bold')
    ax2.set_ylabel('Yield (%)', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1f}%'))

    plt.tight_layout()
    path = str(Path(output_dir) / 'erp_dashboard.png')
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
