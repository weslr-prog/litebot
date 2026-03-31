#!/usr/bin/env python3
"""
Comprehensive Production Bot Test Suite
Tests all critical components before live deployment
"""
import sys
sys.path.insert(0, '.')

import os
import json
from datetime import datetime, timedelta
import pytz

# Try to use colorama for colored output, fallback to no colors
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback - no colors
    class Fore:
        CYAN = RED = GREEN = YELLOW = BLUE = ''
    class Style:
        RESET_ALL = ''
    HAS_COLOR = False

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")

def print_test(name):
    print(f"\n{Fore.YELLOW}🧪 TEST: {name}{Style.RESET_ALL}")

def print_pass(msg):
    print(f"   {Fore.GREEN}✅ PASS:{Style.RESET_ALL} {msg}")

def print_fail(msg):
    print(f"   {Fore.RED}❌ FAIL:{Style.RESET_ALL} {msg}")

def print_warn(msg):
    print(f"   {Fore.YELLOW}⚠️  WARN:{Style.RESET_ALL} {msg}")

def print_info(msg):
    print(f"   {Fore.BLUE}ℹ️  INFO:{Style.RESET_ALL} {msg}")

# Test results tracking
tests_passed = 0
tests_failed = 0
tests_warned = 0

print_header("🚀 LiteBotX Comprehensive Production Test Suite")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# TEST 1: Environment & Credentials
# ============================================================================
print_header("TEST SUITE 1: Environment & Credentials")

print_test("1.1 - Alpaca API Credentials")
api_key = os.environ.get('APCA_API_KEY_ID')
secret_key = os.environ.get('APCA_API_SECRET_KEY')

if api_key and secret_key:
    print_pass(f"Alpaca credentials found")
    print_info(f"API Key: {api_key[:8]}...")
    tests_passed += 1
else:
    print_fail("Alpaca credentials not found in environment")
    tests_failed += 1

print_test("1.2 - Python Dependencies")
required_modules = [
    ('alpaca', 'alpaca-py'),
    ('yfinance', 'yfinance'),
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('pytz', 'pytz'),
]

for module_name, package_name in required_modules:
    try:
        __import__(module_name)
        print_pass(f"{package_name} installed")
        tests_passed += 1
    except ImportError:
        print_fail(f"{package_name} not installed")
        tests_failed += 1

# ============================================================================
# TEST 2: Core Files & Structure
# ============================================================================
print_header("TEST SUITE 2: Core Files & Structure")

print_test("2.1 - Required Files Exist")
required_files = [
    'start_litebotx.py',
    'positions.json',
    'config.py',
    'data_loader.py',
    'execution_engine.py',
    'pre_filter.py',
    'daily_watchlist_refresh.py',
    'logs/current_watchlist.json',
    'traders/short_cycle_trader.py',
]

for filepath in required_files:
    if os.path.exists(filepath):
        print_pass(f"{filepath} exists")
        tests_passed += 1
    else:
        print_fail(f"{filepath} missing")
        tests_failed += 1

print_test("2.2 - Directory Structure")
required_dirs = ['logs', 'traders', 'core', 'docs', 'test', 'scripts']

for dirpath in required_dirs:
    if os.path.isdir(dirpath):
        print_pass(f"{dirpath}/ exists")
        tests_passed += 1
    else:
        print_fail(f"{dirpath}/ missing")
        tests_failed += 1

# ============================================================================
# TEST 3: Watchlist Health
# ============================================================================
print_header("TEST SUITE 3: Watchlist Health")

print_test("3.1 - Watchlist File Valid")
try:
    with open('logs/current_watchlist.json', 'r') as f:
        watchlist = json.load(f)
    
    symbols = watchlist.get('symbols', [])
    generated_at_str = watchlist.get('generated_at', '')
    
    print_pass(f"Watchlist loaded successfully")
    print_info(f"Symbols: {len(symbols)}")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot load watchlist: {e}")
    tests_failed += 1
    symbols = []
    generated_at_str = None

print_test("3.2 - Watchlist Age Check")
if generated_at_str:
    try:
        generated_at = datetime.fromisoformat(generated_at_str)
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        age_hours = (now - generated_at).total_seconds() / 3600
        
        print_info(f"Age: {age_hours:.1f} hours")
        
        if age_hours < 24:
            print_pass("Watchlist is fresh (<24 hours)")
            tests_passed += 1
        else:
            print_warn(f"Watchlist is stale ({age_hours:.1f} hours old)")
            tests_warned += 1
    except Exception as e:
        print_fail(f"Cannot parse watchlist age: {e}")
        tests_failed += 1
else:
    print_fail("No timestamp in watchlist")
    tests_failed += 1

print_test("3.3 - Watchlist Size Check")
if symbols:
    print_info(f"Symbols: {', '.join(symbols)}")
    
    if 8 <= len(symbols) <= 20:
        print_pass(f"Optimal size: {len(symbols)} symbols")
        tests_passed += 1
    elif len(symbols) < 8:
        print_warn(f"Too few symbols: {len(symbols)} (need 8-20)")
        tests_warned += 1
    else:
        print_warn(f"Too many symbols: {len(symbols)} (need 8-20)")
        tests_warned += 1
else:
    print_fail("Watchlist is empty")
    tests_failed += 1

# ============================================================================
# TEST 4: Positions File Integrity
# ============================================================================
print_header("TEST SUITE 4: Positions File Integrity")

print_test("4.1 - Positions File Valid JSON")
try:
    with open('positions.json', 'r') as f:
        positions = json.load(f)
    
    print_pass(f"Loaded {len(positions)} positions")
    print_info(f"File size: {os.path.getsize('positions.json')/1024:.1f} KB")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot load positions.json: {e}")
    tests_failed += 1
    positions = []

print_test("4.2 - No Null Shares in Active Positions")
null_count = 0
active_positions = []

for pos in positions:
    status = pos.get('status', '')
    if status in ['entered', 'pending', 'active']:
        active_positions.append(pos)
        shares = pos.get('position_size_shares')
        if shares is None:
            null_count += 1
            print_fail(f"{pos.get('symbol')}: shares is null (status: {status})")

if null_count == 0:
    print_pass(f"All active positions have valid shares")
    tests_passed += 1
else:
    print_fail(f"{null_count} active positions have null shares")
    tests_failed += 1

print_test("4.3 - Position Data Completeness")
for pos in active_positions:
    symbol = pos.get('symbol', 'UNKNOWN')
    required_fields = [
        'symbol', 'entry_date', 'entry_price', 
        'position_size_shares', 'stop_price', 'status'
    ]
    
    missing_fields = [f for f in required_fields if pos.get(f) is None]
    
    if not missing_fields:
        print_pass(f"{symbol}: All required fields present")
        tests_passed += 1
    else:
        print_fail(f"{symbol}: Missing fields: {', '.join(missing_fields)}")
        tests_failed += 1

# ============================================================================
# TEST 5: Alpaca Account Connection
# ============================================================================
print_header("TEST SUITE 5: Alpaca Account Connection")

print_test("5.1 - Alpaca API Connection")
try:
    from alpaca.trading.client import TradingClient
    
    client = TradingClient(api_key, secret_key, paper=True)
    account = client.get_account()
    
    print_pass("Connected to Alpaca successfully")
    print_info(f"Account ID: {account.id}")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot connect to Alpaca: {e}")
    tests_failed += 1
    account = None

print_test("5.2 - Account Status")
if account:
    print_info(f"Equity: ${float(account.equity):,.2f}")
    print_info(f"Cash: ${float(account.cash):,.2f}")
    print_info(f"Buying Power: ${float(account.buying_power):,.2f}")
    
    if account.status == 'ACTIVE':
        print_pass("Account is ACTIVE")
        tests_passed += 1
    else:
        print_fail(f"Account status: {account.status}")
        tests_failed += 1
    
    if account.trading_blocked:
        print_fail("Trading is BLOCKED on account")
        tests_failed += 1
    else:
        print_pass("Trading is ENABLED")
        tests_passed += 1
else:
    print_fail("Cannot check account status")
    tests_failed += 1

print_test("5.3 - Position Sync Check")
if account:
    try:
        alpaca_positions = client.get_all_positions()
        alpaca_symbols = {pos.symbol: int(float(pos.qty)) for pos in alpaca_positions}
        
        print_info(f"Alpaca has {len(alpaca_positions)} positions")
        
        sync_issues = []
        for pos in active_positions:
            symbol = pos.get('symbol')
            local_shares = pos.get('position_size_shares')
            alpaca_shares = alpaca_symbols.get(symbol)
            
            if alpaca_shares is None:
                sync_issues.append(f"{symbol}: In file but not in Alpaca")
            elif local_shares != alpaca_shares:
                sync_issues.append(f"{symbol}: File has {local_shares}, Alpaca has {alpaca_shares}")
        
        if not sync_issues:
            print_pass("Positions are synced with Alpaca")
            tests_passed += 1
        else:
            for issue in sync_issues:
                print_warn(issue)
            tests_warned += 1
            
    except Exception as e:
        print_fail(f"Cannot check position sync: {e}")
        tests_failed += 1
else:
    print_fail("Cannot check position sync (no Alpaca connection)")
    tests_failed += 1

# ============================================================================
# TEST 6: Core Module Imports
# ============================================================================
print_header("TEST SUITE 6: Core Module Imports")

print_test("6.1 - Import Core Modules")
modules_to_test = [
    ('config', 'Config'),
    ('data_loader', 'DataLoader'),
    ('traders.short_cycle_trader', 'ShortCycleTrader'),
    ('traders.short_cycle_trader', 'ShortCycleConfig'),
]

for module_name, class_name in modules_to_test:
    try:
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)
        print_pass(f"Imported {module_name}.{class_name}")
        tests_passed += 1
    except Exception as e:
        print_fail(f"Cannot import {module_name}.{class_name}: {e}")
        tests_failed += 1

print_test("6.2 - Initialize Configuration")
try:
    from traders.short_cycle_trader import ShortCycleConfig
    
    config = ShortCycleConfig()
    print_pass("Configuration initialized")
    print_info(f"Portfolio: ${config.portfolio_value:,.0f}")
    print_info(f"Daily pool: ${config.daily_pool_dollars:,.0f}")
    print_info(f"Max positions per day: {config.max_positions_per_day}")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot initialize config: {e}")
    tests_failed += 1

print_test("6.3 - Initialize Data Loader")
try:
    from data_loader import DataLoader
    
    loader = DataLoader()
    print_pass("DataLoader initialized")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot initialize DataLoader: {e}")
    tests_failed += 1

# ============================================================================
# TEST 7: Trading Logic Components
# ============================================================================
print_header("TEST SUITE 7: Trading Logic Components")

print_test("7.1 - Position Sizer Test")
try:
    from traders.short_cycle_trader import AIConfidencePositionSizer, ShortCycleConfig, AISignal
    
    config = ShortCycleConfig()
    sizer = AIConfidencePositionSizer(config)
    
    # Create test signal
    test_signal = AISignal(
        symbol="TEST",
        action="BUY",
        confidence=0.75,
        time_horizon_days=1.0,
        entry_price=100.0,
        target_price=105.0,
        stop_price=98.0
    )
    
    shares, value = sizer.calculate_position_size(test_signal, 98.0, 500000)
    
    if shares is not None and shares > 0:
        print_pass(f"Position sizer works: {shares} shares, ${value:,.2f}")
        tests_passed += 1
    else:
        print_fail(f"Position sizer returned invalid: shares={shares}")
        tests_failed += 1
        
except Exception as e:
    print_fail(f"Position sizer test failed: {e}")
    tests_failed += 1

print_test("7.2 - PreFilter Test")
try:
    from pre_filter import PreFilter
    from data_loader import DataLoader
    
    loader = DataLoader()
    prefilter = PreFilter(
        simulation_mode=False,
        fast_mode=True,
        data_loader=loader
    )
    
    print_pass("PreFilter initialized")
    tests_passed += 1
except Exception as e:
    print_fail(f"PreFilter test failed: {e}")
    tests_failed += 1

# ============================================================================
# TEST 8: Start Script Validation
# ============================================================================
print_header("TEST SUITE 8: Start Script Validation")

print_test("8.1 - start_litebotx.py Structure")
try:
    with open('start_litebotx.py', 'r') as f:
        content = f.read()
    
    # Check it's not calling test function
    if 'test_short_cycle_system' in content:
        print_warn("Script still references test function")
        tests_warned += 1
    else:
        print_pass("Not calling test function")
        tests_passed += 1
    
    # Check it has production loop
    if 'while True' in content:
        print_pass("Has continuous loop")
        tests_passed += 1
    else:
        print_fail("No continuous loop found")
        tests_failed += 1
    
    # Check it has error handling
    if 'try:' in content and 'except' in content:
        print_pass("Has error handling")
        tests_passed += 1
    else:
        print_warn("Limited error handling")
        tests_warned += 1
        
except Exception as e:
    print_fail(f"Cannot validate start script: {e}")
    tests_failed += 1

# ============================================================================
# TEST 9: System Health Checks
# ============================================================================
print_header("TEST SUITE 9: System Health Checks")

print_test("9.1 - Disk Space")
import shutil
disk_usage = shutil.disk_usage('.')
free_gb = disk_usage.free / (1024**3)

print_info(f"Free space: {free_gb:.1f} GB")

if free_gb > 1.0:
    print_pass("Sufficient disk space")
    tests_passed += 1
else:
    print_warn(f"Low disk space: {free_gb:.1f} GB")
    tests_warned += 1

print_test("9.2 - Log File Access")
log_files = ['logs/trading_bot.log', 'logs/bot.log', 'logs/dashboard.log']

for log_file in log_files:
    if os.path.exists(log_file):
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n# Test write at {datetime.now()}\n")
            print_pass(f"{log_file} writable")
            tests_passed += 1
        except Exception as e:
            print_fail(f"{log_file} not writable: {e}")
            tests_failed += 1
    else:
        print_info(f"{log_file} will be created on startup")
        tests_passed += 1

print_test("9.3 - Market Hours Check")
et_tz = pytz.timezone('US/Eastern')
now_et = datetime.now(et_tz)
current_time = now_et.time()
current_day = now_et.weekday()  # 0=Monday, 6=Sunday

market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0).time()
market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0).time()

is_weekday = current_day < 5
is_market_hours = market_open <= current_time <= market_close

print_info(f"Current time: {now_et.strftime('%I:%M %p ET')}")
print_info(f"Day: {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][current_day]}")

if is_weekday and is_market_hours:
    print_pass("Market is OPEN - bot will trade")
    tests_passed += 1
elif is_weekday:
    print_info("Market is CLOSED - bot will wait")
    tests_passed += 1
else:
    print_info("Weekend - bot will wait for Monday")
    tests_passed += 1

# ============================================================================
# TEST 10: Integration Test (Dry Run)
# ============================================================================
print_header("TEST SUITE 10: Integration Test (Quick Dry Run)")

print_test("10.1 - Initialize Full Trader")
try:
    from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
    
    config = ShortCycleConfig()
    trader = ShortCycleTrader(config)
    
    print_pass("Trader initialized successfully")
    print_info(f"Positions loaded: {len(trader.positions)}")
    tests_passed += 1
except Exception as e:
    print_fail(f"Cannot initialize trader: {e}")
    import traceback
    traceback.print_exc()
    tests_failed += 1

# ============================================================================
# FINAL RESULTS
# ============================================================================
print_header("📊 TEST RESULTS SUMMARY")

total_tests = tests_passed + tests_failed + tests_warned

print(f"\n{Fore.GREEN}✅ PASSED: {tests_passed}/{total_tests}{Style.RESET_ALL}")
print(f"{Fore.RED}❌ FAILED: {tests_failed}/{total_tests}{Style.RESET_ALL}")
print(f"{Fore.YELLOW}⚠️  WARNED: {tests_warned}/{total_tests}{Style.RESET_ALL}")

pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"\n{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}")

if tests_failed == 0:
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}🎉 ALL CRITICAL TESTS PASSED - BOT IS READY FOR PRODUCTION!")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}To start the bot:{Style.RESET_ALL}")
    print(f"   python3 start_litebotx.py")
    sys.exit(0)
elif tests_failed <= 2 and tests_warned <= 3:
    print(f"\n{Fore.YELLOW}{'='*80}")
    print(f"{Fore.YELLOW}⚠️  MINOR ISSUES DETECTED - REVIEW BEFORE PRODUCTION")
    print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}Fix the failed tests above before running in production.{Style.RESET_ALL}")
    sys.exit(1)
else:
    print(f"\n{Fore.RED}{'='*80}")
    print(f"{Fore.RED}❌ CRITICAL FAILURES - DO NOT RUN IN PRODUCTION")
    print(f"{Fore.RED}{'='*80}{Style.RESET_ALL}")
    print(f"\n{Fore.RED}Fix the critical issues above before proceeding.{Style.RESET_ALL}")
    sys.exit(1)
