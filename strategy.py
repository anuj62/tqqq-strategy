#!/usr/bin/env python3
"""
TQQQ Trend Following Strategy
Based on 250-day moving average crossover of NASDAQ-100

Author: Khajack (github.com/anuj62)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import MA_PERIOD, TICKER_INDEX, TICKER_LONG, TICKER_SHORT


def get_data(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch historical data from Yahoo Finance."""
    data = yf.download(ticker, period=period, progress=False)
    return data


def calculate_sma(data: pd.DataFrame, period: int = MA_PERIOD) -> pd.Series:
    """Calculate Simple Moving Average."""
    return data['Close'].rolling(window=period).mean()


def get_signal(data: pd.DataFrame, ma_period: int = MA_PERIOD) -> dict:
    """
    Generate trading signal based on price vs moving average.
    
    Returns:
        dict with signal details
    """
    if len(data) < ma_period:
        return {"error": f"Need at least {ma_period} days of data"}
    
    data = data.copy()
    data['SMA'] = calculate_sma(data, ma_period)
    
    latest = data.iloc[-1]
    prev = data.iloc[-2]
    
    current_price = float(latest['Close'])
    current_sma = float(latest['SMA'])
    prev_price = float(prev['Close'])
    prev_sma = float(prev['SMA'])
    
    # Determine position
    above_ma = current_price > current_sma
    crossed_up = (current_price > current_sma) and (prev_price <= prev_sma)
    crossed_down = (current_price < current_sma) and (prev_price >= prev_sma)
    
    if above_ma:
        signal = "LONG"
        position = TICKER_LONG
        allocation = 1.0
    else:
        signal = "CASH"  # Or SHORT if you want to use SQQQ
        position = "CASH"
        allocation = 0.0
    
    return {
        "date": data.index[-1].strftime("%Y-%m-%d"),
        "ticker": TICKER_INDEX,
        "price": round(current_price, 2),
        "sma": round(current_sma, 2),
        "ma_period": ma_period,
        "above_ma": above_ma,
        "signal": signal,
        "position": position,
        "allocation": allocation,
        "crossed_up": crossed_up,
        "crossed_down": crossed_down,
        "distance_from_ma": round((current_price - current_sma) / current_sma * 100, 2),
    }


def get_position_size(signal: dict, portfolio_value: float) -> dict:
    """
    Calculate position size based on signal and portfolio value.
    
    Args:
        signal: Signal dict from get_signal()
        portfolio_value: Total portfolio value in USD
    
    Returns:
        dict with position sizing details
    """
    if signal.get("error"):
        return signal
    
    allocation = signal["allocation"]
    position_value = portfolio_value * allocation
    
    # Get current price of the position ticker
    if signal["position"] == "CASH":
        return {
            **signal,
            "portfolio_value": portfolio_value,
            "position_value": 0,
            "shares_to_hold": 0,
            "action": "HOLD CASH"
        }
    
    ticker_data = get_data(signal["position"], period="5d")
    if ticker_data.empty:
        return {"error": f"Could not fetch data for {signal['position']}"}
    
    ticker_price = float(ticker_data['Close'].iloc[-1])
    shares = int(position_value / ticker_price)
    
    return {
        **signal,
        "portfolio_value": portfolio_value,
        "position_value": round(position_value, 2),
        "ticker_price": round(ticker_price, 2),
        "shares_to_hold": shares,
        "action": f"HOLD {shares} shares of {signal['position']}"
    }


def print_signal(signal: dict):
    """Pretty print the signal."""
    if signal.get("error"):
        print(f"❌ Error: {signal['error']}")
        return
    
    print("\n" + "="*50)
    print("📊 TQQQ TREND STRATEGY - DAILY SIGNAL")
    print("="*50)
    print(f"📅 Date: {signal['date']}")
    print(f"📈 {signal['ticker']}: ${signal['price']}")
    print(f"📉 {signal['ma_period']}-day SMA: ${signal['sma']}")
    print(f"📏 Distance from MA: {signal['distance_from_ma']}%")
    print("-"*50)
    
    if signal['above_ma']:
        emoji = "🟢"
        status = "ABOVE"
    else:
        emoji = "🔴"
        status = "BELOW"
    
    print(f"{emoji} Price is {status} the {signal['ma_period']}-day MA")
    
    if signal.get('crossed_up'):
        print("⚡ CROSSOVER: Price crossed ABOVE MA - BUY SIGNAL")
    elif signal.get('crossed_down'):
        print("⚡ CROSSOVER: Price crossed BELOW MA - SELL SIGNAL")
    
    print("-"*50)
    print(f"🎯 SIGNAL: {signal['signal']}")
    print(f"💼 POSITION: {signal['position']}")
    print(f"📊 ALLOCATION: {signal['allocation']*100:.0f}%")
    
    if signal.get('shares_to_hold') is not None:
        print("-"*50)
        print(f"💰 Portfolio Value: ${signal['portfolio_value']:,.2f}")
        print(f"🎯 Action: {signal['action']}")
    
    print("="*50 + "\n")


if __name__ == "__main__":
    print("Fetching NASDAQ-100 data...")
    data = get_data(TICKER_INDEX)
    
    signal = get_signal(data)
    print_signal(signal)
    
    # Example with position sizing
    print("\n📊 Example with $100,000 portfolio:")
    sized_signal = get_position_size(signal, 100000)
    print_signal(sized_signal)
