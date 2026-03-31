#!/usr/bin/env python3
"""
Emergency Position Cleanup Script
Sync bot's positions.json with actual Alpaca positions and force close everything
"""

import sys
import json
import time
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

from connect_real_trading import RealPaperTradingEngine

def main():
    print("\n" + "="*80)
    print("EMERGENCY POSITION CLEANUP")
    print("="*80 + "\n")
    
    engine = RealPaperTradingEngine()
    
    # Step 1: Get all Alpaca positions
    print("Step 1: Checking Alpaca positions...")
    positions = engine.get_positions()
    
    if not positions:
        print("  ✅ No positions in Alpaca\n")
    else:
        print(f"  Found {len(positions)} positions:\n")
        for symbol, pos in positions.items():
            print(f"    {symbol}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f}")
        print()
        
        # Step 2: Close all positions using Alpaca's close_all_positions
        print("Step 2: Closing all positions via Alpaca API...")
        try:
            # Use Alpaca's built-in close all positions
            engine.client.close_all_positions(cancel_orders=True)
            print("  ✅ Close all positions command sent\n")
            
            time.sleep(3)
            
            # Verify
            remaining = engine.get_positions()
            if remaining:
                print(f"  ⚠️ Still have {len(remaining)} positions (may be pending close)")
            else:
                print("  ✅ All positions closed!\n")
                
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
    
    # Step 3: Clear positions.json
    print("Step 3: Clearing positions.json...")
    with open('/home/wes/Desktop/litebotx-usb-deployment/positions.json', 'w') as f:
        json.dump([], f, indent=2)
    print("  ✅ positions.json cleared\n")
    
    # Step 4: Final status
    print("="*80)
    print("FINAL STATUS")
    print("="*80 + "\n")
    
    account = engine.get_account_info()
    if account:
        print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
        print(f"Cash: ${account['cash']:.2f}")
        print(f"Buying Power: ${account['buying_power']:.2f}\n")
    
    positions = engine.get_positions()
    print(f"Active Positions: {len(positions)}\n")
    
    print("="*80)
    print("✅ CLEANUP COMPLETE - Bot ready to start fresh")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
