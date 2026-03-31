#!/usr/bin/env python3
"""
Sync Alpaca Positions to positions.json
=========================================

This tool syncs positions from Alpaca account into positions.json
Useful when positions exist in Alpaca but not in tracking file
"""

import json
import datetime as dt
from connect_real_trading import RealPaperTradingEngine

def sync_positions():
    """Sync positions from Alpaca to positions.json"""
    
    # Load existing positions
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
    except FileNotFoundError:
        positions = []
    
    # Get Alpaca positions
    engine = RealPaperTradingEngine()
    alpaca_positions = engine.get_positions()
    
    # Track which symbols are already tracked
    tracked_symbols = {p['symbol'] for p in positions if p.get('status') == 'entered'}
    
    print(f"\n📊 Alpaca Sync Report")
    print("=" * 80)
    print(f"Tracked positions: {len(tracked_symbols)}")
    print(f"Alpaca positions: {len(alpaca_positions)}")
    print()
    
    # Find positions in Alpaca but not tracked
    synced = 0
    for symbol, details in alpaca_positions.items():
        if symbol not in tracked_symbols:
            print(f"⚠️  Found untracked position: {symbol} ({details['quantity']:.0f} shares)")
            print(f"    Avg Cost: ${details['avg_cost']:.2f}")
            print(f"    Market Value: ${details['market_value']:.2f}")
            print(f"    Unrealized P&L: ${details['unrealized_pnl']:.2f}")
            
            # Add to positions.json
            today = dt.date.today()
            tomorrow = today + dt.timedelta(days=1)
            
            # Skip weekends
            while tomorrow.weekday() >= 5:
                tomorrow += dt.timedelta(days=1)
            
            new_position = {
                'symbol': symbol,
                'entry_date': today.isoformat(),
                'exit_date': tomorrow.isoformat(),
                'entry_price': details['avg_cost'],
                'position_size_shares': int(details['quantity']),
                'position_size_dollars': details['market_value'],
                'stop_price': details['avg_cost'] * 0.98,  # 2% stop
                'target_price': None,
                'status': 'entered',
                'max_risk_dollars': 100.0,
                'entry_timestamp': dt.datetime.now().isoformat(),
                'filled_at': None,  # Unknown for existing positions
                'order_id': None,
                'ai_signal': {
                    'action': 'BUY',
                    'confidence': 0.5,
                    'time_horizon_days': 1.5,
                    'entry_price': details['avg_cost'],
                    'target_price': None,
                    'features_used': {},
                    'timestamp': dt.datetime.now().isoformat()
                },
                'exit_price': None,
                'exit_reason': None,
                'realized_pnl': None
            }
            
            positions.append(new_position)
            synced += 1
            print(f"    ✅ Added to positions.json")
            print()
    
    if synced > 0:
        # Save updated positions
        with open('positions.json', 'w') as f:
            json.dump(positions, f, indent=2)
        
        print(f"\n✅ Synced {synced} positions from Alpaca")
        print(f"💾 Updated positions.json with {len(positions)} total positions")
    else:
        print(f"\n✅ All Alpaca positions are already tracked")
    
    print("=" * 80)

if __name__ == "__main__":
    sync_positions()
