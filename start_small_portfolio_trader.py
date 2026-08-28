#!/usr/bin/env python3
"""
Small Portfolio Trader Startup Script
Launches ShortCycleTrader with SmallPortfolioConfig for <$1K cash account trading
Features:
- Cash account mode (no PDT restrictions)
- Same-day exits and re-entries enabled
- Intraday scalping enabled
- Settlement tracking for T+2 compliance
"""
import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timedelta
import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_watchlist_freshness():
    """Check if watchlist needs refresh"""
    logger.info("🔍 Checking watchlist freshness...")
    
    try:
        with open('logs/current_watchlist.json', 'r') as f:
            watchlist = json.load(f)
        
        generated_str = watchlist.get('generated_at', '')
        generated_at = datetime.fromisoformat(generated_str)
        
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        age_hours = (now - generated_at).total_seconds() / 3600
        
        symbol_count = len(watchlist.get('symbols', []))
        
        logger.info(f"   Age: {age_hours:.1f} hours | Symbols: {symbol_count}")
        
        # Refresh if > 24 hours old or < 8 symbols
        needs_refresh = age_hours > 24 or symbol_count < 8
        
        if needs_refresh:
            logger.warning(f"⚠️  Watchlist needs refresh (age: {age_hours:.1f}h, count: {symbol_count})")
            return True
        else:
            logger.info("✅ Watchlist is fresh")
            return False
            
    except FileNotFoundError:
        logger.warning("⚠️  Watchlist file not found")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking watchlist: {e}")
        return True


def refresh_watchlist():
    """Run watchlist refresh"""
    logger.info("🔄 Refreshing watchlist...")
    
    try:
        result = subprocess.run(
            [sys.executable, 'daily_watchlist_refresh.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("✅ Watchlist refresh complete")
            return True
        else:
            logger.error(f"❌ Watchlist refresh failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Watchlist refresh timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error refreshing watchlist: {e}")
        return False


def check_dependencies():
    """Check critical dependencies"""
    logger.info("🔍 Checking dependencies...")
    
    missing = []
    
    try:
        import yfinance as yf
        version = getattr(yf, '__version__', 'unknown')
        logger.info(f"   ✅ yfinance ({version})")
    except ImportError as e:
        missing.append("yfinance")
        logger.error(f"   ❌ yfinance: {e}")
    
    try:
        from alpaca.trading.client import TradingClient
        logger.info("   ✅ alpaca-py")
    except ImportError as e:
        missing.append("alpaca-py")
        logger.error(f"   ❌ alpaca-py: {e}")
    
    if missing:
        logger.error(f"❌ Missing dependencies: {', '.join(missing)}")
        logger.error("Install with: pip3 install " + " ".join(missing))
        return False
    
    logger.info("✅ All dependencies available")
    return True


def start_trader():
    """Start the short-cycle trader with SmallPortfolioConfig in PRODUCTION mode"""
    logger.info("🚀 Starting Small Portfolio Trader (CASH ACCOUNT MODE)...")
    
    try:
        # Import trader components
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from traders.short_cycle_trader import ShortCycleTrader
        from small_portfolio_config import SmallPortfolioConfig
        import time
        import pytz
        from datetime import datetime
        
        # Initialize configuration
        config = SmallPortfolioConfig()
        logger.info(f"📊 Portfolio: ${config.portfolio_value:,.0f}")
        logger.info(f"💵 Daily pool: ${config.portfolio_value * config.daily_pool_percent:,.0f} (Mon-Wed)")
        logger.info(f"🏦 Cash Account Mode: {'ENABLED' if config.cash_account_mode else 'DISABLED'}")
        logger.info(f"📈 Same-Day Exit: {'ENABLED' if config.enable_same_day_exit else 'DISABLED'}")
        logger.info(f"🔄 Same-Day Re-Entry: {'ENABLED' if config.enable_same_day_reentry else 'DISABLED'}")
        logger.info(f"⚡ Intraday Scalping: {'ENABLED' if config.enable_intraday_scalping else 'DISABLED'}")
        logger.info(f"🛑 Daily Loss Guardrail: {config.max_daily_loss_percent:.1%}")
        logger.info(f"🧭 Universe Range: ${config.min_price:.0f}-${config.max_price:.0f}")
        logger.info(f"🎯 Max Positions/Day: {config.max_positions_per_day}")
        
        # Initialize trader
        trader = ShortCycleTrader(config)
        logger.info("✅ Trader initialized successfully")
        
        # Production loop - run continuously
        et_tz = pytz.timezone('US/Eastern')
        
        logger.info("🔄 Entering production trading loop...")
        logger.info("   • Market hours: 9:30 AM - 4:00 PM ET")
        
        # Display correct account type based on config
        if config.cash_account_mode:
            logger.info("   • Cash account: UNLIMITED day trades")
            logger.info("   • Settlement tracking: T+2 monitoring")
        else:
            logger.info("   • Margin account: PDT RESTRICTED (3 day trades per 5 days)")
            logger.info("   • Swing trading: D+1 exits only (avoid PDT violations)")
        
        logger.info("   • Market-aware scheduling")
        logger.info("   • Press Ctrl+C to stop")
        
        # Run market-aware continuous cycle (handles all scheduling internally)
        # This will:
        # - Sleep until market hours
        # - Run PreFilter and signal scans throughout session (after initial stabilization)
        # - Monitor positions intraday every 5 minutes
        # - Exit positions intraday using strategy and force-flat rules
        # - Allow same-day exits when profit targets hit
        # - Enable re-entries after exits (cash account only)
        # - Refresh watchlist post-market
        trader.run_continuous_cycle()
        
        logger.info("✅ Trader shutdown complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start trader: {e}", exc_info=True)
        return False


def main():
    """Main startup sequence"""
    logger.info("=" * 70)
    logger.info("🤖 LiteBotX Small Portfolio Trader - Startup")
    logger.info("=" * 70)
    
    # 1. Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        return False
    
    # 2. Check and refresh watchlist if needed
    if check_watchlist_freshness():
        if not refresh_watchlist():
            logger.error("❌ Watchlist refresh failed")
            # Continue anyway - bot may have fallback
    
    # 3. Start trader
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Launching Small Portfolio Trading Bot")
    logger.info("=" * 70)
    
    return start_trader()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Startup interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Startup failed: {e}", exc_info=True)
        sys.exit(1)
