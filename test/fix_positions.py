#!/usr/bin/env python3
"""
Enhanced position sync with better error handling
"""

import json
import sys
from datetime import datetime
from connect_real_trading import RealPaperTradingEngine

def fix_positions():
    """Fix position data to prevent NoneType errors"""
    
    print("🔧 Fixing position data...")
    
    try:
        # Load current positions
        with open('positions.json', 'r') as f:
            positions = json.load(f)
        
        fixed_positions = []
        
        for pos in positions:
            # Fix any None values that cause errors
            if pos.get('stop_price') is None:
                # Calculate a reasonable stop price (2% below entry)
                entry_price = pos.get('entry_price', 0)
                if entry_price > 0:
                    pos['stop_price'] = entry_price * 0.98
                else:
                    pos['stop_price'] = 0
            
            if pos.get('exit_price') is None:
                pos['exit_price'] = 0  # Will be updated when position exits
                
            if pos.get('realized_pnl') is None:
                pos['realized_pnl'] = 0
                
            if pos.get('unrealized_pnl') is None:
                pos['unrealized_pnl'] = 0
                
            if pos.get('max_risk_dollars') is None:
                # Set reasonable risk amount
                pos_value = pos.get('position_size_dollars', 0)
                pos['max_risk_dollars'] = pos_value * 0.02  # 2% risk
            
            fixed_positions.append(pos)
        
        # Save fixed positions
        with open('positions.json', 'w') as f:
            json.dump(fixed_positions, f, indent=2)
            
        print(f"✅ Fixed {len(fixed_positions)} positions")
        
        # Show current active positions
        active = [p for p in fixed_positions if p.get('status') == 'entered']
        print(f"📊 Active positions: {len(active)}")
        for pos in active:
            symbol = pos['symbol']
            shares = pos.get('position_size_shares', 0)
            entry_price = pos.get('entry_price', 0)
            print(f"  • {symbol}: {shares} shares @ ${entry_price:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_positions()
    sys.exit(0 if success else 1)