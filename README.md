# TQQQ Trend Following Strategy

A simple, automated trend-following strategy based on the 250-day moving average crossover.

**Inspired by:** Malik's $700K automated trading strategy (MaletTQQQ on Kinfo)

## Strategy Overview

- **Instruments:** TQQQ (3x long NASDAQ) and SQQQ (3x short NASDAQ)
- **Signal:** NASDAQ-100 (NDX) vs 250-day Simple Moving Average
- **Execution:** End of day (last 10 minutes of trading)
- **Frequency:** ~1-2 trades per week

### Rules

| Condition | Action |
|-----------|--------|
| NDX closes **above** 250-day SMA | Hold 100% TQQQ |
| NDX closes **below** 250-day SMA | Exit to cash (or hold SQQQ for shorts) |

### The Edge

> "It's mathematically impossible for a sustained rally without being above the 50/250-day moving average."

This strategy captures major trends while avoiding prolonged drawdowns.

## Backtested Performance (1985-2025)

- **Annual Return:** ~40-80%
- **Max Drawdown:** ~30%
- **Win Rate:** High (rides trends for months/years)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Check Current Signal
```bash
python strategy.py
```

### Run Backtest
```bash
python backtest.py
```

### Paper Trade with Alpaca
```bash
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
python trade.py --paper
```

## Files

- `strategy.py` - Core strategy logic and signal generation
- `backtest.py` - Historical backtesting with performance metrics
- `trade.py` - Live/paper trading with Alpaca integration
- `config.py` - Configuration settings

## Disclaimer

This is for educational purposes only. Trading leveraged ETFs involves significant risk. Past performance does not guarantee future results. Do your own research.

## License

MIT
