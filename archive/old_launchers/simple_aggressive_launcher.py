#!/usr/bin/env python3
"""
Simple Aggressive Trading Launcher - Bypasses timezone issues
"""

import sys
import os
import time
from datetime import datetime, time as dt_time

# Set timezone environment
os.environ['TZ'] = 'America/New_York'

# Add to path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def main():
    print("🚀 Simple Aggressive Trading Launcher")
    print("=====================================")
    
    # Create aggressive config
    config = ShortCycleConfig(
        max_positions_per_day=10,
        daily_pool_percent=0.60,
        max_risk_per_trade_dollars=50.0,
        min_position_size_dollars=15.0,
        confidence_threshold=0.40,
        max_daily_loss_percent=0.001,  # 0.1%
        max_weekly_loss_percent=0.005,  # 0.5%
        max_hold_days=1,
        exit_time="15:50"
    )
    
    print(f"📊 Config: {config.max_positions_per_day} positions, {config.confidence_threshold} confidence")
    
    # Initialize trader
    try:
        trader = ShortCycleTrader(config)
        
        # Get status
        portfolio_val = trader._get_portfolio_value()
        active_positions = [p for p in trader.positions if p.status.value == "entered"]
        
        print(f"💰 Portfolio: ${portfolio_val:,.2f}")
        print(f"📊 Active positions: {len(active_positions)}/{config.max_positions_per_day}")
        
        for pos in active_positions:
            print(f"   • {pos.symbol}: {pos.position_size_shares} shares @ ${pos.entry_price:.2f}")
        
        print(f"\n🔄 Starting trading cycles...")
        
        # Market hours
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        cycle_count = 0
        while True:
            now = datetime.now()
            
            # Check market hours
            if now.weekday() >= 5:  # Weekend
                print(f"😴 Weekend - next check in 1 hour")
                time.sleep(3600)
                continue
                
            if not (market_open <= now.time() <= market_close):
                print(f"😴 Market closed - next check in 5 minutes")
                time.sleep(300)
                continue
            
            # Run trading cycle
            cycle_count += 1
            print(f"\n🔄 Cycle #{cycle_count} at {now.strftime('%H:%M:%S')}")
            
            try:
                # Simple trading cycle without complex error handling
                trader.run_daily_cycle()
                
                # Show results
                portfolio_val = trader._get_portfolio_value()
                active_positions = [p for p in trader.positions if p.status.value == "entered"]
                
                print(f"💰 ${portfolio_val:,.0f} | Positions: {len(active_positions)}/{config.max_positions_per_day}")
                
            except Exception as e:
                print(f"⚠️ Cycle error (continuing): {e}")
            
            # Wait 60 seconds
            time.sleep(60)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped by user")
        if 'trader' in locals():
            trader._save_positions()
        print(f"✅ Session complete")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        if 'trader' in locals():
            trader._save_positions()

if __name__ == "__main__":
    main()