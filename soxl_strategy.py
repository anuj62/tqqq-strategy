#!/usr/bin/env python3
"""
SOXL/SOXS Semiconductor Trend Strategy

Semiconductors are more volatile and cyclical than NASDAQ.
This strategy uses:
1. 200-day MA for primary trend direction
2. 50-day MA for momentum confirmation
3. Rate of change filter to avoid choppy markets

Author: Khajack (github.com/anuj62)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


# Configuration
TICKER_INDEX = "^SOX"      # PHLX Semiconductor Index
TICKER_LONG = "SOXL"       # 3x Long Semiconductors
TICKER_SHORT = "SOXS"      # 3x Short Semiconductors
MA_LONG = 200              # Long-term trend
MA_SHORT = 50              # Short-term momentum
ROC_PERIOD = 20            # Rate of change lookback
ROC_THRESHOLD = 0.02       # 2% minimum momentum to enter


def get_data(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance."""
    data = yf.download(ticker, period=period, progress=False)
    return data


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators."""
    df = data.copy()
    
    # Moving averages
    df['SMA_200'] = df['Close'].rolling(window=MA_LONG).mean()
    df['SMA_50'] = df['Close'].rolling(window=MA_SHORT).mean()
    
    # Rate of change (momentum)
    df['ROC'] = df['Close'].pct_change(periods=ROC_PERIOD)
    
    # Volatility (for position sizing)
    df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)
    
    # Trend strength (distance from 200 MA as %)
    df['Trend_Strength'] = (df['Close'] - df['SMA_200']) / df['SMA_200']
    
    return df


def get_signal(data: pd.DataFrame) -> dict:
    """
    Generate trading signal for SOXL/SOXS.
    
    Strategy Rules:
    - LONG (SOXL): Price > 200 MA AND Price > 50 MA AND ROC > threshold
    - SHORT (SOXS): Price < 200 MA AND Price < 50 MA AND ROC < -threshold
    - CASH: Otherwise (choppy/uncertain market)
    
    Position Sizing:
    - Full position when trend is strong
    - Reduced position in high volatility
    """
    df = calculate_indicators(data)
    
    if len(df) < MA_LONG:
        return {"error": f"Need at least {MA_LONG} days of data"}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    price = float(latest['Close'])
    sma_200 = float(latest['SMA_200'])
    sma_50 = float(latest['SMA_50'])
    roc = float(latest['ROC'])
    volatility = float(latest['Volatility'])
    trend_strength = float(latest['Trend_Strength'])
    
    # Determine trend
    above_200 = price > sma_200
    above_50 = price > sma_50
    below_200 = price < sma_200
    below_50 = price < sma_50
    
    # Momentum confirmation
    strong_up_momentum = roc > ROC_THRESHOLD
    strong_down_momentum = roc < -ROC_THRESHOLD
    
    # Signal logic
    if above_200 and above_50 and strong_up_momentum:
        signal = "LONG"
        position = TICKER_LONG
        allocation = calculate_position_size(trend_strength, volatility, bullish=True)
    elif below_200 and below_50 and strong_down_momentum:
        signal = "SHORT"
        position = TICKER_SHORT
        allocation = calculate_position_size(abs(trend_strength), volatility, bullish=False)
    else:
        signal = "CASH"
        position = "CASH"
        allocation = 0.0
    
    # Detect crossovers
    prev_above_200 = float(prev['Close']) > float(prev['SMA_200'])
    crossed_up_200 = above_200 and not prev_above_200
    crossed_down_200 = not above_200 and prev_above_200
    
    return {
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "ticker": TICKER_INDEX,
        "price": round(price, 2),
        "sma_200": round(sma_200, 2),
        "sma_50": round(sma_50, 2),
        "roc": round(roc * 100, 2),  # As percentage
        "volatility": round(volatility * 100, 2),  # Annualized %
        "trend_strength": round(trend_strength * 100, 2),
        "above_200_ma": above_200,
        "above_50_ma": above_50,
        "signal": signal,
        "position": position,
        "allocation": round(allocation, 2),
        "crossed_up_200": crossed_up_200,
        "crossed_down_200": crossed_down_200,
        "regime": get_market_regime(above_200, above_50, roc),
    }


def calculate_position_size(trend_strength: float, volatility: float, bullish: bool) -> float:
    """
    Dynamic position sizing based on trend strength and volatility.
    
    - Stronger trend = larger position
    - Higher volatility = smaller position (risk management)
    """
    # Base allocation
    base = 1.0
    
    # Trend strength multiplier (0.5 to 1.0)
    trend_mult = min(1.0, 0.5 + abs(trend_strength) * 2)
    
    # Volatility adjustment (reduce size if vol > 50% annualized)
    if volatility > 0.50:
        vol_mult = 0.5
    elif volatility > 0.35:
        vol_mult = 0.75
    else:
        vol_mult = 1.0
    
    allocation = base * trend_mult * vol_mult
    
    # Cap at 100%
    return min(1.0, allocation)


def get_market_regime(above_200: bool, above_50: bool, roc: float) -> str:
    """Classify current market regime."""
    if above_200 and above_50:
        if roc > 0.05:
            return "STRONG_UPTREND"
        elif roc > 0:
            return "UPTREND"
        else:
            return "WEAKENING_UPTREND"
    elif not above_200 and not above_50:
        if roc < -0.05:
            return "STRONG_DOWNTREND"
        elif roc < 0:
            return "DOWNTREND"
        else:
            return "WEAKENING_DOWNTREND"
    else:
        return "TRANSITION"


def print_signal(signal: dict):
    """Pretty print the signal."""
    if signal.get("error"):
        print(f"❌ Error: {signal['error']}")
        return
    
    print("\n" + "="*55)
    print("🔧 SOXL/SOXS SEMICONDUCTOR STRATEGY - DAILY SIGNAL")
    print("="*55)
    print(f"📅 Date: {signal['date']}")
    print(f"📈 SOX Index: ${signal['price']}")
    print("-"*55)
    
    # Indicators
    print("📊 INDICATORS:")
    print(f"   200-day MA: ${signal['sma_200']} {'🟢 Above' if signal['above_200_ma'] else '🔴 Below'}")
    print(f"   50-day MA:  ${signal['sma_50']} {'🟢 Above' if signal['above_50_ma'] else '🔴 Below'}")
    print(f"   Momentum (ROC): {signal['roc']}%")
    print(f"   Volatility: {signal['volatility']}% (annualized)")
    print(f"   Trend Strength: {signal['trend_strength']}%")
    print("-"*55)
    
    # Regime
    regime_emoji = {
        "STRONG_UPTREND": "🚀",
        "UPTREND": "📈",
        "WEAKENING_UPTREND": "📉",
        "STRONG_DOWNTREND": "💥",
        "DOWNTREND": "📉",
        "WEAKENING_DOWNTREND": "📈",
        "TRANSITION": "⚖️",
    }
    print(f"🌡️ Market Regime: {regime_emoji.get(signal['regime'], '❓')} {signal['regime']}")
    
    # Crossovers
    if signal.get('crossed_up_200'):
        print("⚡ ALERT: Price crossed ABOVE 200-day MA!")
    elif signal.get('crossed_down_200'):
        print("⚡ ALERT: Price crossed BELOW 200-day MA!")
    
    print("-"*55)
    
    # Signal
    signal_emoji = {"LONG": "🟢", "SHORT": "🔴", "CASH": "⚪"}
    print(f"🎯 SIGNAL: {signal_emoji.get(signal['signal'], '❓')} {signal['signal']}")
    print(f"💼 POSITION: {signal['position']}")
    print(f"📊 ALLOCATION: {signal['allocation']*100:.0f}%")
    
    # Reasoning
    print("-"*55)
    print("📝 REASONING:")
    if signal['signal'] == "LONG":
        print("   ✓ Price above both 200 & 50 day MAs (uptrend)")
        print("   ✓ Positive momentum confirms trend")
        print(f"   → Go long SOXL at {signal['allocation']*100:.0f}% allocation")
    elif signal['signal'] == "SHORT":
        print("   ✓ Price below both 200 & 50 day MAs (downtrend)")
        print("   ✓ Negative momentum confirms trend")
        print(f"   → Go short via SOXS at {signal['allocation']*100:.0f}% allocation")
    else:
        print("   ⚠ Mixed signals or weak momentum")
        print("   → Stay in cash, wait for clearer trend")
    
    print("="*55 + "\n")


def compare_to_tqqq():
    """Compare SOX vs NDX signals."""
    print("\n📊 COMPARING SEMICONDUCTOR vs NASDAQ SIGNALS\n")
    
    # Get both indices
    sox_data = get_data("^SOX")
    ndx_data = get_data("^NDX")
    
    sox_signal = get_signal(sox_data)
    
    # Simple NDX signal
    ndx_df = ndx_data.copy()
    ndx_df['SMA_200'] = ndx_df['Close'].rolling(200).mean()
    ndx_latest = ndx_df.iloc[-1]
    ndx_above_ma = float(ndx_latest['Close']) > float(ndx_latest['SMA_200'])
    
    print(f"{'Index':<15} {'Price':>10} {'200 MA':>10} {'Signal':>10}")
    print("-" * 50)
    print(f"{'SOX (Semis)':<15} ${sox_signal['price']:>8} ${sox_signal['sma_200']:>8} {sox_signal['signal']:>10}")
    print(f"{'NDX (Nasdaq)':<15} ${float(ndx_latest['Close']):>8.0f} ${float(ndx_latest['SMA_200']):>8.0f} {'LONG' if ndx_above_ma else 'CASH':>10}")
    
    print("\n💡 Note: Semiconductors often lead NASDAQ at turning points!")


if __name__ == "__main__":
    print("Fetching SOX Semiconductor Index data...")
    data = get_data(TICKER_INDEX)
    
    signal = get_signal(data)
    print_signal(signal)
    
    # Compare to NASDAQ
    compare_to_tqqq()
