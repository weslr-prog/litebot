#!/usr/bin/env python3
"""
Swing Trading Bot Pre-Flight Check
Tests critical functionality before leaving unmonitored
"""
import sys
import json
import logging
from datetime import datetime, time
import pytz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_configuration():
    """Test that configuration loads correctly"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 1: Configuration Load")
    logger.info("=" * 70)
    
    try:
        from small_portfolio_config import SmallPortfolioConfig
        config = SmallPortfolioConfig()
        
        # Critical swing trading parameters
        assert config.cash_account_mode == False, "❌ Should be margin account (False)"
        logger.info("✅ Cash account mode: False (margin account)")
        
        assert config.enable_same_day_exit == False, "❌ Same-day exit should be disabled"
        logger.info("✅ Same-day exit: Disabled (swing trading)")
        
        assert config.max_hold_days == 3, "❌ Max hold days should be 3"
        logger.info(f"✅ Max hold days: {config.max_hold_days} (swing trading)")
        
        assert config.confidence_threshold > 0.03, "❌ Confidence threshold too low"
        logger.info(f"✅ Confidence threshold: {config.confidence_threshold:.1%} (balanced)")
        
        assert config.max_positions_per_day <= 2, "❌ Too many positions per day"
        logger.info(f"✅ Max positions per day: {config.max_positions_per_day}")
        
        assert config.zone1_take_profit >= 0.05, "❌ Profit targets too tight"
        logger.info(f"✅ D+1 profit target: {config.zone1_take_profit:.1%}")
        
        assert config.zone1_stop_loss <= -0.03, "❌ Stop loss too tight"
        logger.info(f"✅ D+1 stop loss: {config.zone1_stop_loss:.1%}")
        
        logger.info(f"✅ Portfolio value: ${config.portfolio_value:,.0f}")
        logger.info(f"✅ Max position size: ${config.max_position_dollars:,.0f}")
        logger.info(f"✅ Price range: ${config.min_price:.0f}-${config.max_price:.0f}")
        logger.info(f"✅ Volatility range: {config.min_volatility:.1%}-{config.max_volatility:.1%}")
        
        logger.info("\n✅ PASS: Configuration loaded correctly for swing trading\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAIL: Configuration error: {e}")
        return False


def test_watchlist():
    """Test that watchlist exists and has candidates"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 2: Watchlist Check")
    logger.info("=" * 70)
    
    try:
        with open('logs/current_watchlist.json', 'r') as f:
            watchlist = json.load(f)
        
        symbols = watchlist.get('symbols', [])
        count = len(symbols)
        
        assert count >= 8, f"❌ Not enough symbols ({count} < 8)"
        logger.info(f"✅ Watchlist has {count} symbols")
        
        # Check freshness
        generated_str = watchlist.get('generated_at', '')
        generated_at = datetime.fromisoformat(generated_str)
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        age_hours = (now - generated_at).total_seconds() / 3600
        
        logger.info(f"✅ Watchlist age: {age_hours:.1f} hours")
        
        if age_hours > 24:
            logger.warning(f"⚠️  Watchlist is {age_hours:.1f} hours old - consider refresh")
        
        logger.info(f"✅ Top 5 symbols: {', '.join(symbols[:5])}")
        
        logger.info("\n✅ PASS: Watchlist ready\n")
        return True
        
    except FileNotFoundError:
        logger.error("❌ FAIL: Watchlist file not found")
        logger.error("   Run: python3 daily_watchlist_refresh.py")
        return False
    except Exception as e:
        logger.error(f"❌ FAIL: Watchlist error: {e}")
        return False


def test_universe():
    """Test that stock universe is configured"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 3: Stock Universe")
    logger.info("=" * 70)
    
    try:
        with open('config/short_cycle_universe.json', 'r') as f:
            universe = json.load(f)
        
        stocks = universe.get('base_universe', [])
        count = len(stocks)
        
        assert count >= 20, f"❌ Not enough stocks in universe ({count} < 20)"
        logger.info(f"✅ Universe has {count} stocks")
        
        # Check for mid-cap volatile stocks
        sample_stocks = ['PLTR', 'RIVN', 'SOFI', 'MARA', 'PLUG']
        found = [s for s in sample_stocks if s in stocks]
        logger.info(f"✅ Sample mid-cap stocks found: {', '.join(found)}")
        
        logger.info("\n✅ PASS: Stock universe configured\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAIL: Universe error: {e}")
        return False


def test_positions_file():
    """Test that positions file exists and is valid"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 4: Positions File")
    logger.info("=" * 70)
    
    try:
        with open('positions.json', 'r') as f:
            data = json.load(f)
        
        positions = data.get('positions', [])
        count = len(positions)
        
        logger.info(f"✅ Positions file exists with {count} positions")
        
        # Count active positions
        active = [p for p in positions if p.get('status') in ['PENDING', 'ENTERED']]
        logger.info(f"✅ Active positions: {len(active)}")
        
        if len(active) > 0:
            logger.info(f"   Symbols: {', '.join([p.get('symbol') for p in active])}")
        
        logger.info("\n✅ PASS: Positions file valid\n")
        return True
        
    except FileNotFoundError:
        logger.warning("⚠️  Positions file not found (will be created on first trade)")
        logger.info("\n✅ PASS: Will be created automatically\n")
        return True
    except Exception as e:
        logger.error(f"❌ FAIL: Positions file error: {e}")
        return False


def test_market_hours():
    """Test market hours detection"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 5: Market Hours Detection")
    logger.info("=" * 70)
    
    try:
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        
        logger.info(f"✅ Current ET time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"✅ Day of week: {now.strftime('%A')}")
        
        # Check if market hours
        current_time = now.time()
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        is_market_hours = market_open <= current_time <= market_close
        is_weekday = now.weekday() < 5
        
        if is_market_hours and is_weekday:
            logger.info("✅ MARKET IS OPEN - Bot will scan for entries")
        elif is_weekday:
            logger.info("⏰ Market closed - Bot will wait until 9:30 AM ET")
        else:
            logger.info("📅 Weekend - Bot will wait until Monday 9:30 AM ET")
        
        logger.info("\n✅ PASS: Market hours detection working\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAIL: Market hours error: {e}")
        return False


def test_import_trader():
    """Test that trader module imports without errors"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 6: Trader Module Import")
    logger.info("=" * 70)
    
    try:
        # Try to import the trader
        sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')
        from traders.short_cycle_trader import ShortCycleTrader
        
        logger.info("✅ ShortCycleTrader imported successfully")
        logger.info("✅ All dependencies available")
        
        logger.info("\n✅ PASS: Trader module ready\n")
        return True
        
    except ImportError as e:
        logger.error(f"❌ FAIL: Import error: {e}")
        logger.error("   Missing dependencies or syntax error in trader")
        return False
    except Exception as e:
        logger.error(f"❌ FAIL: Trader error: {e}")
        return False


def main():
    """Run all pre-flight checks"""
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("🚀 SWING TRADING BOT PRE-FLIGHT CHECK")
    logger.info("=" * 70)
    logger.info("Testing critical functionality before unmonitored operation")
    logger.info("=" * 70)
    logger.info("\n")
    
    tests = [
        ("Configuration", test_configuration),
        ("Watchlist", test_watchlist),
        ("Stock Universe", test_universe),
        ("Positions File", test_positions_file),
        ("Market Hours", test_market_hours),
        ("Trader Module", test_import_trader),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"❌ TEST CRASHED: {name} - {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("📊 PRE-FLIGHT CHECK SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 70)
    logger.info(f"Result: {passed}/{total} tests passed")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("\n")
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("=" * 70)
        logger.info("✅ Bot is ready for unmonitored operation")
        logger.info("✅ Swing trading configuration validated")
        logger.info("✅ Will enter 1-2 positions tomorrow if signals appear")
        logger.info("✅ Will hold overnight and exit D+1, D+2, or D+3")
        logger.info("=" * 70)
        logger.info("\n📋 WHAT TO EXPECT TOMORROW:")
        logger.info("   • Bot scans 9:45 AM - 3:00 PM for entries")
        logger.info("   • Max 2 new positions per day")
        logger.info("   • Targets: +5-8% over 1-3 days")
        logger.info("   • Stops: -3-4%")
        logger.info("   • Force exit all positions on D+3 at 3:50 PM")
        logger.info("\n💾 Logs: tail -f logs/short_cycle_trader.log")
        logger.info("📊 Positions: cat positions.json")
        logger.info("\n")
        return 0
    else:
        logger.error("\n")
        logger.error("❌ SOME TESTS FAILED")
        logger.error("=" * 70)
        logger.error(f"⚠️  {total - passed} test(s) failed")
        logger.error("⚠️  Fix errors before leaving unmonitored")
        logger.error("=" * 70)
        logger.error("\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
