#!/usr/bin/env python3
"""
Aggressive Trading Configuration for Today
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def create_aggressive_config():
    """Create more aggressive trading config for today"""
    
    # Aggressive settings for more active trading
    config = ShortCycleConfig(
        # More positions and larger position sizes
        max_positions_per_day=10,              # Up from 6 to 10
        daily_pool_percent=0.60,               # Up from 45% to 60% of portfolio
        max_risk_per_trade_dollars=50.0,       # Up from $25 to $50
        min_position_size_dollars=15.0,        # Down from $25 to $15 (smaller positions OK)
        max_position_size_percent=0.25,        # Up from 20% to 25%
        
        # Lower confidence threshold for more signals
        confidence_threshold=0.40,             # Down from 0.50 to 0.40 (more signals)
        
        # Looser risk limits for more activity
        max_daily_loss_percent=0.001,          # Up from 0.0005 to 0.001 (0.1% = ~$963)
        max_weekly_loss_percent=0.005,         # Up from 0.002 to 0.005 (0.5% = ~$4,817)
        
        # Keep short holding periods for day trading style
        max_hold_days=1,                       # Same day exits when possible
        exit_time="15:50"                      # Exit closer to market close
    )
    
    return config

if __name__ == "__main__":
    print("🔥 Creating aggressive trading configuration for today...")
    
    config = create_aggressive_config()
    
    print(f"📊 Aggressive Settings:")
    print(f"   Max positions: {config.max_positions_per_day}")
    print(f"   Daily pool: {config.daily_pool_percent*100:.0f}% of portfolio")
    print(f"   Confidence threshold: {config.confidence_threshold}")
    print(f"   Min position size: ${config.min_position_size_dollars}")
    print(f"   Max risk per trade: ${config.max_risk_per_trade_dollars}")
    print(f"   Daily loss limit: {config.max_daily_loss_percent*100:.2f}%")
    
    # Start trader with aggressive config
    print(f"\n🚀 Starting aggressive trader...")
    trader = ShortCycleTrader(config)
    
    # Show current status
    portfolio_val = trader._get_portfolio_value()
    open_positions = len([p for p in trader.positions if p.status.value == "entered"])
    
    print(f"💰 Portfolio: ${portfolio_val:,.2f}")
    print(f"📊 Current positions: {open_positions}/{config.max_positions_per_day}")
    print(f"💵 Daily pool available: ${portfolio_val * config.daily_pool_percent:,.0f}")
    print(f"🎯 Daily loss limit: ${portfolio_val * config.max_daily_loss_percent:,.0f}")
    
    print(f"\n✅ Ready for aggressive trading!")
    print(f"🔄 Bot will look for signals every minute...")
    
    # Run continuous trading with aggressive settings
    try:
        import time
        from datetime import datetime, time as dt_time
        
        print(f"\n🔥 Starting aggressive continuous trading...")
        print(f"🛑 Press Ctrl+C to stop")
        
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        while True:
            now = datetime.now()
            current_time = now.time()
            
            # Only trade during market hours
            if now.weekday() < 5 and market_open <= current_time <= market_close:
                print(f"\n🔄 Aggressive trading cycle at {now.strftime('%H:%M:%S')}")
                
                # Run trading cycle
                trader.run_daily_cycle()
                
                # Show current status
                portfolio_val = trader._get_portfolio_value()
                open_positions = len([p for p in trader.positions if p.status.value == "entered"])
                
                print(f"💰 Portfolio: ${portfolio_val:,.0f} | Positions: {open_positions}/{config.max_positions_per_day}")
                
            else:
                if now.weekday() >= 5:
                    print(f"😴 Weekend - sleeping until Monday...")
                    time.sleep(3600)  # Sleep 1 hour
                else:
                    print(f"😴 Market closed - sleeping until 9:30 AM...")
                    time.sleep(300)   # Sleep 5 minutes
                continue
            
            # Wait 60 seconds between cycles
            time.sleep(60)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Aggressive trading stopped by user")
        print(f"💾 Saving final state...")
        trader._save_positions()
        print(f"✅ Session complete!")
    
    except Exception as e:
        print(f"❌ Error in aggressive trading: {e}")
        trader._save_positions()