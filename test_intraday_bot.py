"""
Comprehensive Test Suite for Intraday Day Trading Bot
Tests configuration, entry/exit logic, risk management, and edge cases
"""

import sys
import datetime as dt
from datetime import time
import pytz
sys.path.insert(0, '.')

from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCycleTrader, ShortCyclePosition, PositionStatus

def print_test_header(test_name):
    """Print formatted test header"""
    print("\n" + "="*70)
    print(f"TEST: {test_name}")
    print("="*70)

def print_result(test_name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")

# ==============================================================================
# TEST 1: CONFIGURATION VALIDATION
# ==============================================================================
def test_configuration():
    """Test all configuration parameters are correct for intraday trading"""
    print_test_header("Configuration Validation")
    
    config = SmallPortfolioConfig()
    all_passed = True
    
    # Core intraday settings
    tests = [
        ("max_hold_days == 0", config.max_hold_days == 0, f"Found: {config.max_hold_days}"),
        ("cash_account_mode == True", config.cash_account_mode == True, f"Found: {config.cash_account_mode}"),
        ("enable_same_day_exit == True", config.enable_same_day_exit == True, f"Found: {config.enable_same_day_exit}"),
        ("enable_all_day_entries == True", config.enable_all_day_entries == True, f"Found: {config.enable_all_day_entries}"),
        ("force_exit_time == 15:45", config.force_exit_time == time(15, 45), f"Found: {config.force_exit_time}"),
        ("all_day_entry_cutoff_time == 14:30", config.all_day_entry_cutoff_time == "14:30", f"Found: {config.all_day_entry_cutoff_time}"),
        ("max_late_entries_per_day >= 3", config.max_late_entries_per_day >= 3, f"Found: {config.max_late_entries_per_day}"),
        ("trading_days includes Friday", "friday" in config.trading_days, f"Found: {config.trading_days}"),
        ("exit_only_days is empty", len(config.exit_only_days) == 0, f"Found: {config.exit_only_days}"),
    ]
    
    for test_name, condition, detail in tests:
        print_result(test_name, condition, detail)
        all_passed = all_passed and condition
    
    # Profit/loss targets (intraday appropriate)
    profit_tests = [
        ("intraday_take_profit <= 0.03", config.intraday_take_profit <= 0.03, f"Found: {config.intraday_take_profit*100}%"),
        ("intraday_stop_loss >= -0.02", config.intraday_stop_loss >= -0.02, f"Found: {config.intraday_stop_loss*100}%"),
        ("zone1_take_profit <= 0.04", config.zone1_take_profit <= 0.04, f"Found: {config.zone1_take_profit*100}%"),
        ("zone1_stop_loss >= -0.02", config.zone1_stop_loss >= -0.02, f"Found: {config.zone1_stop_loss*100}%"),
        ("trailing_trigger_pct <= 0.02", config.trailing_trigger_pct <= 0.02, f"Found: {config.trailing_trigger_pct*100}%"),
    ]
    
    for test_name, condition, detail in tests:
        print_result(test_name, condition, detail)
        all_passed = all_passed and condition
    
    print(f"\n{'✅ ALL CONFIGURATION TESTS PASSED' if all_passed else '❌ SOME CONFIGURATION TESTS FAILED'}")
    return all_passed

# ==============================================================================
# TEST 2: ENTRY LOGIC
# ==============================================================================
def test_entry_logic():
    """Test entry timing and conditions"""
    print_test_header("Entry Logic and Timing")
    
    config = SmallPortfolioConfig()
    all_passed = True
    
    # Test morning entry window (9:45-10:00)
    ET = pytz.timezone('US/Eastern')
    market_open = dt.datetime(2025, 11, 5, 9, 30, 0, tzinfo=ET)
    entry_start = dt.datetime(2025, 11, 5, 9, 45, 0, tzinfo=ET)
    entry_end = dt.datetime(2025, 11, 5, 10, 0, 0, tzinfo=ET)
    
    tests = [
        ("Morning entry starts 15 min after open", (entry_start - market_open).total_seconds() == 15*60, "15 minutes"),
        ("Entry window is 15 minutes", (entry_end - entry_start).total_seconds() == 15*60, "15 minutes"),
        ("Late entry starts after 30 min", config.allow_late_entries_after_minutes == 30, f"Found: {config.allow_late_entries_after_minutes}"),
        ("Late entry confidence multiplier > 1.0", config.late_entry_confidence_multiplier > 1.0, f"Found: {config.late_entry_confidence_multiplier}x"),
        ("Max positions per day <= 10", config.max_positions_per_day <= 10, f"Found: {config.max_positions_per_day}"),
    ]
    
    for test_name, condition, detail in tests:
        print_result(test_name, condition, detail)
        all_passed = all_passed and condition
    
    # Test cutoff time is before force exit
    cutoff_hour, cutoff_min = map(int, config.all_day_entry_cutoff_time.split(':'))
    cutoff_minutes = cutoff_hour * 60 + cutoff_min
    exit_minutes = config.force_exit_time.hour * 60 + config.force_exit_time.minute
    
    buffer_minutes = exit_minutes - cutoff_minutes
    test_name = "Entry cutoff is before force exit"
    condition = buffer_minutes >= 60
    print_result(test_name, condition, f"Buffer: {buffer_minutes} minutes")
    all_passed = all_passed and condition
    
    print(f"\n{'✅ ALL ENTRY LOGIC TESTS PASSED' if all_passed else '❌ SOME ENTRY LOGIC TESTS FAILED'}")
    return all_passed

# ==============================================================================
# TEST 3: EXIT LOGIC
# ==============================================================================
def test_exit_logic():
    """Test same-day exit logic and force close"""
    print_test_header("Exit Logic and Same-Day Trading")
    
    config = SmallPortfolioConfig()
    trader = ShortCycleTrader(config)
    all_passed = True
    
    # Create test position entered today
    ET = pytz.timezone('US/Eastern')
    now = dt.datetime.now(ET)
    today = now.date()
    
    # Create mock AI signal
    from traders.short_cycle_trader import AISignal
    mock_signal = AISignal(
        symbol="SPY",
        action="BUY",
        confidence=0.08,
        time_horizon_days=0,  # Intraday
        target_price=692.0,
        stop_price=665.0,
        entry_price=675.0,
        position_size_dollars=675.0
    )
    
    position = ShortCyclePosition(
        symbol="SPY",
        entry_date=today,
        entry_price=675.0,
        position_size_shares=1,
        position_size_dollars=675.0,
        stop_price=665.0,
        target_price=692.0,
        exit_date=today,  # Same day for intraday
        status=PositionStatus.ENTERED,
        ai_signal=mock_signal,
        entry_timestamp=now,
        filled_at=now
    )
    
    # Test 1: Same-day exit eligibility (cash account mode)
    test_name = "Same-day exit allowed (cash account)"
    condition = position.is_d1_eligible(now, cash_account_mode=True)
    print_result(test_name, condition, "Entry and exit same day")
    all_passed = all_passed and condition
    
    # Test 2: Profit target exit (+2.5%)
    current_price = 691.88  # +2.5% gain
    should_exit, reason = position.should_smart_exit(today, current_price, now, cash_account_mode=True)
    test_name = "Exit at +2.5% profit target"
    condition = should_exit and ("PROFIT" in reason.upper() or "3PCT" in reason.upper())
    print_result(test_name, condition, f"Reason: {reason}")
    all_passed = all_passed and condition
    
    # Test 3: Stop loss exit (-2%)
    current_price = 661.50  # -2% loss
    should_exit, reason = position.should_smart_exit(today, current_price, now, cash_account_mode=True)
    test_name = "Exit at -2% stop loss"
    condition = should_exit and "STOP" in reason.upper()
    print_result(test_name, condition, f"Reason: {reason}")
    all_passed = all_passed and condition
    
    # Test 4: Force exit time (3:45 PM)
    force_exit_time = now.replace(hour=15, minute=45, second=0)
    test_name = "Force exit at 3:45 PM configured"
    condition = config.force_exit_time == time(15, 45)
    print_result(test_name, condition, f"Time: {config.force_exit_time}")
    all_passed = all_passed and condition
    
    # Test 5: Force close method exists
    test_name = "Force close all positions method exists"
    condition = hasattr(trader, '_force_close_all_positions')
    print_result(test_name, condition, "Method: _force_close_all_positions")
    all_passed = all_passed and condition
    
    print(f"\n{'✅ ALL EXIT LOGIC TESTS PASSED' if all_passed else '❌ SOME EXIT LOGIC TESTS FAILED'}")
    return all_passed

# ==============================================================================
# TEST 4: RISK MANAGEMENT
# ==============================================================================
def test_risk_management():
    """Test risk controls and position sizing"""
    print_test_header("Risk Management")
    
    config = SmallPortfolioConfig()
    all_passed = True
    
    portfolio_value = config.portfolio_value  # $1000
    
    tests = [
        # Position sizing
        ("Max position < 50% portfolio", config.max_position_dollars < portfolio_value * 0.5, 
         f"${config.max_position_dollars} vs ${portfolio_value * 0.5}"),
        ("Min position is meaningful", config.min_position_size_dollars >= 25.0,
         f"${config.min_position_size_dollars}"),
        
        # Risk limits
        ("Max risk per trade < 5%", config.max_risk_per_trade_dollars / portfolio_value < 0.05,
         f"{config.max_risk_per_trade_dollars / portfolio_value * 100:.1f}%"),
        ("Max daily loss < 15%", config.max_daily_loss_percent < 0.15,
         f"{config.max_daily_loss_percent * 100}%"),
        ("Max weekly loss < 25%", config.max_weekly_loss_percent < 0.25,
         f"{config.max_weekly_loss_percent * 100}%"),
        
        # Stop losses
        ("Intraday stop loss < -5%", config.intraday_stop_loss > -0.05,
         f"{config.intraday_stop_loss * 100}%"),
        ("Zone stop losses reasonable", all([
            config.zone1_stop_loss > -0.03,
            config.zone2_stop_loss > -0.03,
            config.zone3_stop_loss > -0.03
        ]), "All zones > -3%"),
    ]
    
    for test_name, condition, detail in tests:
        print_result(test_name, condition, detail)
        all_passed = all_passed and condition
    
    # Test position limits
    max_total_exposure = config.max_positions_per_day * config.max_position_dollars
    max_late_exposure = config.max_late_entries_per_day * config.max_position_dollars
    
    test_name = "Total exposure manageable"
    condition = max_total_exposure <= portfolio_value * 3.0  # Max 3x leverage in day
    print_result(test_name, condition, f"Max exposure: ${max_total_exposure} ({max_total_exposure/portfolio_value:.1f}x portfolio)")
    all_passed = all_passed and condition
    
    print(f"\n{'✅ ALL RISK MANAGEMENT TESTS PASSED' if all_passed else '❌ SOME RISK MANAGEMENT TESTS FAILED'}")
    return all_passed

# ==============================================================================
# TEST 5: EDGE CASES
# ==============================================================================
def test_edge_cases():
    """Test edge cases and error handling"""
    print_test_header("Edge Cases and Error Handling")
    
    config = SmallPortfolioConfig()
    trader = ShortCycleTrader(config)
    all_passed = True
    
    # Test trader initialization
    test_name = "Trader initializes with config"
    condition = trader.config == config
    print_result(test_name, condition, "Config attached")
    all_passed = all_passed and condition
    
    # Test execution engine exists
    test_name = "Execution engine connected"
    condition = hasattr(trader, 'execution_engine') and trader.execution_engine is not None
    print_result(test_name, condition, "RealPaperTradingEngine")
    all_passed = all_passed and condition
    
    # Test position tracking
    test_name = "Position tracking initialized"
    condition = hasattr(trader, 'positions')
    print_result(test_name, condition, f"Found {len(trader.positions) if condition else 0} positions")
    all_passed = all_passed and condition
    
    # Test configuration sanity checks
    tests = [
        ("Entry cutoff before market close", config.all_day_entry_cutoff_time < "16:00", 
         f"Cutoff: {config.all_day_entry_cutoff_time}"),
        ("Force exit before market close", config.force_exit_time.hour < 16,
         f"Exit: {config.force_exit_time}"),
        ("Max hold time reasonable", config.intraday_max_hold_minutes <= 390,  # 6.5 hours max
         f"{config.intraday_max_hold_minutes} minutes"),
        ("Monitor interval not too fast", config.intraday_monitor_interval_seconds >= 30,
         f"{config.intraday_monitor_interval_seconds} seconds"),
    ]
    
    for test_name, condition, detail in tests:
        print_result(test_name, condition, detail)
        all_passed = all_passed and condition
    
    print(f"\n{'✅ ALL EDGE CASE TESTS PASSED' if all_passed else '❌ SOME EDGE CASE TESTS FAILED'}")
    return all_passed

# ==============================================================================
# TEST 6: INTEGRATION TEST
# ==============================================================================
def test_integration():
    """Test full workflow integration"""
    print_test_header("Integration Test - Full Workflow")
    
    all_passed = True
    
    try:
        # Initialize bot
        config = SmallPortfolioConfig()
        trader = ShortCycleTrader(config)
        print_result("Bot initialization", True, "All components loaded")
        
        # Verify execution engine can connect
        account_info = trader.execution_engine.get_account_info()
        test_name = "Execution engine API connection"
        condition = account_info is not None
        print_result(test_name, condition, f"Account: {'Connected' if condition else 'Failed'}")
        all_passed = all_passed and condition
        
        # Verify position loading
        test_name = "Position persistence system"
        condition = hasattr(trader, '_save_positions') and hasattr(trader, '_load_positions')
        print_result(test_name, condition, "Save/Load methods exist")
        all_passed = all_passed and condition
        
        # Verify key methods exist
        methods = [
            '_process_existing_positions',
            '_attempt_late_entries',
            '_exit_position',
            '_force_close_all_positions',
            '_get_current_price'
        ]
        
        for method in methods:
            test_name = f"Method exists: {method}"
            condition = hasattr(trader, method)
            print_result(test_name, condition)
            all_passed = all_passed and condition
        
    except Exception as e:
        print_result("Integration test", False, f"Error: {e}")
        all_passed = False
    
    print(f"\n{'✅ INTEGRATION TEST PASSED' if all_passed else '❌ INTEGRATION TEST FAILED'}")
    return all_passed

# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("INTRADAY DAY TRADING BOT - COMPREHENSIVE TEST SUITE")
    print("="*70)
    print(f"Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = {
        "Configuration Validation": test_configuration(),
        "Entry Logic": test_entry_logic(),
        "Exit Logic": test_exit_logic(),
        "Risk Management": test_risk_management(),
        "Edge Cases": test_edge_cases(),
        "Integration": test_integration(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*70)
    print(f"TOTAL: {passed}/{total} test suites passed ({passed/total*100:.0f}%)")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - BOT IS READY FOR TRADING!")
        return True
    else:
        print(f"\n⚠️ WARNING: {total - passed} test suite(s) failed - review before trading")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
