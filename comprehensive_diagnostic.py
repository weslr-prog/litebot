#!/usr/bin/env python3
"""
Comprehensive Bot Diagnostic Suite
Tests all critical functionality and identifies configuration issues
"""
import sys
import json
import logging
from datetime import datetime, time, date
import pytz
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Track all issues
CRITICAL_ISSUES = []
HIGH_ISSUES = []
MEDIUM_ISSUES = []
LOW_ISSUES = []

def add_issue(severity, title, description, fix_action=None):
    """Track an issue"""
    issue = {
        'title': title,
        'description': description,
        'fix_action': fix_action
    }
    
    if severity == 'CRITICAL':
        CRITICAL_ISSUES.append(issue)
    elif severity == 'HIGH':
        HIGH_ISSUES.append(issue)
    elif severity == 'MEDIUM':
        MEDIUM_ISSUES.append(issue)
    else:
        LOW_ISSUES.append(issue)


def test_day_of_week_detection():
    """Test if day-of-week detection is correct"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 1: Day-of-Week Detection")
    logger.info("=" * 70)
    
    try:
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        
        # Get actual day
        actual_day = now.strftime('%A')
        actual_weekday = now.weekday()  # 0=Monday, 4=Friday
        
        logger.info(f"✅ Current date: {now.strftime('%Y-%m-%d')}")
        logger.info(f"✅ Day of week: {actual_day} (weekday #{actual_weekday})")
        
        # Test if today is Friday
        is_friday = actual_weekday == 4
        logger.info(f"✅ Is Friday: {is_friday}")
        
        # Check if bot would activate Friday freeze
        if actual_day == "Thursday" and is_friday:
            add_issue('CRITICAL', 
                     'Day Detection Bug',
                     f'Date is {now.strftime("%Y-%m-%d")} (Thursday) but code thinks it is Friday',
                     'Fix weekend risk filter day detection logic')
            logger.error("❌ CRITICAL: Thursday detected as Friday!")
            return False
        
        logger.info("\n✅ PASS: Day-of-week detection is correct\n")
        return True
        
    except Exception as e:
        add_issue('CRITICAL', 'Day Detection Error', str(e))
        logger.error(f"❌ FAIL: {e}")
        return False


def test_configuration_loading():
    """Test that SmallPortfolioConfig loads correctly with all parameters"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 2: Configuration Loading")
    logger.info("=" * 70)
    
    try:
        from small_portfolio_config import SmallPortfolioConfig
        config = SmallPortfolioConfig()
        
        # Test critical parameters
        tests = [
            ('confidence_threshold', 0.04, 'equals', 'Confidence threshold should be 4%'),
            ('late_entry_confidence_multiplier', 1.2, 'equals', 'Late entry multiplier should be 1.2x'),
            ('vol_spike_min', 0.8, 'equals', 'Volume spike filter should be 80%'),
            ('breakout_min', 0.003, 'equals', 'Breakout minimum should be 0.3%'),
            ('min_avg_volume', 200000, 'equals', 'Min volume should be 200K'),
            ('min_dollar_volume', 1000000, 'equals', 'Min dollar volume should be $1M'),
            ('max_position_dollars', 250.0, 'equals', 'Max position should be $250'),
            ('max_positions_per_day', 2, 'equals', 'Max positions per day should be 2'),
            ('cash_account_mode', False, 'equals', 'Should be margin account'),
            ('enable_same_day_exit', False, 'equals', 'Same-day exit should be disabled'),
            ('max_hold_days', 3, 'equals', 'Max hold days should be 3'),
        ]
        
        failed = []
        for param_name, expected, comparison, description in tests:
            actual = getattr(config, param_name, None)
            
            if actual is None:
                failed.append(f"{param_name}: MISSING")
                add_issue('HIGH', f'Missing Config: {param_name}', description)
                logger.error(f"❌ {param_name}: MISSING")
            elif comparison == 'equals' and actual != expected:
                failed.append(f"{param_name}: {actual} != {expected}")
                add_issue('HIGH', f'Wrong Config: {param_name}', 
                         f'{description} (got {actual}, expected {expected})')
                logger.error(f"❌ {param_name}: {actual} (expected {expected})")
            else:
                logger.info(f"✅ {param_name}: {actual}")
        
        # Check for missing attributes that cause errors
        optional_attrs = ['max_universe_size', 'min_universe_size']
        for attr in optional_attrs:
            if not hasattr(config, attr):
                add_issue('HIGH', f'Missing Attribute: {attr}', 
                         'Causes watchlist refresh errors')
                logger.warning(f"⚠️  Missing attribute: {attr}")
        
        if failed:
            logger.error(f"\n❌ FAIL: {len(failed)} configuration issues found\n")
            return False
        
        logger.info("\n✅ PASS: Configuration loaded correctly\n")
        return True
        
    except Exception as e:
        add_issue('CRITICAL', 'Configuration Load Error', str(e))
        logger.error(f"❌ FAIL: {e}")
        return False


def test_position_sizing():
    """Test position sizing calculations"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 3: Position Sizing Logic")
    logger.info("=" * 70)
    
    try:
        from small_portfolio_config import SmallPortfolioConfig
        config = SmallPortfolioConfig()
        
        # Test case: IBM at $312.42, stop at $304.61
        entry_price = 312.42
        stop_price = 304.61
        risk_per_share = entry_price - stop_price  # $7.81
        
        portfolio = 1000.0
        max_position_pct = 0.25  # 25%
        max_position_dollars = portfolio * max_position_pct  # $250
        
        # Method 1: Max position sizing
        shares_by_dollars = max_position_dollars / entry_price
        position_value_1 = shares_by_dollars * entry_price
        
        # Method 2: Risk-based sizing (2% risk = $20)
        max_risk_dollars = config.max_risk_per_trade_dollars  # Should be $20
        shares_by_risk = max_risk_dollars / risk_per_share
        position_value_2 = shares_by_risk * entry_price
        
        logger.info(f"Entry: ${entry_price:.2f}")
        logger.info(f"Stop: ${stop_price:.2f}")
        logger.info(f"Risk per share: ${risk_per_share:.2f}")
        logger.info(f"Portfolio: ${portfolio:.2f}")
        logger.info(f"Max position %: {max_position_pct:.1%}")
        logger.info("")
        logger.info(f"Method 1 (Max Position):")
        logger.info(f"  Shares: {shares_by_dollars:.2f}")
        logger.info(f"  Position value: ${position_value_1:.2f}")
        logger.info("")
        logger.info(f"Method 2 (Risk-Based):")
        logger.info(f"  Max risk: ${max_risk_dollars:.2f}")
        logger.info(f"  Shares: {shares_by_risk:.2f}")
        logger.info(f"  Position value: ${position_value_2:.2f}")
        logger.info("")
        
        # Take the smaller position
        final_shares = min(shares_by_dollars, shares_by_risk)
        final_value = final_shares * entry_price
        
        logger.info(f"Final position:")
        logger.info(f"  Shares: {final_shares:.2f}")
        logger.info(f"  Value: ${final_value:.2f}")
        
        # Check for the $0 bug
        if final_value == 0 or final_shares == 0:
            add_issue('CRITICAL', 
                     'Position Sizing Returns $0',
                     f'IBM at ${entry_price} with ${portfolio} portfolio calculated as $0 position',
                     'Debug position sizing logic in ShortCycleTrader')
            logger.error("❌ CRITICAL: Position sizing returned $0!")
            return False
        
        if final_value < 25:
            add_issue('HIGH',
                     'Position Too Small',
                     f'Position ${final_value:.2f} below $25 minimum',
                     'Adjust position sizing or minimum position threshold')
            logger.warning(f"⚠️  Position ${final_value:.2f} below $25 minimum")
        
        logger.info("\n✅ PASS: Position sizing calculations work\n")
        return True
        
    except Exception as e:
        add_issue('CRITICAL', 'Position Sizing Error', str(e))
        logger.error(f"❌ FAIL: {e}")
        return False


def test_stock_universe():
    """Test stock universe and watchlist"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 4: Stock Universe & Watchlist")
    logger.info("=" * 70)
    
    try:
        # Check base universe
        with open('config/short_cycle_universe.json', 'r') as f:
            universe = json.load(f)
        
        base_stocks = universe.get('base_universe', [])
        logger.info(f"✅ Base universe: {len(base_stocks)} stocks")
        
        # Check for mid-cap volatile stocks
        expected_stocks = ['PLTR', 'SOFI', 'RIVN', 'MARA', 'PLUG', 'HOOD', 'SNAP', 'COIN']
        found = [s for s in expected_stocks if s in base_stocks]
        missing = [s for s in expected_stocks if s not in base_stocks]
        
        logger.info(f"✅ Expected mid-cap stocks found: {len(found)}/{len(expected_stocks)}")
        if missing:
            logger.warning(f"⚠️  Missing stocks: {', '.join(missing)}")
        
        # Check for old large-cap stocks that shouldn't be there
        old_stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA']
        old_found = [s for s in old_stocks if s in base_stocks]
        if old_found:
            add_issue('MEDIUM',
                     'Old Large-Cap Stocks in Universe',
                     f'Found {len(old_found)} S&P 500 stocks: {", ".join(old_found)}',
                     'Remove large-cap stocks from universe')
            logger.warning(f"⚠️  Old large-cap stocks found: {', '.join(old_found)}")
        
        # Check current watchlist
        try:
            with open('logs/current_watchlist.json', 'r') as f:
                watchlist = json.load(f)
            
            symbols = watchlist.get('symbols', [])
            generated_str = watchlist.get('generated_at', '')
            
            logger.info(f"✅ Current watchlist: {len(symbols)} stocks")
            logger.info(f"   Symbols: {', '.join(symbols[:10])}{' ...' if len(symbols) > 10 else ''}")
            
            if generated_str:
                generated_at = datetime.fromisoformat(generated_str)
                et_tz = pytz.timezone('US/Eastern')
                now = datetime.now(et_tz)
                age_hours = (now - generated_at).total_seconds() / 3600
                logger.info(f"   Age: {age_hours:.1f} hours")
                
                if age_hours > 24:
                    add_issue('MEDIUM',
                             'Stale Watchlist',
                             f'Watchlist is {age_hours:.1f} hours old',
                             'Run watchlist refresh before market open')
                    logger.warning(f"⚠️  Watchlist is {age_hours:.1f} hours old")
            
            # Check if watchlist has wrong stocks (old universe)
            wrong_stocks = ['AMD', 'MMM', 'IBM', 'UPS', 'CSCO']
            wrong_found = [s for s in wrong_stocks if s in symbols]
            if wrong_found:
                add_issue('HIGH',
                         'Wrong Stocks in Watchlist',
                         f'Watchlist contains old large-cap stocks: {", ".join(wrong_found)}',
                         'Force watchlist refresh with new universe')
                logger.error(f"❌ Wrong stocks in watchlist: {', '.join(wrong_found)}")
        
        except FileNotFoundError:
            add_issue('HIGH', 'Missing Watchlist', 'No current_watchlist.json file')
            logger.error("❌ No watchlist file found")
        
        logger.info("\n✅ PASS: Stock universe configured\n")
        return True
        
    except Exception as e:
        add_issue('CRITICAL', 'Universe Configuration Error', str(e))
        logger.error(f"❌ FAIL: {e}")
        return False


def test_file_structure():
    """Test that all required files exist and are valid"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 5: File Structure & Dependencies")
    logger.info("=" * 70)
    
    required_files = {
        'config/short_cycle_universe.json': 'Stock universe',
        'small_portfolio_config.py': 'Configuration',
        'traders/short_cycle_trader.py': 'Trading engine',
        'start_small_portfolio_trader.py': 'Startup script',
    }
    
    optional_files = {
        'positions.json': 'Position tracking',
        'trades.json': 'Trade history',
        'logs/current_watchlist.json': 'Active watchlist',
    }
    
    missing = []
    for filepath, description in required_files.items():
        if Path(filepath).exists():
            logger.info(f"✅ {description}: {filepath}")
        else:
            missing.append(filepath)
            add_issue('CRITICAL', f'Missing Required File: {filepath}', description)
            logger.error(f"❌ Missing: {filepath}")
    
    for filepath, description in optional_files.items():
        if Path(filepath).exists():
            logger.info(f"✅ {description}: {filepath}")
        else:
            logger.warning(f"⚠️  Missing (will be created): {filepath}")
    
    if missing:
        logger.error(f"\n❌ FAIL: {len(missing)} required files missing\n")
        return False
    
    logger.info("\n✅ PASS: All required files present\n")
    return True


def test_legacy_cleanup_needed():
    """Check for legacy files/configs that need cleanup"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 6: Legacy Files & Cleanup Needed")
    logger.info("=" * 70)
    
    # Check for old config files
    legacy_configs = [
        'config.py',
        'stock_config.py',
        'automated_momentum_trader.py',
        'automated_momentum_trader_v2.py',
        'simple_stock_launcher.py',
    ]
    
    found_legacy = []
    for filepath in legacy_configs:
        if Path(filepath).exists():
            found_legacy.append(filepath)
            logger.warning(f"⚠️  Legacy file: {filepath}")
    
    if found_legacy:
        add_issue('MEDIUM',
                 'Legacy Files Present',
                 f'Found {len(found_legacy)} old files: {", ".join(found_legacy)}',
                 'Move to archive or delete to avoid confusion')
    
    # Check for multiple config files that might conflict
    config_files = list(Path('.').glob('*config*.py'))
    logger.info(f"Found {len(config_files)} config files:")
    for cf in config_files:
        logger.info(f"   {cf}")
    
    if len(config_files) > 2:  # small_portfolio_config.py + maybe 1 other
        add_issue('MEDIUM',
                 'Multiple Config Files',
                 f'Found {len(config_files)} config files - may cause confusion',
                 'Consolidate to single config file')
    
    # Check for old universe files
    if Path('config/stock_universe.json').exists():
        add_issue('LOW',
                 'Old Universe File',
                 'config/stock_universe.json exists (using short_cycle_universe.json)',
                 'Archive old universe file')
        logger.warning("⚠️  Old universe file: config/stock_universe.json")
    
    logger.info("\n✅ PASS: Legacy file scan complete\n")
    return True


def test_module_imports():
    """Test that all required modules import correctly"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 7: Module Imports")
    logger.info("=" * 70)
    
    modules = [
        ('small_portfolio_config', 'SmallPortfolioConfig'),
        ('traders.short_cycle_trader', 'ShortCycleTrader'),
        ('data_source', None),
        ('signal_generator', None),
        ('pre_filter', None),
    ]
    
    failed = []
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name] if class_name else [])
            if class_name:
                getattr(module, class_name)
            logger.info(f"✅ {module_name}" + (f".{class_name}" if class_name else ""))
        except ImportError as e:
            failed.append(f"{module_name}: {e}")
            add_issue('CRITICAL', f'Import Error: {module_name}', str(e))
            logger.error(f"❌ {module_name}: {e}")
        except AttributeError as e:
            failed.append(f"{module_name}.{class_name}: {e}")
            add_issue('CRITICAL', f'Missing Class: {class_name}', str(e))
            logger.error(f"❌ {module_name}.{class_name}: {e}")
    
    if failed:
        logger.error(f"\n❌ FAIL: {len(failed)} import errors\n")
        return False
    
    logger.info("\n✅ PASS: All modules import successfully\n")
    return True


def test_weekend_risk_filter():
    """Test weekend risk filter logic"""
    logger.info("=" * 70)
    logger.info("🔍 TEST 8: Weekend Risk Filter Logic")
    logger.info("=" * 70)
    
    try:
        et_tz = pytz.timezone('US/Eastern')
        
        # Test various dates
        test_dates = [
            (date(2025, 11, 7), 'Thursday', False),  # Today
            (date(2025, 11, 8), 'Friday', True),      # Tomorrow
            (date(2025, 11, 10), 'Monday', False),    # Next Monday
        ]
        
        for test_date, expected_day, should_freeze in test_dates:
            dt = datetime.combine(test_date, time(10, 0))
            dt = et_tz.localize(dt)
            
            actual_day = dt.strftime('%A')
            is_friday = dt.weekday() == 4
            
            logger.info(f"Date: {test_date} ({expected_day})")
            logger.info(f"  Detected as: {actual_day}")
            logger.info(f"  Is Friday: {is_friday}")
            logger.info(f"  Should freeze entries: {should_freeze}")
            
            if actual_day != expected_day:
                add_issue('CRITICAL',
                         f'Wrong Day Detection: {test_date}',
                         f'Date {test_date} is {expected_day} but detected as {actual_day}')
                logger.error(f"  ❌ WRONG! Expected {expected_day}, got {actual_day}")
            elif is_friday != should_freeze:
                add_issue('CRITICAL',
                         'Friday Detection Logic Error',
                         f'{expected_day} freeze status incorrect')
                logger.error(f"  ❌ WRONG! Friday detection mismatch")
            else:
                logger.info(f"  ✅ Correct")
            logger.info("")
        
        logger.info("✅ PASS: Weekend filter logic test complete\n")
        return True
        
    except Exception as e:
        add_issue('CRITICAL', 'Weekend Filter Test Error', str(e))
        logger.error(f"❌ FAIL: {e}")
        return False


def main():
    """Run all diagnostic tests"""
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("🔬 COMPREHENSIVE BOT DIAGNOSTIC SUITE")
    logger.info("=" * 70)
    logger.info("Testing all critical functionality and identifying issues")
    logger.info("=" * 70)
    logger.info("\n")
    
    tests = [
        ("Day-of-Week Detection", test_day_of_week_detection),
        ("Configuration Loading", test_configuration_loading),
        ("Position Sizing Logic", test_position_sizing),
        ("Stock Universe & Watchlist", test_stock_universe),
        ("File Structure", test_file_structure),
        ("Legacy Cleanup", test_legacy_cleanup_needed),
        ("Module Imports", test_module_imports),
        ("Weekend Risk Filter", test_weekend_risk_filter),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"❌ TEST CRASHED: {name} - {e}")
            results.append((name, False))
            add_issue('CRITICAL', f'Test Crashed: {name}', str(e))
    
    # Summary
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("📊 DIAGNOSTIC SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 70)
    logger.info(f"Tests: {passed}/{total} passed")
    logger.info("=" * 70)
    
    # Issues summary
    total_issues = len(CRITICAL_ISSUES) + len(HIGH_ISSUES) + len(MEDIUM_ISSUES) + len(LOW_ISSUES)
    
    logger.info("\n")
    logger.info("=" * 70)
    logger.info(f"🐛 ISSUES FOUND: {total_issues}")
    logger.info("=" * 70)
    
    if CRITICAL_ISSUES:
        logger.error(f"\n🚨 CRITICAL ISSUES ({len(CRITICAL_ISSUES)}):")
        logger.error("-" * 70)
        for i, issue in enumerate(CRITICAL_ISSUES, 1):
            logger.error(f"\n{i}. {issue['title']}")
            logger.error(f"   {issue['description']}")
            if issue['fix_action']:
                logger.error(f"   FIX: {issue['fix_action']}")
    
    if HIGH_ISSUES:
        logger.warning(f"\n⚠️  HIGH PRIORITY ISSUES ({len(HIGH_ISSUES)}):")
        logger.warning("-" * 70)
        for i, issue in enumerate(HIGH_ISSUES, 1):
            logger.warning(f"\n{i}. {issue['title']}")
            logger.warning(f"   {issue['description']}")
            if issue['fix_action']:
                logger.warning(f"   FIX: {issue['fix_action']}")
    
    if MEDIUM_ISSUES:
        logger.info(f"\n📋 MEDIUM PRIORITY ISSUES ({len(MEDIUM_ISSUES)}):")
        logger.info("-" * 70)
        for i, issue in enumerate(MEDIUM_ISSUES, 1):
            logger.info(f"\n{i}. {issue['title']}")
            logger.info(f"   {issue['description']}")
            if issue['fix_action']:
                logger.info(f"   FIX: {issue['fix_action']}")
    
    if LOW_ISSUES:
        logger.info(f"\n💡 LOW PRIORITY ISSUES ({len(LOW_ISSUES)}):")
        logger.info("-" * 70)
        for i, issue in enumerate(LOW_ISSUES, 1):
            logger.info(f"\n{i}. {issue['title']}")
            logger.info(f"   {issue['description']}")
    
    # Overall status
    logger.info("\n")
    logger.info("=" * 70)
    
    if len(CRITICAL_ISSUES) > 0:
        logger.error("🚨 OVERALL STATUS: CRITICAL - BOT WILL NOT TRADE CORRECTLY")
        logger.error(f"   Must fix {len(CRITICAL_ISSUES)} critical issues before trading")
    elif len(HIGH_ISSUES) > 0:
        logger.warning("⚠️  OVERALL STATUS: HIGH RISK - BOT MAY MALFUNCTION")
        logger.warning(f"   Should fix {len(HIGH_ISSUES)} high-priority issues")
    elif len(MEDIUM_ISSUES) > 0:
        logger.info("📋 OVERALL STATUS: NEEDS ATTENTION - BOT FUNCTIONAL BUT SUBOPTIMAL")
        logger.info(f"   Recommended: Fix {len(MEDIUM_ISSUES)} medium-priority issues")
    else:
        logger.info("✅ OVERALL STATUS: HEALTHY - BOT READY TO TRADE")
    
    logger.info("=" * 70)
    logger.info("\n")
    
    return 0 if len(CRITICAL_ISSUES) == 0 and len(HIGH_ISSUES) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
