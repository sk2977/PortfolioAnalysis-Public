"""
Portfolio Optimizer
===================
Runs portfolio optimization using pyportfolioopt with:
- Three expected return methods: CAPM, Mean Historical, EMA
- Weighted average of all three methods
- Configurable risk tolerance presets
- Ledoit-Wolf covariance shrinkage
"""

import pandas as pd
import numpy as np
from pypfopt import risk_models, expected_returns, EfficientFrontier, objective_functions


# Risk tolerance presets
RISK_PRESETS = {
    'conservative': {
        'max_weight': 0.10,
        'optimization_method': 'min_volatility',
        'gamma': 0.10,
        'risk_free_rate': 0.04,
        'method_weights': {'capm': 0.34, 'mean': 0.33, 'ema': 0.33},
        'include_tickers': [],
        'include_floor': 0.01,
        'benchmark': 'VTI',
    },
    'moderate': {
        'max_weight': 0.15,
        'optimization_method': 'max_sharpe',
        'gamma': 0.05,
        'risk_free_rate': 0.04,
        'method_weights': {'capm': 0.34, 'mean': 0.33, 'ema': 0.33},
        'include_tickers': [],
        'include_floor': 0.01,
        'benchmark': 'VTI',
    },
    'aggressive': {
        'max_weight': 0.25,
        'optimization_method': 'max_sharpe',
        'gamma': 0.02,
        'risk_free_rate': 0.04,
        'method_weights': {'capm': 0.34, 'mean': 0.33, 'ema': 0.33},
        'include_tickers': [],
        'include_floor': 0.01,
        'benchmark': 'VTI',
    },
}


def _build_weight_bounds(tickers, max_weight, include_tickers=None, include_floor=0.01):
    """
    Build weight bounds for EfficientFrontier.

    Parameters
    ----------
    tickers : list of str
        Ordered list of tickers (must match cov_matrix.index order).
    max_weight : float
        Maximum weight per security (upper bound for all tickers).
    include_tickers : list of str or None
        Tickers that must appear with at least include_floor weight.
        Matching is case-insensitive. If None or empty, returns scalar tuple.
    include_floor : float
        Minimum weight for forced-include tickers.

    Returns
    -------
    tuple or list of tuples
        Scalar (0, max_weight) if no include list; list of per-ticker
        (min, max) tuples if include list is provided.
    """
    if not include_tickers:
        return (0, max_weight)

    forced = {t.upper() for t in include_tickers}
    return [
        (include_floor, max_weight) if ticker.upper() in forced else (0, max_weight)
        for ticker in tickers
    ]


def get_default_config(risk_tolerance='moderate'):
    """
    Get optimization config for a given risk tolerance.

    Parameters
    ----------
    risk_tolerance : str
        One of: 'conservative', 'moderate', 'aggressive'

    Returns
    -------
    dict
        Configuration dictionary with all optimization parameters.
    """
    if risk_tolerance not in RISK_PRESETS:
        print(f"  [WARN] Unknown risk tolerance '{risk_tolerance}', using 'moderate'")
        risk_tolerance = 'moderate'

    config = RISK_PRESETS[risk_tolerance].copy()
    config['risk_tolerance'] = risk_tolerance
    return config


def optimize_portfolio(prices, benchmark_prices, current_allocations, config=None):
    """
    Run full portfolio optimization pipeline.

    Parameters
    ----------
    prices : pd.DataFrame
        Historical close prices (columns=tickers, index=dates).
    benchmark_prices : pd.Series
        Benchmark price series for CAPM.
    current_allocations : pd.Series
        Current portfolio weights (index=ticker, values=weight 0-1).
    config : dict, optional
        Optimization config. If None, uses moderate defaults.

    Returns
    -------
    dict
        {
            'optimal_allocations': pd.Series,
            'comparison': pd.DataFrame,
            'performance': {
                'current': {'return', 'volatility', 'sharpe'},
                'optimal': {'return', 'volatility', 'sharpe'}
            },
            'method_results': dict,
            'cov_matrix': pd.DataFrame,
            'config': dict
        }
    """
    if config is None:
        config = get_default_config('moderate')

    print(f"\nRunning portfolio optimization...")
    print(f"  Risk tolerance: {config.get('risk_tolerance', 'custom')}")
    print(f"  Method: {config['optimization_method']}")
    print(f"  Max weight per security: {config['max_weight']:.0%}")

    # Step 1: Covariance matrix (Ledoit-Wolf shrinkage)
    print("  Calculating covariance matrix (Ledoit-Wolf)...")
    cov_matrix = risk_models.CovarianceShrinkage(prices).ledoit_wolf()

    # Step 2: Expected returns (3 methods)
    print("  Calculating expected returns...")
    returns_dict = calculate_expected_returns(
        prices, benchmark_prices, config['risk_free_rate']
    )

    # Step 3: Optimize for each method
    method_results = {}
    for method in ['capm', 'mean', 'ema']:
        print(f"    Optimizing with {method.upper()} returns...")
        method_results[method] = _run_single_optimization(
            returns_dict[method],
            cov_matrix,
            config['max_weight'],
            config['risk_free_rate'],
            config['gamma'],
            config['optimization_method'],
            include_tickers=config.get('include_tickers'),
            include_floor=config.get('include_floor', 0.01)
        )

    # Step 4: Weighted average allocation
    print("  Computing weighted average allocation...")
    optimal_alloc = _weighted_average(
        method_results, config['method_weights'], list(prices.columns)
    )

    # Step 5: Compare current vs optimal
    comparison = _compare_allocations(current_allocations, optimal_alloc)

    # Step 6: Calculate portfolio performance
    weighted_mu = sum(
        returns_dict[m] * config['method_weights'][m]
        for m in ['capm', 'mean', 'ema']
    )

    current_perf = _portfolio_performance(
        current_allocations, weighted_mu, cov_matrix, config['risk_free_rate']
    )
    optimal_perf = _portfolio_performance(
        optimal_alloc, weighted_mu, cov_matrix, config['risk_free_rate']
    )

    print(f"\n  Results:")
    print(f"    Current:  Return={current_perf['return']:.2%}  "
          f"Vol={current_perf['volatility']:.2%}  "
          f"Sharpe={current_perf['sharpe']:.3f}")
    print(f"    Optimal:  Return={optimal_perf['return']:.2%}  "
          f"Vol={optimal_perf['volatility']:.2%}  "
          f"Sharpe={optimal_perf['sharpe']:.3f}")

    return {
        'optimal_allocations': optimal_alloc,
        'comparison': comparison,
        'performance': {
            'current': current_perf,
            'optimal': optimal_perf
        },
        'method_results': method_results,
        'cov_matrix': cov_matrix,
        'returns_dict': returns_dict,
        'config': config
    }


def calculate_expected_returns(prices, benchmark_prices, risk_free_rate=0.04):
    """
    Calculate expected returns using three methods.

    Returns
    -------
    dict
        {'capm': pd.Series, 'mean': pd.Series, 'ema': pd.Series}
    """
    return {
        'capm': expected_returns.capm_return(
            prices, market_prices=benchmark_prices,
            risk_free_rate=risk_free_rate
        ),
        'mean': expected_returns.mean_historical_return(prices),
        'ema': expected_returns.ema_historical_return(prices),
    }


def _run_single_optimization(mu, cov_matrix, max_weight, risk_free_rate,
                              gamma, method='max_sharpe',
                              include_tickers=None, include_floor=0.01):
    """Run optimization for a single expected returns method."""
    bounds = _build_weight_bounds(
        list(cov_matrix.index), max_weight,
        include_tickers=include_tickers, include_floor=include_floor
    )
    ef = EfficientFrontier(mu, cov_matrix, weight_bounds=bounds)
    ef.add_objective(objective_functions.L2_reg, gamma=gamma)

    try:
        if method == 'max_sharpe':
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        elif method == 'min_volatility':
            ef.min_volatility()
        elif method == 'max_quadratic_utility':
            ef.max_quadratic_utility(risk_aversion=1)
        else:
            ef.max_sharpe(risk_free_rate=risk_free_rate)

        weights = ef.clean_weights()
        performance = ef.portfolio_performance(risk_free_rate=risk_free_rate)

        return {
            'weights': weights,
            'performance': {
                'return': performance[0],
                'volatility': performance[1],
                'sharpe': performance[2]
            },
            'method_used': method
        }

    except Exception as e:
        print(f"      [WARN] {method} failed ({e}), falling back to max_sharpe")
        ef2 = EfficientFrontier(mu, cov_matrix, weight_bounds=bounds)
        ef2.add_objective(objective_functions.L2_reg, gamma=gamma)
        ef2.max_sharpe(risk_free_rate=risk_free_rate)

        weights = ef2.clean_weights()
        performance = ef2.portfolio_performance(risk_free_rate=risk_free_rate)

        return {
            'weights': weights,
            'performance': {
                'return': performance[0],
                'volatility': performance[1],
                'sharpe': performance[2]
            },
            'method_used': 'max_sharpe (fallback)'
        }


def _weighted_average(method_results, weights, tickers):
    """Compute weighted average allocation across methods."""
    alloc = pd.Series(0.0, index=tickers)
    for method, weight in weights.items():
        method_weights = pd.Series(method_results[method]['weights'])
        alloc = alloc.add(method_weights * weight, fill_value=0)
    return alloc


def _compare_allocations(current, optimal):
    """Create comparison DataFrame."""
    comparison = pd.DataFrame({
        'Current': current,
        'Optimal': optimal
    }).fillna(0)
    comparison['Difference'] = comparison['Optimal'] - comparison['Current']
    return comparison.sort_values('Difference', ascending=False)


def _portfolio_performance(weights, mu, cov_matrix, risk_free_rate):
    """Calculate portfolio return, volatility, and Sharpe ratio."""
    # Align weights with mu index
    w = weights.reindex(mu.index).fillna(0)

    ret = w.dot(mu)
    vol = np.sqrt(w @ cov_matrix @ w)
    sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0

    return {
        'return': float(ret),
        'volatility': float(vol),
        'sharpe': float(sharpe)
    }


if __name__ == '__main__':
    print("Risk tolerance presets:")
    for name, preset in RISK_PRESETS.items():
        print(f"  {name}: max_weight={preset['max_weight']:.0%}, "
              f"method={preset['optimization_method']}, gamma={preset['gamma']}")
