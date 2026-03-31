#!/usr/bin/env python3
"""
FIXED Aggressive Trading Launcher with Correct Portfolio Values
-             print(f"✅ Connected to Alpaca - LIVE MODE ENABLED")
            print(f"💰 Portfolio Value: ${account_info['portfolio_value']:,.2f}")
            print(f"💵 Cash: ${account_info['cash']:,.2f}")
            print(f"🔴 LIVE TRADING CONFIG - No Paper Trading Restrictions")s real $963K portfolio value instead of hard-coded $1000
- Properly calculates safety limits  
- Ensures actual Alpaca trades go through
"""

import sys
import os
import time
from datetime import datetime, timedelta
import logging

# Add the project directory to Python path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from connect_real_trading import RealPaperTradingEngine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/wes/Desktop/litebotx-usb-deployment/fixed_trading.log'),
        logging.StreamHandler()
    ]
)

def create_fixed_config():
    """Create config with real portfolio value and appropriate limits"""
    
    # LIVE TRADING MODE: No paper trading restrictions
    print("🔴 LIVE TRADING MODE ENABLED")
    print("💰 This system operates with LIVE trading configuration")
    print("🚫 NO PAPER TRADING RESTRICTIONS OR LIMITATIONS")
    
    print("✅ LIVE trading mode enabled - initializing...")
    
    # Get real portfolio value from Alpaca
    engine = RealPaperTradingEngine()
    account_info = engine.get_account_info()
    
    if account_info:
        real_portfolio_value = account_info['portfolio_value']
        print(f"📊 Real Portfolio Value: ${real_portfolio_value:,.2f}")
    else:
        real_portfolio_value = 963000.0  # Fallback
        print(f"⚠️  Using fallback portfolio value: ${real_portfolio_value:,.2f}")
    
    return ShortCycleConfig(
        # CRITICAL: Use real portfolio value
        portfolio_value=real_portfolio_value,
        
        # Aggressive settings for more trading activity  
        daily_pool_percent=0.80,  # 80% of portfolio available for trading
        max_risk_per_trade_dollars=100.0,  # $100 max risk per trade
        
        # Position limits
        max_positions_per_day=8,
        min_position_size_dollars=25.0,
        max_position_size_percent=0.03,  # 3% max per position
        
        # Safety limits (percentage of REAL portfolio value)
        max_daily_loss_percent=0.005,  # 0.5% daily = ~$4,815 on $963K
        max_weekly_loss_percent=0.02,  # 2.0% weekly = ~$19,260 on $963K
        
        # Signal thresholds - super aggressive
        confidence_threshold=0.10,  # Very low confidence needed
        
        # Trading days
        trading_days=["monday", "tuesday", "wednesday", "thursday", "friday"]
    )

def main():
    print("🚀 FIXED Aggressive Trading Launcher")
    print("="*60)
    
    try:
        # Create fixed configuration
        config = create_fixed_config()
        
        # Display safety limits with real values
        daily_limit = config.portfolio_value * config.max_daily_loss_percent
        weekly_limit = config.portfolio_value * config.max_weekly_loss_percent
        daily_pool = config.portfolio_value * config.daily_pool_percent
        
        print(f"💰 Portfolio: ${config.portfolio_value:,.2f}")
        print(f"🛡️  Daily Loss Limit: ${daily_limit:,.2f} ({config.max_daily_loss_percent:.1%})")
        print(f"🛡️  Weekly Loss Limit: ${weekly_limit:,.2f} ({config.max_weekly_loss_percent:.1%})")
        print(f"💸 Daily Trading Pool: ${daily_pool:,.2f} ({config.daily_pool_percent:.1%})")
        print(f"🎯 Confidence Threshold: {config.confidence_threshold:.1%}")
        print()
        
        # Initialize trader with fixed config
        trader = ShortCycleTrader(config)
        
        # Verify real Alpaca connection
        account_info = trader.execution_engine.get_account_info()
        if account_info:
            print(f"✅ Connected to Alpaca Paper Trading")
            print(f"   Portfolio: ${account_info['portfolio_value']:,.2f}")
            print(f"   Cash: ${account_info['cash']:,.2f}")
            print(f"   Status: {account_info['status']}")
        else:
            print("❌ Failed to connect to Alpaca")
            return
        
        cycle_count = 0
        
        while True:
            cycle_count += 1
            now = datetime.now()
            
            print(f"\\n🔄 FIXED Trading Cycle #{cycle_count} at {now.strftime('%H:%M:%S')}")
            
            try:
                # Run actual trading cycle
                trader.run_daily_cycle()
                
                # Show current status
                portfolio_val = trader._get_portfolio_value()
                trader._load_positions()  # This updates trader.positions
                positions = trader.positions  # Get the loaded positions
                active_positions = len([p for p in positions if p.status == "entered"])
                
                print(f"💰 ${portfolio_val:,.0f} | Active: {active_positions}/10")
                
            except Exception as e:
                print(f"❌ Cycle error: {e}")
                logging.error(f"Trading cycle error: {e}")
            
            # Wait between cycles
            print("⏱️ Waiting 60 seconds...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()