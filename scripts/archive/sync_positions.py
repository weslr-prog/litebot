#!/usr/bin/env python3
"""
Sync Local Positions with Alpaca
===============================

Synchronizes our local position tracking with actual Alpaca positions.
This ensures our bot doesn't try to manage phantom positions.
"""

import json
import sys
import logging
from datetime import datetime
from connect_real_trading import RealPaperTradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def sync_positions():
    """Sync local positions.json with actual Alpaca positions"""
    
    print("🔄 Syncing positions with Alpaca...")
    
    try:
        # Get actual Alpaca positions
        engine = RealPaperTradingEngine()
        alpaca_positions = engine.get_positions()
        
        print(f"📊 Found {len(alpaca_positions)} positions in Alpaca:")
        for symbol, data in alpaca_positions.items():
            print(f"  • {symbol}: {data['quantity']} shares @ ${data['avg_cost']:.2f}")
        
        # Load current local positions (for history)
        try:
            with open('positions.json', 'r') as f:
                local_positions = json.load(f)
        except FileNotFoundError:
            local_positions = []
        
        # Keep only closed positions for history
        historical_positions = [pos for pos in local_positions if pos.get('status') in ['stopped_out', 'closed', 'filled']]
        
        print(f"📚 Keeping {len(historical_positions)} historical positions")
        
        # Add current Alpaca positions as "entered" (since they exist in Alpaca)
        current_positions = []
        
        for symbol, data in alpaca_positions.items():
            # Create position entry matching our format
            position = {
                "symbol": symbol,
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
                "exit_date": None,
                "entry_price": data['avg_cost'],
                "position_size_shares": int(data['quantity']),
                "position_size_dollars": data['market_value'],
                "stop_price": None,  # Will be calculated by strategy
                "target_price": None,
                "status": "entered",  # Exists in Alpaca = entered
                "max_risk_dollars": None,
                "ai_signal": {
                    "action": "BUY",
                    "confidence": 0.5,  # Default for synced positions
                    "time_horizon_days": 1.0,
                    "entry_price": data['avg_cost'],
                    "target_price": None,
                    "features_used": {},
                    "timestamp": datetime.now().isoformat()
                },
                "exit_price": None,
                "exit_reason": None,
                "realized_pnl": None,
                "unrealized_pnl": data['unrealized_pnl'],
                "synced_from_alpaca": True  # Mark as synced
            }
            current_positions.append(position)
        
        # Combine historical + current
        all_positions = historical_positions + current_positions
        
        # Save updated positions
        with open('positions.json', 'w') as f:
            json.dump(all_positions, f, indent=2)
        
        print(f"✅ Sync complete!")
        print(f"   📚 Historical positions: {len(historical_positions)}")
        print(f"   📊 Current positions: {len(current_positions)}")
        print(f"   📋 Total in file: {len(all_positions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = sync_positions()
    sys.exit(0 if success else 1)