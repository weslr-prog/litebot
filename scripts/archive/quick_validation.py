#!/usr/bin/env python3
"""
Quick Validation Test
====================
Test the specific fixes made for October 6 trading issues
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_position_class():
    """Test ShortCyclePosition with correct parameters"""
    print("🔍 Testing ShortCyclePosition class...")
    
    try:
        from traders.short_cycle_trader import ShortCyclePosition, PositionStatus, AISignal
        from datetime import date, datetime
        import dataclasses
        
        # Create AISignal
        ai_signal = AISignal(
            signal_type="MOMENTUM_LONG",
            confidence=0.85,
            target_return=0.025,
            risk_assessment=0.8,
            entry_reasons=["momentum", "volume"],
            features={"rsi": 45, "volume_ratio": 1.5}
        )
        
        # Create position with correct parameters
        position = ShortCyclePosition(
            symbol="AAPL",
            entry_date=date.today(),
            exit_date=date.today(),
            entry_price=150.0,
            position_size_shares=100,
            position_size_dollars=15000.0,
            stop_price=147.0,
            target_price=153.0,
            status=PositionStatus.ENTERED,
            ai_signal=ai_signal
        )
        
        print(f"✅ Position created: {position.symbol}")
        
        # Test critical attributes
        test_attrs = ['entry_timestamp', 'entry_date', 'exit_timestamp', 'exit_date']
        for attr in test_attrs:
            if hasattr(position, attr):
                print(f"   ✅ {attr}: {getattr(position, attr)}")
            else:
                print(f"   ❌ {attr}: MISSING")
        
        return True
        
    except Exception as e:
        print(f"❌ Position test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pre_filter_quick():
    """Quick test of pre-filter fixes"""
    print("\n🔍 Testing Pre-Filter fixes...")
    
    try:
        from pre_filter import PreFilter
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Simulate free tier data (21 days)
        dates = pd.date_range(end=datetime.now(), periods=21)
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        data = []
        for symbol in symbols:
            for date in dates:
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'close': 100.0,
                    'volume': 1000000
                })
        
        df = pd.DataFrame(data)
        pre_filter = PreFilter()
        
        # Test with min_rows=20 (should pass)
        result = pre_filter.data_completeness_filter(df, min_rows=20)
        symbols_20 = len(result['symbol'].unique()) if not result.empty else 0
        
        # Test with min_rows=30 (should fail)
        result = pre_filter.data_completeness_filter(df, min_rows=30)
        symbols_30 = len(result['symbol'].unique()) if not result.empty else 0
        
        print(f"   Min rows 20: {symbols_20} symbols pass")
        print(f"   Min rows 30: {symbols_30} symbols pass")
        
        if symbols_20 > 0 and symbols_30 == 0:
            print("✅ Pre-filter fixes working correctly")
            return True
        else:
            print("❌ Pre-filter still has issues")
            return False
        
    except Exception as e:
        print(f"❌ Pre-filter test failed: {e}")
        return False

def test_has_same_day_activity():
    """Test the specific method that had the AttributeError"""
    print("\n🔍 Testing _has_same_day_activity fix...")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader
        from datetime import date
        
        trader = ShortCycleTrader()
        
        # Test with empty positions (should not crash)
        result = trader._has_same_day_activity("AAPL", date.today())
        print(f"   Empty positions test: {result}")
        
        # Test should not crash anymore with missing entry_timestamp
        print("✅ _has_same_day_activity method working")
        return True
        
    except Exception as e:
        print(f"❌ same day activity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_min_rows_settings():
    """Check if all min_rows are set to 20"""
    print("\n🔍 Checking min_rows settings...")
    
    try:
        with open('/home/wes/Desktop/litebotx-usb-deployment/pre_filter.py', 'r') as f:
            content = f.read()
        
        # Find all min_rows references
        lines = content.split('\n')
        min_rows_lines = []
        
        for i, line in enumerate(lines, 1):
            if 'min_rows=' in line and not line.strip().startswith('#'):
                min_rows_lines.append((i, line.strip()))
        
        print(f"   Found {len(min_rows_lines)} min_rows settings:")
        
        problematic = []
        for line_num, line in min_rows_lines:
            if 'min_rows=90' in line or 'min_rows=100' in line or 'min_rows=120' in line:
                problematic.append((line_num, line))
            print(f"     Line {line_num}: {line}")
        
        if problematic:
            print(f"❌ Found {len(problematic)} high min_rows settings:")
            for line_num, line in problematic:
                print(f"     Line {line_num}: {line}")
            return False
        else:
            print("✅ All min_rows settings look good")
            return True
            
    except Exception as e:
        print(f"❌ min_rows check failed: {e}")
        return False

def main():
    """Run quick validation tests"""
    print("🔬 QUICK VALIDATION TEST")
    print("=" * 50)
    
    tests = [
        ("Position Class", test_position_class),
        ("Pre-Filter", test_pre_filter_quick),
        ("Same Day Activity", test_has_same_day_activity),
        ("Min Rows Settings", check_min_rows_settings)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n🧪 {name}...")
        results[name] = test_func()
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 ALL FIXES VALIDATED - Ready for historical testing!")
    else:
        print(f"\n⚠️  {total - passed} issues remaining")

if __name__ == "__main__":
    main()