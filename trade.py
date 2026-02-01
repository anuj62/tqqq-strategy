#!/usr/bin/env python3
"""
Live/Paper Trading with Alpaca

Executes the TQQQ trend strategy with real or paper money.
"""

import os
import argparse
from datetime import datetime
from strategy import get_data, get_signal
from config import (
    TICKER_INDEX, TICKER_LONG, TICKER_SHORT,
    ALPACA_BASE_URL_PAPER, ALPACA_BASE_URL_LIVE,
    USE_SHORTS
)

# Check for Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


def get_alpaca_client(paper: bool = True) -> 'TradingClient':
    """Get Alpaca trading client."""
    if not ALPACA_AVAILABLE:
        raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")
    
    api_key = os.environ.get('ALPACA_API_KEY')
    secret_key = os.environ.get('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError(
            "Alpaca credentials not found. Set environment variables:\n"
            "  export ALPACA_API_KEY='your_key'\n"
            "  export ALPACA_SECRET_KEY='your_secret'"
        )
    
    return TradingClient(api_key, secret_key, paper=paper)


def get_account_info(client: 'TradingClient') -> dict:
    """Get account information."""
    account = client.get_account()
    return {
        'equity': float(account.equity),
        'cash': float(account.cash),
        'buying_power': float(account.buying_power),
        'portfolio_value': float(account.portfolio_value),
    }


def get_current_positions(client: 'TradingClient') -> dict:
    """Get current positions."""
    positions = client.get_all_positions()
    return {
        pos.symbol: {
            'qty': int(pos.qty),
            'market_value': float(pos.market_value),
            'avg_entry': float(pos.avg_entry_price),
            'unrealized_pl': float(pos.unrealized_pl),
        }
        for pos in positions
    }


def execute_trade(
    client: 'TradingClient',
    symbol: str,
    qty: int,
    side: str,
    dry_run: bool = False
) -> dict:
    """Execute a market order."""
    if dry_run:
        return {
            'status': 'DRY_RUN',
            'symbol': symbol,
            'qty': qty,
            'side': side,
        }
    
    order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
    
    order_request = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=order_side,
        time_in_force=TimeInForce.DAY
    )
    
    order = client.submit_order(order_request)
    
    return {
        'status': 'SUBMITTED',
        'order_id': order.id,
        'symbol': order.symbol,
        'qty': order.qty,
        'side': order.side,
        'type': order.type,
    }


def calculate_target_position(signal: dict, portfolio_value: float, current_price: float) -> int:
    """Calculate target number of shares."""
    target_value = portfolio_value * signal['allocation']
    target_shares = int(target_value / current_price)
    return target_shares


def run_strategy(paper: bool = True, dry_run: bool = False):
    """Run the trading strategy."""
    print("\n" + "="*60)
    print(f"🤖 TQQQ TREND STRATEGY - {'PAPER' if paper else 'LIVE'} TRADING")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Get signal
    print("\n📊 Fetching market data...")
    data = get_data(TICKER_INDEX)
    signal = get_signal(data)
    
    if signal.get('error'):
        print(f"❌ Error: {signal['error']}")
        return
    
    print(f"\n🎯 Signal: {signal['signal']}")
    print(f"   NDX: ${signal['price']} | SMA: ${signal['sma']}")
    print(f"   Distance from MA: {signal['distance_from_ma']}%")
    
    # Connect to Alpaca
    print("\n🔗 Connecting to Alpaca...")
    try:
        client = get_alpaca_client(paper=paper)
    except (ImportError, ValueError) as e:
        print(f"❌ {e}")
        return
    
    # Get account info
    account = get_account_info(client)
    print(f"\n💰 Account:")
    print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"   Cash: ${account['cash']:,.2f}")
    
    # Get current positions
    positions = get_current_positions(client)
    print(f"\n📦 Current Positions:")
    if positions:
        for symbol, pos in positions.items():
            print(f"   {symbol}: {pos['qty']} shares (${pos['market_value']:,.2f})")
    else:
        print("   No positions")
    
    # Determine target position
    target_ticker = TICKER_LONG if signal['signal'] == 'LONG' else None
    
    if signal['signal'] == 'SHORT' and USE_SHORTS:
        target_ticker = TICKER_SHORT
    
    # Get current TQQQ/SQQQ position
    current_tqqq = positions.get(TICKER_LONG, {}).get('qty', 0)
    current_sqqq = positions.get(TICKER_SHORT, {}).get('qty', 0)
    
    print(f"\n🎯 Target Position:")
    
    if target_ticker == TICKER_LONG:
        # Get TQQQ price
        tqqq_data = get_data(TICKER_LONG, period="5d")
        tqqq_price = float(tqqq_data['Close'].iloc[-1])
        
        target_shares = calculate_target_position(signal, account['portfolio_value'], tqqq_price)
        shares_to_trade = target_shares - current_tqqq
        
        print(f"   {TICKER_LONG}: {target_shares} shares (currently have {current_tqqq})")
        
        # Close any SQQQ position first
        if current_sqqq > 0:
            print(f"\n⚡ Closing {TICKER_SHORT} position...")
            result = execute_trade(client, TICKER_SHORT, current_sqqq, 'sell', dry_run)
            print(f"   {result}")
        
        # Buy/sell TQQQ to target
        if shares_to_trade > 0:
            print(f"\n⚡ Buying {shares_to_trade} shares of {TICKER_LONG}...")
            result = execute_trade(client, TICKER_LONG, shares_to_trade, 'buy', dry_run)
            print(f"   {result}")
        elif shares_to_trade < 0:
            print(f"\n⚡ Selling {abs(shares_to_trade)} shares of {TICKER_LONG}...")
            result = execute_trade(client, TICKER_LONG, abs(shares_to_trade), 'sell', dry_run)
            print(f"   {result}")
        else:
            print("\n✅ Already at target position")
            
    elif target_ticker == TICKER_SHORT:
        # Similar logic for short position
        sqqq_data = get_data(TICKER_SHORT, period="5d")
        sqqq_price = float(sqqq_data['Close'].iloc[-1])
        
        target_shares = calculate_target_position(signal, account['portfolio_value'], sqqq_price)
        shares_to_trade = target_shares - current_sqqq
        
        print(f"   {TICKER_SHORT}: {target_shares} shares (currently have {current_sqqq})")
        
        # Close TQQQ first
        if current_tqqq > 0:
            print(f"\n⚡ Closing {TICKER_LONG} position...")
            result = execute_trade(client, TICKER_LONG, current_tqqq, 'sell', dry_run)
            print(f"   {result}")
        
        if shares_to_trade > 0:
            print(f"\n⚡ Buying {shares_to_trade} shares of {TICKER_SHORT}...")
            result = execute_trade(client, TICKER_SHORT, shares_to_trade, 'buy', dry_run)
            print(f"   {result}")
            
    else:  # CASH
        print("   CASH (no position)")
        
        # Close all positions
        if current_tqqq > 0:
            print(f"\n⚡ Selling all {TICKER_LONG}...")
            result = execute_trade(client, TICKER_LONG, current_tqqq, 'sell', dry_run)
            print(f"   {result}")
        
        if current_sqqq > 0:
            print(f"\n⚡ Selling all {TICKER_SHORT}...")
            result = execute_trade(client, TICKER_SHORT, current_sqqq, 'sell', dry_run)
            print(f"   {result}")
        
        if current_tqqq == 0 and current_sqqq == 0:
            print("\n✅ Already in cash")
    
    print("\n" + "="*60)
    print("✅ Strategy execution complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TQQQ Trend Strategy Trader')
    parser.add_argument('--paper', action='store_true', default=True,
                       help='Use paper trading (default: True)')
    parser.add_argument('--live', action='store_true',
                       help='Use live trading (WARNING: real money!)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate trades without executing')
    
    args = parser.parse_args()
    
    paper = not args.live
    
    if not paper:
        print("\n⚠️  WARNING: LIVE TRADING MODE ⚠️")
        print("This will execute real trades with real money!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("Aborted.")
            exit(0)
    
    run_strategy(paper=paper, dry_run=args.dry_run)
