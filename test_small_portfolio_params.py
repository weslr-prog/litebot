#!/usr/bin/env python3
"""
Test Suite for Small Portfolio Configuration Changes
Created: November 10, 2025
Purpose: Validate all parameter changes from optimization plan
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_import_config():
    """Test 1: Config imports without errors"""
    print("TEST 1: Import Configuration")
    try:
        from small_portfolio_config import SmallPortfolioConfig
        config = SmallPortfolioConfig()
        print("✅ PASS - Config imported successfully")
        return True, config
    except Exception as e:
        print(f"❌ FAIL - Import error: {e}")
        return False, None


def test_price_range(config):
    """Test 2: Price range matches optimization plan ($10-30)"""
    print("\nTEST 2: Price Range Validation")
    
    if config.min_price != 10.0:
        print(f"❌ FAIL - min_price is {config.min_price}, expected 10.0")
        return False
    
    if config.max_price != 30.0:
        print(f"❌ FAIL - max_price is {config.max_price}, expected 30.0")
        return False
    
    print(f"✅ PASS - Price range: ${config.min_price}-${config.max_price} (correct)")
    return True


def test_exit_zones(config):
    """Test 3: Exit zones match optimization plan (TP 3-4%, SL -2-3%)"""
    print("\nTEST 3: Exit Zone Validation")
    
    errors = []
    
    # Zone 1: TP +3%, SL -2%
    if config.zone1_take_profit != 0.03:
        errors.append(f"zone1_take_profit is {config.zone1_take_profit}, expected 0.03")
    if config.zone1_stop_loss != -0.02:
        errors.append(f"zone1_stop_loss is {config.zone1_stop_loss}, expected -0.02")
    
    # Zone 2: TP +4%, SL -3%
    if config.zone2_take_profit != 0.04:
        errors.append(f"zone2_take_profit is {config.zone2_take_profit}, expected 0.04")
    if config.zone2_stop_loss != -0.03:
        errors.append(f"zone2_stop_loss is {config.zone2_stop_loss}, expected -0.03")
    
    # Zone 3: TP +2.5%, SL -2%
    if config.zone3_take_profit != 0.025:
        errors.append(f"zone3_take_profit is {config.zone3_take_profit}, expected 0.025")
    if config.zone3_stop_loss != -0.02:
        errors.append(f"zone3_stop_loss is {config.zone3_stop_loss}, expected -0.02")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL - {error}")
        return False
    
    print("✅ PASS - All exit zones correct:")
    print(f"  Zone 1: TP +{config.zone1_take_profit*100}%, SL {config.zone1_stop_loss*100}%")
    print(f"  Zone 2: TP +{config.zone2_take_profit*100}%, SL {config.zone2_stop_loss*100}%")
    print(f"  Zone 3: TP +{config.zone3_take_profit*100}%, SL {config.zone3_stop_loss*100}%")
    return True


def test_trailing_stops(config):
    """Test 4: Trailing stops match optimization plan (3% trigger, 2% trail)"""
    print("\nTEST 4: Trailing Stop Validation")
    
    errors = []
    
    if config.trailing_trigger_pct != 0.03:
        errors.append(f"trailing_trigger_pct is {config.trailing_trigger_pct}, expected 0.03")
    
    if config.trailing_distance_pct != 0.02:
        errors.append(f"trailing_distance_pct is {config.trailing_distance_pct}, expected 0.02")
    
    if config.trailing_min_profit_pct != 0.01:
        errors.append(f"trailing_min_profit_pct is {config.trailing_min_profit_pct}, expected 0.01")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL - {error}")
        return False
    
    print("✅ PASS - Trailing stops correct:")
    print(f"  Trigger: {config.trailing_trigger_pct*100}%")
    print(f"  Trail distance: {config.trailing_distance_pct*100}%")
    print(f"  Min profit: {config.trailing_min_profit_pct*100}%")
    return True


def test_position_sizing(config):
    """Test 5: Position sizing matches optimization plan"""
    print("\nTEST 5: Position Sizing Validation")
    
    errors = []
    
    # Daily pool: 80% of $1K = $800
    if config.daily_pool_percent != 0.80:
        errors.append(f"daily_pool_percent is {config.daily_pool_percent}, expected 0.80")
    
    if config.daily_pool_dollars != 800.0:
        errors.append(f"daily_pool_dollars is {config.daily_pool_dollars}, expected 800.0")
    
    # Max position: $200 (20% of $1K)
    if config.max_position_dollars != 200.0:
        errors.append(f"max_position_dollars is {config.max_position_dollars}, expected 200.0")
    
    # Min position: $100
    if config.min_position_size_dollars != 100.0:
        errors.append(f"min_position_size_dollars is {config.min_position_size_dollars}, expected 100.0")
    
    # Max positions per day: 5
    if config.max_positions_per_day != 5:
        errors.append(f"max_positions_per_day is {config.max_positions_per_day}, expected 5")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL - {error}")
        return False
    
    print("✅ PASS - Position sizing correct:")
    print(f"  Daily pool: {config.daily_pool_percent*100}% = ${config.daily_pool_dollars}")
    print(f"  Max position: ${config.max_position_dollars}")
    print(f"  Min position: ${config.min_position_size_dollars}")
    print(f"  Max positions/day: {config.max_positions_per_day}")
    return True


def test_risk_limits(config):
    """Test 6: Risk limits match optimization plan"""
    print("\nTEST 6: Risk Limits Validation")
    
    errors = []
    
    # Risk per trade: $20 (2% of $1K)
    if config.max_risk_per_trade_dollars != 20.0:
        errors.append(f"max_risk_per_trade_dollars is {config.max_risk_per_trade_dollars}, expected 20.0")
    
    # Max loss per trade: $50 (5% of $1K)
    if config.max_loss_per_trade_dollars != 50.0:
        errors.append(f"max_loss_per_trade_dollars is {config.max_loss_per_trade_dollars}, expected 50.0")
    
    # Daily loss: 3% of $1K = $30
    if config.max_daily_loss_percent != 0.03:
        errors.append(f"max_daily_loss_percent is {config.max_daily_loss_percent}, expected 0.03")
    
    if config.max_daily_loss_dollars != 30.0:
        errors.append(f"max_daily_loss_dollars is {config.max_daily_loss_dollars}, expected 30.0")
    
    # Weekly loss: 10% of $1K = $100
    if config.max_weekly_loss_percent != 0.10:
        errors.append(f"max_weekly_loss_percent is {config.max_weekly_loss_percent}, expected 0.10")
    
    if config.max_weekly_loss_dollars != 100.0:
        errors.append(f"max_weekly_loss_dollars is {config.max_weekly_loss_dollars}, expected 100.0")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL - {error}")
        return False
    
    print("✅ PASS - Risk limits correct:")
    print(f"  Risk/trade: ${config.max_risk_per_trade_dollars} (2%)")
    print(f"  Max loss/trade: ${config.max_loss_per_trade_dollars} (5%)")
    print(f"  Daily loss limit: ${config.max_daily_loss_dollars} (3%)")
    print(f"  Weekly loss limit: ${config.max_weekly_loss_dollars} (10%)")
    return True


def test_math_consistency(config):
    """Test 7: Math relationships are consistent"""
    print("\nTEST 7: Math Consistency Validation")
    
    errors = []
    
    # Check exit zones: TP should be > SL (in absolute terms)
    if abs(config.zone1_take_profit) <= abs(config.zone1_stop_loss):
        errors.append("Zone 1: Take profit not greater than stop loss")
    
    if abs(config.zone2_take_profit) <= abs(config.zone2_stop_loss):
        errors.append("Zone 2: Take profit not greater than stop loss")
    
    if abs(config.zone3_take_profit) <= abs(config.zone3_stop_loss):
        errors.append("Zone 3: Take profit not greater than stop loss")
    
    # Check trailing stops: trigger > distance
    if config.trailing_trigger_pct <= config.trailing_distance_pct:
        errors.append("Trailing trigger should be > trailing distance")
    
    # Check position limits: max > min
    if config.max_position_dollars <= config.min_position_size_dollars:
        errors.append("Max position should be > min position")
    
    # Check price range: max > min
    if config.max_price <= config.min_price:
        errors.append("Max price should be > min price")
    
    # Check volatility range: max > min
    if config.max_volatility <= config.min_volatility:
        errors.append("Max volatility should be > min volatility")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL - {error}")
        return False
    
    print("✅ PASS - All math relationships consistent")
    return True


def test_attribute_existence(config):
    """Test 8: All critical attributes exist"""
    print("\nTEST 8: Attribute Existence Validation")
    
    required_attrs = [
        'portfolio_value',
        'daily_pool_percent',
        'max_position_dollars',
        'min_position_size_dollars',
        'max_positions_per_day',
        'max_risk_per_trade_dollars',
        'max_loss_per_trade_dollars',
        'max_daily_loss_percent',
        'max_weekly_loss_percent',
        'min_price',
        'max_price',
        'min_volatility',
        'max_volatility',
        'zone1_take_profit',
        'zone1_stop_loss',
        'zone2_take_profit',
        'zone2_stop_loss',
        'zone3_take_profit',
        'zone3_stop_loss',
        'trailing_trigger_pct',
        'trailing_distance_pct',
        'confidence_threshold',
        'min_avg_volume',
        'min_dollar_volume',
    ]
    
    missing = []
    for attr in required_attrs:
        if not hasattr(config, attr):
            missing.append(attr)
    
    if missing:
        print(f"❌ FAIL - Missing attributes: {', '.join(missing)}")
        return False
    
    print(f"✅ PASS - All {len(required_attrs)} required attributes exist")
    return True


def test_position_size_calculation(config):
    """Test 9: Position size calculation works correctly"""
    print("\nTEST 9: Position Size Calculation")
    
    try:
        # Test with different confidence levels
        test_cases = [
            ('high', 20.0, 800.0),   # High confidence, $20 stock, $800 available
            ('medium', 15.0, 800.0), # Medium confidence
            ('low', 25.0, 800.0),    # Low confidence
        ]
        
        for confidence, price, available in test_cases:
            size = config.get_position_size(price, confidence, available)
            
            # Size should be between min and max
            if size < 0 or size > config.max_position_dollars:
                print(f"❌ FAIL - Position size ${size} out of range for {confidence}")
                return False
        
        print("✅ PASS - Position size calculations working")
        return True
        
    except Exception as e:
        print(f"❌ FAIL - Position size calculation error: {e}")
        return False


def test_daily_pool_calculation(config):
    """Test 10: Daily pool calculation works correctly"""
    print("\nTEST 10: Daily Pool Calculation")
    
    try:
        # Test Monday-Wednesday: 80% of portfolio
        monday_pool = config.get_daily_pool('monday', 1000.0, 0.0)
        if monday_pool != 800.0:
            print(f"❌ FAIL - Monday pool is ${monday_pool}, expected $800")
            return False
        
        # Test Thursday: all available cash
        thursday_pool = config.get_daily_pool('thursday', 1000.0, 200.0)
        if thursday_pool != 800.0:  # 1000 - 200 open positions
            print(f"❌ FAIL - Thursday pool is ${thursday_pool}, expected $800")
            return False
        
        # Test Friday: should be 0 (exit only)
        friday_pool = config.get_daily_pool('friday', 1000.0, 0.0)
        if friday_pool != 0.0:
            print(f"❌ FAIL - Friday pool is ${friday_pool}, expected $0")
            return False
        
        print("✅ PASS - Daily pool calculations correct")
        return True
        
    except Exception as e:
        print(f"❌ FAIL - Daily pool calculation error: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("=" * 70)
    print("SMALL PORTFOLIO CONFIGURATION - TEST SUITE")
    print("=" * 70)
    
    # Test 1: Import
    success, config = test_import_config()
    if not success:
        print("\n❌ CRITICAL FAILURE - Cannot proceed with other tests")
        return False
    
    # Run all other tests
    results = []
    results.append(("Price Range", test_price_range(config)))
    results.append(("Exit Zones", test_exit_zones(config)))
    results.append(("Trailing Stops", test_trailing_stops(config)))
    results.append(("Position Sizing", test_position_sizing(config)))
    results.append(("Risk Limits", test_risk_limits(config)))
    results.append(("Math Consistency", test_math_consistency(config)))
    results.append(("Attribute Existence", test_attribute_existence(config)))
    results.append(("Position Size Calc", test_position_size_calculation(config)))
    results.append(("Daily Pool Calc", test_daily_pool_calculation(config)))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results) + 1  # +1 for import test
    
    print(f"\nPassed: {passed + 1}/{total} tests")
    
    if passed + 1 == total:
        print("\n🎉 ALL TESTS PASSED - Configuration ready for paper trading!")
        print("\nKey Parameters:")
        print(f"  Stock price range: ${config.min_price}-${config.max_price}")
        print(f"  Position size: ${config.min_position_size_dollars}-${config.max_position_dollars}")
        print(f"  Daily pool: ${config.daily_pool_dollars} ({config.daily_pool_percent*100}%)")
        print(f"  Exit targets: +{config.zone2_take_profit*100}% TP, {config.zone2_stop_loss*100}% SL")
        print(f"  Trailing stops: {config.trailing_trigger_pct*100}% trigger, {config.trailing_distance_pct*100}% trail")
        return True
    else:
        print("\n⚠️  SOME TESTS FAILED - Review errors above")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
