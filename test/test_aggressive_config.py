#!/usr/bin/env python3
"""Test Aggressive Configuration"""
import sys
import importlib.util

def test_aggressive_config():
    print("🧪 Testing Aggressive Configuration")
    print("="*60)
    
    # Load trader config
    spec = importlib.util.spec_from_file_location(
        "short_cycle_trader",
        "traders/short_cycle_trader.py"
    )
    trader_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trader_module)
    
    config = trader_module.ShortCycleConfig()
    
    tests = {
        "Max Position": (config.max_position_dollars, 6000.0, "="),
        "Max Loss": (config.max_loss_per_trade_dollars, 400.0, "="),
        "Confidence": (config.confidence_threshold, 0.07, "="),
        "Daily Pool %": (config.daily_pool_percent, 0.60, "="),
        "Max Positions/Day": (config.max_positions_per_day, 8, "="),
        "Position Size %": (config.max_position_size_percent, 0.12, "="),
        "Daily Loss %": (config.max_daily_loss_percent, 0.002, "="),
        "Weekly Loss %": (config.max_weekly_loss_percent, 0.006, "="),
    }
    
    passed = 0
    failed = 0
    
    for name, (actual, expected, op) in tests.items():
        if op == "=" and actual == expected:
            print(f"  ✅ {name}: {actual}")
            passed += 1
        else:
            print(f"  ❌ {name}: {actual} (expected {expected})")
            failed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Aggressive config ready!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_aggressive_config())
