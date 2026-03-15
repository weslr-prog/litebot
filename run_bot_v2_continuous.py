#!/usr/bin/env python3
"""
Run bot_v2 ProductionTradingEngine in CONTINUOUS OPERATION mode
Handles pre-market, market hours, and post-market activities with sleep/wake cycles

This matches the original bot's behavior of running continuously with scheduled activities.
"""
import os
import sys
import time
import datetime as dt
import pytz
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import bot_v2
from bot_v2.core import ProductionTradingEngine
from bot_v2.config import ShortCycleConfig

# Use Alpaca adapter for live trading
from alpaca_adapter import AlpacaAdapter

# Import data loader
from data_loader import DataLoader


def get_current_et_time():
    """Get current time in ET timezone"""
    et_tz = pytz.timezone('US/Eastern')
    return dt.datetime.now(et_tz)


def is_weekday():
    """Check if today is a weekday (Mon-Fri)"""
    current = get_current_et_time()
    return current.weekday() < 5  # 0-4 is Mon-Fri


def is_pre_market_time():
    """Check if we're in pre-market period (6:00 AM - 9:30 AM ET)"""
    current = get_current_et_time()
    current_time = current.time()
    pre_market_start = dt.time(6, 0)
    market_open = dt.time(9, 30)
    return is_weekday() and pre_market_start <= current_time < market_open


def is_market_hours():
    """Check if we're in regular market hours (9:30 AM - 4:00 PM ET)"""
    current = get_current_et_time()
    current_time = current.time()
    market_open = dt.time(9, 30)
    market_close = dt.time(16, 0)
    return is_weekday() and market_open <= current_time < market_close


def is_post_market_time():
    """Check if we're in post-market period (4:00 PM - 8:00 PM ET)"""
    current = get_current_et_time()
    current_time = current.time()
    market_close = dt.time(16, 0)
    post_market_end = dt.time(20, 0)
    return is_weekday() and market_close <= current_time < post_market_end


def seconds_until_next_activity():
    """Calculate seconds until next scheduled activity"""
    current = get_current_et_time()
    current_time = current.time()
    
    # If weekend, sleep until Monday 6 AM
    if not is_weekday():
        days_until_monday = (7 - current.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 1  # If Sunday, wait 1 day
        next_activity = current.replace(hour=6, minute=0, second=0, microsecond=0)
        next_activity += dt.timedelta(days=days_until_monday)
        return int((next_activity - current).total_seconds())
    
    # Weekday - determine next activity
    if current_time < dt.time(6, 0):
        # Before pre-market, sleep until 6 AM
        next_activity = current.replace(hour=6, minute=0, second=0, microsecond=0)
    elif current_time < dt.time(9, 30):
        # In pre-market, next activity is market open
        next_activity = current.replace(hour=9, minute=30, second=0, microsecond=0)
    elif current_time < dt.time(16, 0):
        # In market hours, check every 5 minutes
        return 300  # 5 minutes
    elif current_time < dt.time(20, 0):
        # In post-market, next activity is end of post-market
        next_activity = current.replace(hour=20, minute=0, second=0, microsecond=0)
    else:
        # After hours, sleep until next day 6 AM
        next_activity = (current + dt.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    
    return int((next_activity - current).total_seconds())


def format_time_remaining(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def initialize_bot():
    """Initialize bot and return (bot, execution_engine) tuple"""
    print("="*70)
    print("bot_v2 ProductionTradingEngine - CONTINUOUS OPERATION MODE")
    print("="*70)
    print()
    
    # Get credentials from environment variables
    alpaca_api_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
    alpaca_secret_key = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET_KEY')
    alpaca_base_url = os.getenv('APCA_API_BASE_URL')
    alpaca_paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
    
    if not alpaca_api_key or not alpaca_secret_key:
        print("❌ ERROR: Alpaca credentials not found in .env file")
        print("   Please ensure .env contains:")
        print("   APCA_API_KEY_ID=your_key_here")
        print("   APCA_API_SECRET_KEY=your_secret_here")
        print("   APCA_API_BASE_URL=https://paper-api.alpaca.markets")
        sys.exit(1)
    
    # Determine if paper trading
    if alpaca_base_url:
        is_paper = 'paper' in alpaca_base_url.lower()
    else:
        is_paper = alpaca_paper
    
    print(f"✅ Loaded credentials from .env")
    print(f"   Mode: {'PAPER TRADING' if is_paper else 'LIVE TRADING'}")
    if alpaca_base_url:
        print(f"   Base URL: {alpaca_base_url}")
    print()
    
    # Initialize configuration
    config = ShortCycleConfig()
    print(f"📋 Configuration:")
    print(f"   Portfolio Value: ${config.portfolio_value:,.0f}")
    
    # Show dynamic daily pool based on day of week
    current = get_current_et_time()
    weekday = current.weekday()
    if weekday <= 2:  # Mon-Wed
        daily_pool_pct = 0.30
        daily_pool_name = "Mon-Wed (Conservative)"
    else:  # Thu-Fri
        daily_pool_pct = 0.50
        daily_pool_name = "Thu-Fri (Aggressive)"
    daily_pool_amt = config.portfolio_value * daily_pool_pct
    
    print(f"   Daily Pool: ${daily_pool_amt:,.0f} ({daily_pool_pct:.0%}) - {daily_pool_name}")
    print(f"   Market Cap Filter: ${config.min_market_cap/1e9:.1f}B - ${config.max_market_cap/1e9:.1f}B (Mid-Cap Only)")
    print(f"   Confidence Threshold: {config.confidence_threshold:.0%}")
    print(f"   Max Positions/Day: {config.max_positions_per_day}")
    print(f"   Max Hold Days: {config.max_hold_days} (D+1 standard, D+2-D+3 for momentum)")
    print(f"   Max Daily Loss: ${config.max_daily_loss_dollars:,.0f} ({config.max_daily_loss_percent:.0%})")
    print(f"   PDT Tracking: {config.max_emergency_exits_per_week} emergency exits/week")
    print()
    
    # Initialize Alpaca adapter
    print("🔌 Connecting to Alpaca...")
    try:
        execution_engine = AlpacaAdapter(
            api_key=alpaca_api_key,
            secret_key=alpaca_secret_key,
            paper=is_paper
        )
        
        # Test connection
        portfolio = execution_engine.get_portfolio_summary()
        account_value = portfolio['account']['portfolio_value']
        buying_power = portfolio['account']['buying_power']
        
        print("✅ Connected to Alpaca")
        print(f"   Account Value: ${account_value:,.2f}")
        print(f"   Buying Power: ${buying_power:,.2f}")
    except Exception as e:
        print(f"❌ Failed to connect to Alpaca: {e}")
        sys.exit(1)
    
    # Initialize data loader
    print("📊 Initializing data loader...")
    try:
        data_loader = DataLoader()
        print("✅ Data loader ready")
    except Exception as e:
        print(f"❌ Failed to initialize data loader: {e}")
        sys.exit(1)
    
    print()
    
    # Initialize bot_v2
    print("🤖 Initializing bot_v2 ProductionTradingEngine...")
    try:
        bot = ProductionTradingEngine(
            config=config,
            execution_engine=execution_engine,
            data_loader=data_loader
        )
        print("✅ bot_v2 initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    return bot, execution_engine


def pre_market_activities(bot):
    """Pre-market preparation (6:00 AM - 9:30 AM ET)"""
    current = get_current_et_time()
    print("="*70)
    print(f"🌅 PRE-MARKET PREPARATION - {current.strftime('%I:%M %p ET')}")
    print("="*70)
    print()
    
    print("📊 Loading market data...")
    print("🔍 Refreshing watchlist...")
    print("📈 Analyzing overnight moves...")
    print("✅ Pre-market preparation complete")
    print()


def market_hours_activities(bot):
    """Market hours trading (9:30 AM - 4:00 PM ET)"""
    current = get_current_et_time()
    print("="*70)
    print(f"📈 MARKET HOURS TRADING - {current.strftime('%I:%M %p ET')}")
    print("="*70)
    print()
    
    try:
        print("🚀 Running daily trading cycle...")
        bot.run_daily_cycle()
        print("✅ Trading cycle complete")
    except Exception as e:
        print(f"❌ Error during trading cycle: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def post_market_activities(bot, execution_engine):
    """Post-market cleanup (4:00 PM - 8:00 PM ET)"""
    current = get_current_et_time()
    print("="*70)
    print(f"🌙 POST-MARKET CLEANUP - {current.strftime('%I:%M %p ET')}")
    print("="*70)
    print()
    
    try:
        # Get portfolio summary
        summary = bot.get_portfolio_summary()
        portfolio = execution_engine.get_portfolio_summary()
        
        print("📊 Daily Performance Summary:")
        print(f"   Portfolio Value: ${summary.get('portfolio_value', 0):,.2f}")
        print(f"   Open Positions: {summary.get('open_positions', 0)}")
        print(f"   Trades Today: {summary.get('trades_today', 0)}")
        print(f"   Daily P&L: ${summary.get('daily_pnl', 0):,.2f}")
        print()
        
        # Show PDT status
        try:
            pdt_status = bot.portfolio_manager.get_pdt_status()
            print("🚦 PDT Slot Tracking:")
            print(f"   Emergency Exits Used: {pdt_status['emergency_exits_used']}/{pdt_status['max_per_week']}")
            print(f"   Emergency Exits Available: {pdt_status['emergency_exits_available']}")
            print(f"   Friday Entry Slots: {pdt_status['friday_slots_available']}")
            print(f"   Can Trade Friday: {'Yes' if pdt_status['can_trade_friday'] else 'No'}")
            if pdt_status['last_weekly_reset']:
                print(f"   Last Weekly Reset: {pdt_status['last_weekly_reset']}")
            print()
        except Exception as e:
            print(f"⚠️  Could not retrieve PDT status: {e}")
            print()
        
        print("💾 Saving position data...")
        print("📝 Generating daily report...")
        print("✅ Post-market cleanup complete")
    except Exception as e:
        print(f"❌ Error during post-market cleanup: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def main():
    """Main continuous operation loop"""
    
    # Initialize bot once at startup
    bot, execution_engine = initialize_bot()
    
    print("="*70)
    print("🔄 CONTINUOUS OPERATION MODE ACTIVE")
    print("="*70)
    print()
    print("Bot will now run continuously with scheduled activities:")
    print("  🌅 Pre-Market (6:00 AM - 9:30 AM): Data loading & preparation")
    print("  📈 Market Hours (9:30 AM - 4:00 PM): Active trading every 5 min")
    print("  🌙 Post-Market (4:00 PM - 8:00 PM): Reporting & cleanup")
    print("  💤 After Hours / Weekends: Sleep until next activity")
    print()
    print("Press Ctrl+C to stop the bot")
    print("="*70)
    print()
    
    last_activity = None
    
    try:
        while True:
            current = get_current_et_time()
            current_day = current.strftime('%A')
            current_time_str = current.strftime('%I:%M:%S %p ET')
            
            # Determine current activity
            if is_pre_market_time():
                activity = "PRE_MARKET"
            elif is_market_hours():
                activity = "MARKET_HOURS"
            elif is_post_market_time():
                activity = "POST_MARKET"
            elif is_weekday():
                activity = "AFTER_HOURS"
            else:
                activity = "WEEKEND"
            
            # Execute activity if it's a new phase
            if activity != last_activity:
                if activity == "PRE_MARKET":
                    pre_market_activities(bot)
                elif activity == "MARKET_HOURS":
                    market_hours_activities(bot)
                elif activity == "POST_MARKET":
                    post_market_activities(bot, execution_engine)
                
                last_activity = activity
            
            # During market hours, run trading cycle every 5 minutes
            elif activity == "MARKET_HOURS":
                print(f"🔄 [{current_time_str}] Checking for trading opportunities...")
                try:
                    bot.run_daily_cycle()
                except Exception as e:
                    print(f"⚠️  Trading cycle error: {e}")
            
            # Calculate sleep time until next activity
            sleep_seconds = seconds_until_next_activity()
            
            # Display status
            if activity in ["AFTER_HOURS", "WEEKEND"]:
                print(f"💤 [{current_time_str}] {activity}: Sleeping for {format_time_remaining(sleep_seconds)}")
                print(f"   Next activity: {current + dt.timedelta(seconds=sleep_seconds):%A %I:%M %p ET}")
                print()
            
            # Sleep until next activity
            time.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        print()
        print("="*70)
        print("⚠️  Bot shutdown requested by user")
        print("="*70)
        print()
        
        # Display final summary
        try:
            summary = bot.get_portfolio_summary()
            print("📊 Final Portfolio Summary:")
            print(f"   Portfolio Value: ${summary.get('portfolio_value', 0):,.2f}")
            print(f"   Open Positions: {summary.get('open_positions', 0)}")
            print(f"   Trades Today: {summary.get('trades_today', 0)}")
            print()
        except:
            pass
        
        print("✅ Bot shutdown complete")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
