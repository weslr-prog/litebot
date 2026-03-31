#!/usr/bin/env python3
"""
Working Aggressive Trading Launcher - Actually calls signal generation
"""

import sys
import os
import time
from datetime import datetime, time as dt_time

# Add to path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def main():
    print("🚀 Working Aggressive Trading Launcher")
    print("=====================================")
    
    # Create aggressive config
    config = ShortCycleConfig(
        max_positions_per_day=10,
        daily_pool_percent=0.60,
        max_risk_per_trade_dollars=50.0,
        min_position_size_dollars=15.0,
        confidence_threshold=0.40,  # Very aggressive
        max_daily_loss_percent=0.001,  # 0.1%
        max_weekly_loss_percent=0.005,  # 0.5%
        max_hold_days=1,
        exit_time="15:50"
    )
    
    print(f"📊 Aggressive Settings:")
    print(f"   Max positions: {config.max_positions_per_day}")
    print(f"   Confidence threshold: {config.confidence_threshold}")
    print(f"   Daily pool: {config.daily_pool_percent*100:.0f}%")
    print(f"   Daily loss limit: {config.max_daily_loss_percent*100:.2f}%")
    
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
        
        print(f"\n🔄 Starting aggressive trading with REAL signal generation...")
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
            print(f"\n🔄 REAL Trading Cycle #{cycle_count} at {now.strftime('%H:%M:%S')}")
            
            try:
                # Call the ACTUAL trading method that generates signals
                trader.run_daily_cycle()
                
                # Show current status
                portfolio_val = trader._get_portfolio_value()
                active_positions = [p for p in trader.positions if p.status.value == "entered"]
                
                print(f"💰 ${portfolio_val:,.0f} | Active: {len(active_positions)}/{config.max_positions_per_day}")
                print(f"📈 Trades today: {trader.trades_today}")
                
            except Exception as e:
                print(f"⚠️ Cycle error: {str(e)[:100]}...")
                import traceback
                traceback.print_exc()
            
            # Wait 60 seconds
            print(f"⏱️ Waiting 60 seconds...")
            time.sleep(60)
            
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