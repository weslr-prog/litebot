#!/usr/bin/env python3
"""
Quick AttributeError Test
=========================
Test if our fixes actually prevent AttributeErrors
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_trader_methods():
    """Test the specific methods that were causing AttributeErrors"""
    print("🔍 Testing ShortCycleTrader methods...")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader
        
        trader = ShortCycleTrader()
        
        # Test the methods that were causing issues
        print("   Testing _has_same_day_activity...")
        result = trader._has_same_day_activity("AAPL")
        print(f"   ✅ _has_same_day_activity returned: {result}")
        
        print("   Testing _generate_portfolio_summary...")
        trader._generate_portfolio_summary()
        print("   ✅ _generate_portfolio_summary completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Trader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_trader_methods()