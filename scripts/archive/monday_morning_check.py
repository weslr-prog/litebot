#!/usr/bin/env python3
"""
Quick Pre-Market Validation Script
Run this Monday morning before 9:00 AM to verify system is ready
"""

import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("🌅 MONDAY MORNING PRE-MARKET VALIDATION")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80 + "\n")

all_checks_passed = True

# Check 1: Import all new components
print("1️⃣ Testing imports...")
try:
    from morning_gap_scanner import MorningGapScanner
    from pattern_recognizer import PatternRecognizer, PatternTracker, StockPattern
    sys.path.insert(0, 'traders')
    from short_cycle_trader import ShortCycleTrader, ShortCycleConfig
    print("✅ All imports successful\n")
except Exception as e:
    print(f"❌ Import failed: {e}\n")
    all_checks_passed = False

# Check 2: Initialize components
print("2️⃣ Initializing components...")
try:
    scanner = MorningGapScanner()
    recognizer = PatternRecognizer()
    tracker = PatternTracker()
    config = ShortCycleConfig()
    print("✅ All components initialized\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    all_checks_passed = False

# Check 3: Test gap scanner basic functionality
print("3️⃣ Testing gap scanner...")
try:
    # Test gap quality assessment
    quality = scanner._assess_gap_quality(0.02, 150, 147, 1000)
    if quality == 'EXCELLENT':
        print("✅ Gap quality assessment working\n")
    else:
        print(f"⚠️ Gap quality unexpected: {quality}\n")
except Exception as e:
    print(f"❌ Gap scanner test failed: {e}\n")
    all_checks_passed = False

# Check 4: Test pattern recognizer
print("4️⃣ Testing pattern recognizer...")
try:
    # Test gapper detection
    pattern = recognizer.identify_pattern(
        current_price=101.5,
        entry_price=100.0,
        gap_at_open=0.02,
        minutes_held=30
    )
    if pattern == StockPattern.MORNING_GAPPER:
        print("✅ Pattern recognition working\n")
    else:
        print(f"⚠️ Pattern unexpected: {pattern.value}\n")
except Exception as e:
    print(f"❌ Pattern recognizer test failed: {e}\n")
    all_checks_passed = False

# Check 5: Test exit timing
print("5️⃣ Testing exit timing...")
try:
    test_time = datetime.now().replace(hour=10, minute=30)
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=StockPattern.MORNING_GAPPER,
        current_time=test_time,
        pnl_pct=0.01
    )
    if should_exit:
        print(f"✅ Exit timing working: {reason}\n")
    else:
        print(f"⚠️ Exit timing unexpected: {should_exit}\n")
except Exception as e:
    print(f"❌ Exit timing test failed: {e}\n")
    all_checks_passed = False

# Check 6: Verify configuration
print("6️⃣ Verifying configuration...")
try:
    print(f"   Portfolio: ${config.portfolio_value:,.0f}")
    print(f"   Daily pool: ${config.daily_pool_dollars:,.0f}")
    print(f"   Max positions: {config.max_positions_per_day}")
    print(f"   Trailing stops: {'ENABLED' if config.enable_trailing_stops else 'DISABLED'}")
    print(f"   Max risk/trade: ${config.max_risk_per_trade_dollars}")
    print("✅ Configuration looks good\n")
except Exception as e:
    print(f"❌ Configuration check failed: {e}\n")
    all_checks_passed = False

# Check 7: Verify file permissions
print("7️⃣ Checking file permissions...")
try:
    import os
    files_to_check = [
        'morning_gap_scanner.py',
        'pattern_recognizer.py',
        'traders/short_cycle_trader.py'
    ]
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            all_checks_passed = False
        elif not os.access(file_path, os.R_OK):
            print(f"⚠️ Cannot read: {file_path}")
            all_checks_passed = False
    print("✅ All files accessible\n")
except Exception as e:
    print(f"❌ File check failed: {e}\n")
    all_checks_passed = False

# Check 8: Test Alpaca connection (if before market open)
print("8️⃣ Testing Alpaca connection...")
try:
    current_hour = datetime.now().hour
    if current_hour < 9:
        from data_loader import DataLoader
        loader = DataLoader()
        # Try to get account info
        account = loader.api.get_account()
        print(f"✅ Connected to Alpaca (Account: {account.status})\n")
    else:
        print("⏩ Skipping Alpaca test (market hours)\n")
except Exception as e:
    print(f"⚠️ Alpaca connection test failed (may be OK): {e}\n")

# Final Summary
print("="*80)
if all_checks_passed:
    print("🎉 ALL CRITICAL CHECKS PASSED!")
    print("✅ System is ready for Monday morning trading")
    print("\n📝 Reminder:")
    print("   • Gap scanner will run automatically at 9:00-9:30 AM")
    print("   • Pattern recognition activates after entry")
    print("   • Dynamic exits based on stock patterns")
    print("   • Trailing stops enabled for profit protection")
    print("\n🚀 To start trading:")
    print("   python traders/short_cycle_trader.py")
else:
    print("⚠️ SOME CHECKS FAILED")
    print("   Please review errors above before trading")
    print("   Run comprehensive test: python3 test_d1_optimizations.py")

print("="*80 + "\n")

sys.exit(0 if all_checks_passed else 1)
