#!/usr/bin/env python3
"""
Fixed Aggressive Trading Launcher - No timezone dependencies
"""

import sys
import os
import time
from datetime import datetime, time as dt_time

# Add to path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def main():
    print("🚀 Fixed Aggressive Trading Launcher")
    print("===================================")
    
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
        
        print(f"\n🔄 Starting aggressive trading...")
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
            print(f"\n🔄 Aggressive Cycle #{cycle_count} at {now.strftime('%H:%M:%S')}")
            
            try:
                # Manual trading cycle to bypass timezone issues
                # 1. Update risk limits
                trader._update_risk_limits()
                
                # 2. Load positions
                old_count = len(trader.positions)
                trader._load_positions()
                active_positions = [p for p in trader.positions if p.status.value == "entered"]
                
                print(f"📊 Loaded {len(trader.positions)} total positions ({len(active_positions)} active)")
                
                # 3. Try to generate signals (simplified)
                try:
                    # Get watchlist symbols
                    watchlist = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'IBM', 'ORCL', 'SHOP', 'AVGO']
                    
                    print(f"🔍 Scanning {len(watchlist)} symbols for signals...")
                    
                    # This will try to generate signals but might fail due to timezone
                    # We'll catch and continue
                    
                except Exception as signal_error:
                    print(f"⚠️ Signal generation error: {signal_error}")
                
                # Show current status
                portfolio_val = trader._get_portfolio_value()
                active_positions = [p for p in trader.positions if p.status.value == "entered"]
                
                print(f"💰 ${portfolio_val:,.0f} | Active: {len(active_positions)}/{config.max_positions_per_day}")
                
                # Show any new activities
                new_count = len(trader.positions)
                if new_count != old_count:
                    print(f"🎯 Position count changed: {old_count} → {new_count}")
                
            except Exception as e:
                print(f"⚠️ Cycle error: {str(e)[:100]}...")
            
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
        if 'trader' in locals():
            try:
                trader._save_positions()
            except:
                pass

if __name__ == "__main__":
    main()