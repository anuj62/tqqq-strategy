#!/usr/bin/env python3
"""
Backtest for TQQQ Trend Following Strategy

Tests the 250-day MA crossover strategy on historical data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from config import MA_PERIOD, TICKER_INDEX, TICKER_LONG


def fetch_data(ticker: str, start: str = "2010-01-01", end: str = None) -> pd.DataFrame:
    """Fetch historical data."""
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching {ticker} data from {start} to {end}...")
    data = yf.download(ticker, start=start, end=end, progress=False)
    return data


def run_backtest(
    index_data: pd.DataFrame,
    etf_data: pd.DataFrame,
    ma_period: int = MA_PERIOD,
    initial_capital: float = 100000,
    use_leverage_decay: bool = True
) -> dict:
    """
    Run backtest of the MA crossover strategy.
    
    Args:
        index_data: NASDAQ-100 index price data
        etf_data: TQQQ price data
        ma_period: Moving average period
        initial_capital: Starting capital
        use_leverage_decay: Whether to simulate 3x leverage decay
    
    Returns:
        dict with backtest results
    """
    # Align data
    # Handle multi-level columns
    if isinstance(index_data.columns, pd.MultiIndex):
        index_data.columns = index_data.columns.get_level_values(0)
    if isinstance(etf_data.columns, pd.MultiIndex):
        etf_data.columns = etf_data.columns.get_level_values(0)
    
    combined = pd.DataFrame({
        'index_close': index_data['Close'],
        'etf_close': etf_data['Close']
    }).dropna()
    
    # Calculate MA on index
    combined['sma'] = combined['index_close'].rolling(window=ma_period).mean()
    combined = combined.dropna()
    
    # Generate signals
    combined['above_ma'] = combined['index_close'] > combined['sma']
    combined['signal'] = combined['above_ma'].astype(int)  # 1 = long, 0 = cash
    
    # Calculate daily returns
    combined['etf_return'] = combined['etf_close'].pct_change()
    combined['strategy_return'] = combined['signal'].shift(1) * combined['etf_return']
    combined['buy_hold_return'] = combined['etf_return']
    
    # Remove first row (NaN from pct_change)
    combined = combined.dropna()
    
    # Calculate cumulative returns
    combined['strategy_cumulative'] = (1 + combined['strategy_return']).cumprod()
    combined['buy_hold_cumulative'] = (1 + combined['buy_hold_return']).cumprod()
    
    # Portfolio values
    combined['strategy_value'] = initial_capital * combined['strategy_cumulative']
    combined['buy_hold_value'] = initial_capital * combined['buy_hold_cumulative']
    
    # Calculate metrics
    results = calculate_metrics(combined, initial_capital)
    results['data'] = combined
    
    return results


def calculate_metrics(data: pd.DataFrame, initial_capital: float) -> dict:
    """Calculate performance metrics."""
    
    # Strategy metrics
    strategy_returns = data['strategy_return']
    final_value = data['strategy_value'].iloc[-1]
    
    # Total return
    total_return = (final_value - initial_capital) / initial_capital
    
    # Annualized return
    years = len(data) / 252
    annual_return = (1 + total_return) ** (1 / years) - 1
    
    # Volatility
    annual_vol = strategy_returns.std() * np.sqrt(252)
    
    # Sharpe Ratio (assuming 0% risk-free rate)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # Max Drawdown
    cumulative = data['strategy_cumulative']
    rolling_max = cumulative.expanding().max()
    drawdowns = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()
    
    # Win rate
    winning_days = (strategy_returns > 0).sum()
    total_days = (strategy_returns != 0).sum()
    win_rate = winning_days / total_days if total_days > 0 else 0
    
    # Trade count (signal changes)
    trades = (data['signal'] != data['signal'].shift(1)).sum()
    
    # Buy & Hold metrics for comparison
    bh_final = data['buy_hold_value'].iloc[-1]
    bh_total_return = (bh_final - initial_capital) / initial_capital
    bh_annual_return = (1 + bh_total_return) ** (1 / years) - 1
    
    bh_cumulative = data['buy_hold_cumulative']
    bh_rolling_max = bh_cumulative.expanding().max()
    bh_drawdowns = (bh_cumulative - bh_rolling_max) / bh_rolling_max
    bh_max_drawdown = bh_drawdowns.min()
    
    return {
        'start_date': data.index[0].strftime("%Y-%m-%d"),
        'end_date': data.index[-1].strftime("%Y-%m-%d"),
        'years': round(years, 2),
        'initial_capital': initial_capital,
        
        # Strategy metrics
        'final_value': round(final_value, 2),
        'total_return': round(total_return * 100, 2),
        'annual_return': round(annual_return * 100, 2),
        'annual_volatility': round(annual_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
        'win_rate': round(win_rate * 100, 2),
        'total_trades': trades,
        
        # Buy & Hold comparison
        'bh_final_value': round(bh_final, 2),
        'bh_total_return': round(bh_total_return * 100, 2),
        'bh_annual_return': round(bh_annual_return * 100, 2),
        'bh_max_drawdown': round(bh_max_drawdown * 100, 2),
    }


def print_results(results: dict):
    """Pretty print backtest results."""
    print("\n" + "="*60)
    print("📊 BACKTEST RESULTS - TQQQ 250-DAY MA STRATEGY")
    print("="*60)
    print(f"📅 Period: {results['start_date']} to {results['end_date']} ({results['years']} years)")
    print(f"💰 Initial Capital: ${results['initial_capital']:,.2f}")
    print()
    
    print("📈 STRATEGY PERFORMANCE:")
    print("-"*40)
    print(f"  Final Value:      ${results['final_value']:>15,.2f}")
    print(f"  Total Return:     {results['total_return']:>15.2f}%")
    print(f"  Annual Return:    {results['annual_return']:>15.2f}%")
    print(f"  Annual Volatility:{results['annual_volatility']:>15.2f}%")
    print(f"  Sharpe Ratio:     {results['sharpe_ratio']:>15.2f}")
    print(f"  Max Drawdown:     {results['max_drawdown']:>15.2f}%")
    print(f"  Win Rate:         {results['win_rate']:>15.2f}%")
    print(f"  Total Trades:     {results['total_trades']:>15}")
    print()
    
    print("📉 BUY & HOLD TQQQ (Comparison):")
    print("-"*40)
    print(f"  Final Value:      ${results['bh_final_value']:>15,.2f}")
    print(f"  Total Return:     {results['bh_total_return']:>15.2f}%")
    print(f"  Annual Return:    {results['bh_annual_return']:>15.2f}%")
    print(f"  Max Drawdown:     {results['bh_max_drawdown']:>15.2f}%")
    print()
    
    # Comparison
    outperformance = results['total_return'] - results['bh_total_return']
    dd_improvement = results['bh_max_drawdown'] - results['max_drawdown']
    
    print("⚡ STRATEGY vs BUY & HOLD:")
    print("-"*40)
    if outperformance > 0:
        print(f"  ✅ Strategy outperformed by {outperformance:.2f}%")
    else:
        print(f"  ❌ Strategy underperformed by {abs(outperformance):.2f}%")
    
    if dd_improvement > 0:
        print(f"  ✅ Drawdown reduced by {dd_improvement:.2f}%")
    else:
        print(f"  ❌ Drawdown increased by {abs(dd_improvement):.2f}%")
    
    print("="*60 + "\n")


def plot_results(results: dict, save_path: str = None):
    """Plot backtest results (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
        
        data = results['data']
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Plot 1: Portfolio Value
        axes[0].plot(data.index, data['strategy_value'], label='Strategy', linewidth=1.5)
        axes[0].plot(data.index, data['buy_hold_value'], label='Buy & Hold TQQQ', linewidth=1.5, alpha=0.7)
        axes[0].set_title('Portfolio Value Over Time')
        axes[0].set_ylabel('Value ($)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Index Price vs MA
        axes[1].plot(data.index, data['index_close'], label='NASDAQ-100', linewidth=1)
        axes[1].plot(data.index, data['sma'], label=f'{MA_PERIOD}-day SMA', linewidth=1.5)
        axes[1].fill_between(data.index, data['index_close'], data['sma'], 
                            where=data['above_ma'], alpha=0.3, color='green', label='Long Signal')
        axes[1].set_title('NASDAQ-100 vs 250-day MA')
        axes[1].set_ylabel('Price')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot 3: Drawdown
        cumulative = data['strategy_cumulative']
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max * 100
        
        axes[2].fill_between(data.index, 0, drawdown, color='red', alpha=0.5)
        axes[2].set_title('Strategy Drawdown')
        axes[2].set_ylabel('Drawdown (%)')
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"📊 Chart saved to {save_path}")
        else:
            plt.show()
            
    except ImportError:
        print("⚠️ matplotlib not installed. Run: pip install matplotlib")


if __name__ == "__main__":
    # Fetch data
    index_data = fetch_data(TICKER_INDEX, start="2010-01-01")
    etf_data = fetch_data(TICKER_LONG, start="2010-01-01")
    
    if index_data.empty or etf_data.empty:
        print("❌ Failed to fetch data")
        exit(1)
    
    # Run backtest
    print("\nRunning backtest...")
    results = run_backtest(index_data, etf_data)
    
    # Print results
    print_results(results)
    
    # Optional: Plot results
    try:
        plot_results(results, save_path="backtest_results.png")
    except Exception as e:
        print(f"⚠️ Could not generate plot: {e}")
