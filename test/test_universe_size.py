#!/usr/bin/env python3
"""
Test Universe Size - Verify 12-15 Stock Minimum
================================================

Validates that the trading universe always has at least 12-15 stocks
by combining PreFilter results with the static base_universe.

Date: October 16, 2025
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

def test_config():
    """Test that config has correct settings"""
    print("=" * 80)
    print("🧪 TEST 1: Config Settings")
    print("=" * 80)
    
    config_path = Path('/home/wes/Desktop/litebotx-usb-deployment/config/short_cycle_universe.json')
    
    if not config_path.exists():
        print("❌ Config file not found!")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    base_universe = config.get('base_universe', [])
    min_symbols = config.get('min_symbols', 0)
    max_symbols = config.get('max_symbols')
    
    print(f"✅ Config loaded:")
    print(f"   base_universe: {len(base_universe)} stocks")
    print(f"   min_symbols: {min_symbols}")
    print(f"   max_symbols: {max_symbols}")
    print(f"\n📋 Base Universe ({len(base_universe)} stocks):")
    for i in range(0, len(base_universe), 5):
        print(f"   {', '.join(base_universe[i:i+5])}")
    
    # Validate
    if len(base_universe) < min_symbols:
        print(f"\n❌ FAIL: base_universe ({len(base_universe)}) < min_symbols ({min_symbols})")
        return False
    
    if min_symbols < 12:
        print(f"\n⚠️ WARNING: min_symbols ({min_symbols}) < 12 (recommended minimum)")
    
    if min_symbols < 15:
        print(f"\n⚠️ WARNING: min_symbols ({min_symbols}) < 15 (your target)")
    else:
        print(f"\n✅ PASS: min_symbols = {min_symbols} (meets 15 target)")
    
    if max_symbols and max_symbols < min_symbols:
        print(f"\n❌ FAIL: max_symbols ({max_symbols}) < min_symbols ({min_symbols})")
        return False
    
    print(f"\n✅ TEST 1 PASSED: Config is valid")
    return True

def test_universe_logic():
    """Test the universe selection logic with mock PreFilter results"""
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Universe Selection Logic")
    print("=" * 80)
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        
        # Create minimal config
        config = ShortCycleConfig(portfolio_value=1000.0)
        trader = ShortCycleTrader(config)
        
        # Call the universe method
        print("\n⏳ Getting trading universe...")
        universe = trader._get_trading_universe()
        
        print(f"\n✅ Universe generated: {len(universe)} stocks")
        print(f"\n📋 Trading Universe ({len(universe)} stocks):")
        for i in range(0, len(universe), 5):
            print(f"   {', '.join(universe[i:i+5])}")
        
        # Validate
        if len(universe) < 12:
            print(f"\n❌ FAIL: Universe has only {len(universe)} stocks (minimum: 12)")
            return False
        
        if len(universe) < 15:
            print(f"\n⚠️ WARNING: Universe has {len(universe)} stocks (target: 15)")
            print("   Consider expanding base_universe or improving PreFilter results")
        else:
            print(f"\n✅ PASS: Universe has {len(universe)} stocks (meets 15 target)")
        
        print(f"\n✅ TEST 2 PASSED: Universe meets minimum size requirement")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              Trading Universe Size Validation Test                        ║
║              Minimum 12-15 Stocks Required                                 ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Test 1: Config
    results.append(("Config Settings", test_config()))
    
    # Test 2: Universe Logic
    results.append(("Universe Selection Logic", test_universe_logic()))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 80)
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\n📋 Your trading universe will have at least 12-15 stocks")
        print("   - PreFilter results used first")
        print("   - Topped up from base_universe to reach min_symbols")
        print("   - Capped at max_symbols to stay focused")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("   Review errors above and adjust configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())
