"""
Configuration for TQQQ Trend Strategy
"""

# Moving Average Settings
MA_PERIOD = 250  # 250-day SMA (roughly 1 trading year)
MA_PERIOD_SHORT = 50  # Optional: 50-day SMA for additional confirmation

# Tickers
TICKER_INDEX = "^NDX"  # NASDAQ-100 Index
TICKER_LONG = "TQQQ"   # 3x Long NASDAQ ETF
TICKER_SHORT = "SQQQ"  # 3x Short NASDAQ ETF
TICKER_UNDERLYING = "QQQ"  # 1x NASDAQ ETF (for reference)

# Trading Settings
EXECUTION_TIME = "15:50"  # Execute in last 10 minutes (3:50 PM ET)
MIN_POSITION_CHANGE = 0.05  # Minimum 5% change to rebalance

# Risk Management
MAX_POSITION_SIZE = 1.0  # Max 100% allocation
USE_SHORTS = False  # Whether to go short with SQQQ or just hold cash

# Alpaca Settings (for live/paper trading)
ALPACA_PAPER = True  # Use paper trading by default
ALPACA_BASE_URL_PAPER = "https://paper-api.alpaca.markets"
ALPACA_BASE_URL_LIVE = "https://api.alpaca.markets"

# Data Settings
DATA_SOURCE = "yfinance"  # or "polygon" for more reliable data
POLYGON_API_KEY = None  # Set via environment variable POLYGON_API_KEY
