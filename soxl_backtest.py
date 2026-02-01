#!/usr/bin/env python3
"""
Backtest for SOXL/SOXS Semiconductor Strategy

Tests the dual MA + momentum strategy on historical data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Strategy parameters
MA_LONG = 200
MA_SHORT = 50
ROC_PERIOD = 20
ROC_THRESHOLD = 0.02

TICKER_INDEX = "^SOX"
TICKER_LONG = "SOXL"
TICKER_SHORT = "SOXS"


def fetch_data(ticker: str, start: str = "2015-01-01", end: str = None) -> pd.DataFrame:
    """Fetch historical data."""
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching {ticker} data from {start} to {end}...")
    data = yf.download(ticker, start=start, end=end, progress=False)
    
    # Handle multi-level columns from yfinance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    return data


def run_backtest(
    index_data: pd.DataFrame,
    long_etf_data: pd.DataFrame,
    short_etf_data: pd.DataFrame = None,
    initial_capital: float = 100000,
    use_shorts: bool = False
) -> dict:
    """
    Run backtest of the semiconductor strategy.
    
    Strategy:
    - LONG: Price > 200 MA, Price > 50 MA, ROC > threshold
    - SHORT: Price < 200 MA, Price < 50 MA, ROC < -threshold
    - CASH: Otherwise
    """
    # Prepare data - extract Close prices as Series
    idx_close = index_data['Close'].copy()
    long_close = long_etf_data['Close'].copy()
    
    # Create aligned DataFrame
    df = pd.DataFrame({
        'index_close': idx_close,
        'long_close': long_close
    })
    
    if short_etf_data is not None and use_shorts:
        short_close = short_etf_data['Close'].copy()
        df['short_close'] = short_close
    
    df = df.dropna()
    
    # Calculate indicators
    df['sma_200'] = df['index_close'].rolling(window=MA_LONG).mean()
    df['sma_50'] = df['index_close'].rolling(window=MA_SHORT).mean()
    df['roc'] = df['index_close'].pct_change(periods=ROC_PERIOD)
    
    df = df.dropna()
    
    # Generate signals
    df['above_200'] = df['index_close'] > df['sma_200']
    df['above_50'] = df['index_close'] > df['sma_50']
    df['strong_up'] = df['roc'] > ROC_THRESHOLD
    df['strong_down'] = df['roc'] < -ROC_THRESHOLD
    
    # Position: 1 = long, -1 = short, 0 = cash
    conditions = [
        (df['above_200'] & df['above_50'] & df['strong_up']),  # Long
        (~df['above_200'] & ~df['above_50'] & df['strong_down']),  # Short
    ]
    choices = [1, -1 if use_shorts else 0]
    df['position'] = np.select(conditions, choices, default=0)
    
    # Calculate returns
    df['long_return'] = df['long_close'].pct_change()
    if use_shorts and 'short_close' in df.columns:
        df['short_return'] = df['short_close'].pct_change()
    else:
        df['short_return'] = 0
    
    # Strategy returns
    df['strategy_return'] = np.where(
        df['position'].shift(1) == 1,
        df['long_return'],
        np.where(
            df['position'].shift(1) == -1,
            df['short_return'],
            0
        )
    )
    
    # Buy and hold returns
    df['buy_hold_return'] = df['long_return']
    
    df = df.dropna()
    
    # Cumulative returns
    df['strategy_cumulative'] = (1 + df['strategy_return']).cumprod()
    df['buy_hold_cumulative'] = (1 + df['buy_hold_return']).cumprod()
    
    # Portfolio values
    df['strategy_value'] = initial_capital * df['strategy_cumulative']
    df['buy_hold_value'] = initial_capital * df['buy_hold_cumulative']
    
    # Calculate metrics
    results = calculate_metrics(df, initial_capital, use_shorts)
    results['data'] = df
    
    return results


def calculate_metrics(data: pd.DataFrame, initial_capital: float, use_shorts: bool) -> dict:
    """Calculate performance metrics."""
    
    strategy_returns = data['strategy_return']
    final_value = data['strategy_value'].iloc[-1]
    
    # Basic metrics
    total_return = (final_value - initial_capital) / initial_capital
    years = len(data) / 252
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    annual_vol = strategy_returns.std() * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # Max drawdown
    cumulative = data['strategy_cumulative']
    rolling_max = cumulative.expanding().max()
    drawdowns = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()
    
    # Win rate
    winning_days = (strategy_returns > 0).sum()
    trading_days = (strategy_returns != 0).sum()
    win_rate = winning_days / trading_days if trading_days > 0 else 0
    
    # Trade count
    trades = (data['position'] != data['position'].shift(1)).sum()
    
    # Time in market
    time_long = (data['position'] == 1).mean()
    time_short = (data['position'] == -1).mean()
    time_cash = (data['position'] == 0).mean()
    
    # Buy & hold comparison
    bh_final = data['buy_hold_value'].iloc[-1]
    bh_total = (bh_final - initial_capital) / initial_capital
    bh_annual = (1 + bh_total) ** (1 / years) - 1 if years > 0 else 0
    
    bh_cumulative = data['buy_hold_cumulative']
    bh_rolling_max = bh_cumulative.expanding().max()
    bh_drawdowns = (bh_cumulative - bh_rolling_max) / bh_rolling_max
    bh_max_dd = bh_drawdowns.min()
    
    return {
        'start_date': data.index[0].strftime("%Y-%m-%d"),
        'end_date': data.index[-1].strftime("%Y-%m-%d"),
        'years': round(years, 2),
        'initial_capital': initial_capital,
        'use_shorts': use_shorts,
        
        # Strategy
        'final_value': round(final_value, 2),
        'total_return': round(total_return * 100, 2),
        'annual_return': round(annual_return * 100, 2),
        'annual_volatility': round(annual_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
        'win_rate': round(win_rate * 100, 2),
        'total_trades': trades,
        
        # Time allocation
        'time_long': round(time_long * 100, 1),
        'time_short': round(time_short * 100, 1),
        'time_cash': round(time_cash * 100, 1),
        
        # Buy & hold
        'bh_final_value': round(bh_final, 2),
        'bh_total_return': round(bh_total * 100, 2),
        'bh_annual_return': round(bh_annual * 100, 2),
        'bh_max_drawdown': round(bh_max_dd * 100, 2),
    }


def print_results(results: dict):
    """Pretty print backtest results."""
    print("\n" + "="*65)
    print("🔧 BACKTEST RESULTS - SOXL/SOXS SEMICONDUCTOR STRATEGY")
    print("="*65)
    print(f"📅 Period: {results['start_date']} to {results['end_date']} ({results['years']} years)")
    print(f"💰 Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"🔀 Shorting: {'Enabled (SOXS)' if results['use_shorts'] else 'Disabled (Cash only)'}")
    print()
    
    print("📈 STRATEGY PERFORMANCE:")
    print("-"*45)
    print(f"  Final Value:      ${results['final_value']:>15,.2f}")
    print(f"  Total Return:     {results['total_return']:>15.2f}%")
    print(f"  Annual Return:    {results['annual_return']:>15.2f}%")
    print(f"  Annual Volatility:{results['annual_volatility']:>15.2f}%")
    print(f"  Sharpe Ratio:     {results['sharpe_ratio']:>15.2f}")
    print(f"  Max Drawdown:     {results['max_drawdown']:>15.2f}%")
    print(f"  Win Rate:         {results['win_rate']:>15.2f}%")
    print(f"  Total Trades:     {results['total_trades']:>15}")
    print()
    
    print("⏱️ TIME ALLOCATION:")
    print("-"*45)
    print(f"  Long (SOXL):      {results['time_long']:>15.1f}%")
    print(f"  Short (SOXS):     {results['time_short']:>15.1f}%")
    print(f"  Cash:             {results['time_cash']:>15.1f}%")
    print()
    
    print("📉 BUY & HOLD SOXL (Comparison):")
    print("-"*45)
    print(f"  Final Value:      ${results['bh_final_value']:>15,.2f}")
    print(f"  Total Return:     {results['bh_total_return']:>15.2f}%")
    print(f"  Annual Return:    {results['bh_annual_return']:>15.2f}%")
    print(f"  Max Drawdown:     {results['bh_max_drawdown']:>15.2f}%")
    print()
    
    # Comparison
    outperf = results['total_return'] - results['bh_total_return']
    dd_improve = results['bh_max_drawdown'] - results['max_drawdown']
    
    print("⚡ STRATEGY vs BUY & HOLD:")
    print("-"*45)
    if outperf > 0:
        print(f"  ✅ Outperformed by {outperf:.2f}%")
    else:
        print(f"  ❌ Underperformed by {abs(outperf):.2f}%")
    
    if dd_improve > 0:
        print(f"  ✅ Drawdown reduced by {dd_improve:.2f}%")
    else:
        print(f"  ❌ Drawdown increased by {abs(dd_improve):.2f}%")
    
    print("="*65 + "\n")


def run_comparison():
    """Compare long-only vs long-short strategies."""
    print("\n🔬 RUNNING STRATEGY COMPARISON...\n")
    
    # Fetch data
    index_data = fetch_data(TICKER_INDEX, start="2015-01-01")
    long_data = fetch_data(TICKER_LONG, start="2015-01-01")
    short_data = fetch_data(TICKER_SHORT, start="2015-01-01")
    
    if index_data.empty or long_data.empty:
        print("❌ Failed to fetch data")
        return
    
    # Long only (cash when bearish)
    print("\n" + "="*65)
    print("📊 SCENARIO 1: LONG ONLY (Cash when bearish)")
    print("="*65)
    results_long = run_backtest(index_data, long_data, use_shorts=False)
    print_results(results_long)
    
    # Long-short
    if not short_data.empty:
        print("\n" + "="*65)
        print("📊 SCENARIO 2: LONG-SHORT (SOXS when bearish)")
        print("="*65)
        results_both = run_backtest(index_data, long_data, short_data, use_shorts=True)
        print_results(results_both)
        
        # Summary comparison
        print("\n" + "="*65)
        print("📊 SUMMARY COMPARISON")
        print("="*65)
        print(f"{'Strategy':<20} {'Return':>12} {'Max DD':>12} {'Sharpe':>10}")
        print("-"*55)
        print(f"{'Long Only':<20} {results_long['total_return']:>11.1f}% {results_long['max_drawdown']:>11.1f}% {results_long['sharpe_ratio']:>10.2f}")
        print(f"{'Long-Short':<20} {results_both['total_return']:>11.1f}% {results_both['max_drawdown']:>11.1f}% {results_both['sharpe_ratio']:>10.2f}")
        print(f"{'Buy & Hold SOXL':<20} {results_long['bh_total_return']:>11.1f}% {results_long['bh_max_drawdown']:>11.1f}% {'N/A':>10}")
        print()


if __name__ == "__main__":
    run_comparison()
