#!/usr/bin/env python3
"""
EXTREME Aggressive Trading Launcher - 0.10 confidence with bypass filters
"""

import sys
import os
import time
from datetime import datetime, time as dt_time

# Add to path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def main():
    print("🚀 EXTREME Aggressive Trading Launcher")
    print("=====================================")
    
    # Create EXTREME aggressive config
    config = ShortCycleConfig(
        max_positions_per_day=10,
        daily_pool_percent=0.80,  # Increased from 60%
        max_risk_per_trade_dollars=100.0,  # Increased from 50
        min_position_size_dollars=10.0,   # Decreased from 15
        confidence_threshold=0.10,  # EXTREME - down from 0.20
        max_daily_loss_percent=0.002,  # Increased limit
        max_weekly_loss_percent=0.01,   # Increased limit
        max_hold_days=1,
        exit_time="15:50"
    )
    
    print(f"📊 EXTREME Aggressive Settings:")
    print(f"   Max positions: {config.max_positions_per_day}")
    print(f"   Confidence threshold: {config.confidence_threshold} ⚡ EXTREME LOW")
    print(f"   Daily pool: {config.daily_pool_percent*100:.0f}%")
    print(f"   Max risk per trade: ${config.max_risk_per_trade_dollars}")
    print(f"   Min position size: ${config.min_position_size_dollars}")
    
    # Initialize trader
    try:
        trader = ShortCycleTrader(config)
        
        # Get status
        portfolio_val = trader._get_portfolio_value()
        active_positions = [p for p in trader.positions if p.status.value == "entered"]
        
        print(f"\n💰 Portfolio: ${portfolio_val:,.2f}")
        print(f"📊 Active positions: {len(active_positions)}/{config.max_positions_per_day}")
        
        for pos in active_positions:
            print(f"   • {pos.symbol}: {pos.position_size_shares} shares @ ${pos.entry_price:.2f}")
        
        print(f"\n🔄 Starting EXTREME aggressive trading (0.10 confidence)...")
        print(f"🛑 Press Ctrl+C to stop")
        
        # Market hours
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        cycle_count = 0
        while True:
            now = datetime.now()
            
            # Check market hours
            if now.weekday() >= 5:  # Weekend
                print(f"😴 Weekend - sleeping 1 hour")
                time.sleep(3600)
                continue
                
            if not (market_open <= now.time() <= market_close):
                if now.time() < market_open:
                    print(f"😴 Pre-market - sleeping 5 minutes")
                else:
                    print(f"😴 After-hours - sleeping 1 hour")
                time.sleep(300 if now.time() < market_open else 3600)
                continue
            
            # Run trading cycle
            cycle_count += 1
            print(f"\n🔄 EXTREME Cycle #{cycle_count} at {now.strftime('%H:%M:%S')}")
            
            try:
                # Call the ACTUAL trading method that generates signals
                trader.run_daily_cycle()
                
                # Show current status
                portfolio_val = trader._get_portfolio_value()
                active_positions = [p for p in trader.positions if p.status.value == "entered"]
                
                print(f"💰 ${portfolio_val:,.0f} | Active: {len(active_positions)}/{config.max_positions_per_day}")
                print(f"📈 Trades today: {trader.trades_today}")
                
                # Show any new positions
                if len(active_positions) > 5:
                    new_positions = active_positions[5:]
                    print(f"🎯 NEW POSITIONS:")
                    for pos in new_positions:
                        print(f"   🆕 {pos.symbol}: {pos.position_size_shares} shares @ ${pos.entry_price:.2f}")
                
            except Exception as e:
                print(f"⚠️ Cycle error: {str(e)[:100]}...")
                import traceback
                traceback.print_exc()
            
            # Wait 30 seconds (faster cycles)
            print(f"⏱️ Waiting 30 seconds...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped by user")
        if 'trader' in locals():
            try:
                trader._save_positions()
                print(f"💾 Positions saved")
            except:
                print(f"⚠️ Could not save positions")
        print(f"✅ Session complete")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        if 'trader' in locals():
            try:
                trader._save_positions()
            except:
                pass

if __name__ == "__main__":
    main()