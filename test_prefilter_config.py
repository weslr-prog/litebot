#!/usr/bin/env python3
"""
Test PreFilter Price Range Configuration
Verifies that PreFilter uses $10-30 range for small portfolio trading
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_prefilter_price_range():
    """Test that PreFilter is configured for $10-30 mid-cap stocks"""
    
    print("=" * 70)
    print("PREFILTER PRICE RANGE TEST")
    print("=" * 70)
    
    from pre_filter import PreFilter
    
    # Initialize PreFilter
    prefilter = PreFilter(simulation_mode=True, fast_mode=True)
    
    print("\n📊 PreFilter Configuration:")
    print(f"  MIN_PRICE: ${prefilter.MIN_PRICE}")
    print(f"  MAX_PRICE: ${prefilter.MAX_PRICE}")
    print(f"  MIN_ATR: {prefilter.MIN_ATR:.1%}")
    print(f"  MAX_ATR: {prefilter.MAX_ATR:.1%}")
    print(f"  MIN_AVG_VOL: {prefilter.MIN_AVG_VOL:,}")
    print(f"  MIN_AVG_DOLLAR_VOL: ${prefilter.MIN_AVG_DOLLAR_VOL:,}")
    
    # Test 1: Price range
    print("\n" + "=" * 70)
    print("TEST 1: Price Range Configuration")
    print("=" * 70)
    
    errors = []
    
    if prefilter.MIN_PRICE != 10.0:
        errors.append(f"MIN_PRICE is ${prefilter.MIN_PRICE}, expected $10.0")
    
    if prefilter.MAX_PRICE != 30.0:
        errors.append(f"MAX_PRICE is ${prefilter.MAX_PRICE}, expected $30.0")
    
    if errors:
        for error in errors:
            print(f"❌ FAIL: {error}")
        return False
    
    print("✅ PASS: Price range $10-30 configured correctly")
    
    # Test 2: Volatility requirements
    print("\n" + "=" * 70)
    print("TEST 2: Volatility Requirements")
    print("=" * 70)
    
    if prefilter.MIN_ATR != 0.03:
        print(f"❌ FAIL: MIN_ATR is {prefilter.MIN_ATR:.1%}, expected 3.0%")
        return False
    
    if prefilter.MAX_ATR != 0.12:
        print(f"❌ FAIL: MAX_ATR is {prefilter.MAX_ATR:.1%}, expected 12%")
        return False
    
    print("✅ PASS: Volatility range 3-12% configured correctly")
    
    # Test 3: Volume requirements
    print("\n" + "=" * 70)
    print("TEST 3: Volume Requirements")
    print("=" * 70)
    
    if prefilter.MIN_AVG_VOL != 100_000:
        print(f"❌ FAIL: MIN_AVG_VOL is {prefilter.MIN_AVG_VOL:,}, expected 100,000")
        return False
    
    if prefilter.MIN_AVG_DOLLAR_VOL != 1_000_000:
        print(f"❌ FAIL: MIN_AVG_DOLLAR_VOL is ${prefilter.MIN_AVG_DOLLAR_VOL:,}, expected $1,000,000")
        return False
    
    print("✅ PASS: Volume requirements configured for mid-caps")
    
    # Test 4: Stock classification
    print("\n" + "=" * 70)
    print("TEST 4: Stock Classification")
    print("=" * 70)
    
    test_stocks = [
        ("PLTR", 18.50, True, "Mid-cap in range"),
        ("RIVN", 15.00, True, "Mid-cap in range"),
        ("SOFI", 8.00, False, "Below $10 minimum"),
        ("AMD", 238.00, False, "Above $30 maximum"),
        ("SHOP", 176.00, False, "Above $30 maximum"),
        ("XOM", 117.00, False, "Above $30 maximum"),
        ("UPS", 96.00, False, "Above $30 maximum"),
        ("SNAP", 12.00, True, "Mid-cap in range"),
        ("PLUG", 4.50, False, "Below $10 minimum"),
        ("AAPL", 263.00, False, "Above $30 maximum"),
    ]
    
    for symbol, price, should_pass, reason in test_stocks:
        passes = prefilter.MIN_PRICE <= price <= prefilter.MAX_PRICE
        
        if passes == should_pass:
            status = "✅" if should_pass else "❌"
            print(f"{status} {symbol:6s} @ ${price:7.2f}: {reason}")
        else:
            print(f"🚨 FAIL: {symbol} @ ${price:.2f} - Expected {should_pass}, got {passes}")
            return False
    
    return True


if __name__ == "__main__":
    print("\n")
    print("🔬 Testing PreFilter Configuration for Small Portfolio")
    print("=" * 70)
    print("Issue: PreFilter was using $20-500 range instead of $10-30")
    print("Fix: Updated hardcoded values in pre_filter.py to match small portfolio config")
    print("=" * 70)
    
    try:
        success = test_prefilter_price_range()
        
        print("\n" + "=" * 70)
        print("FINAL RESULT")
        print("=" * 70)
        
        if success:
            print("\n🎉 ALL TESTS PASSED - PreFilter Configured for Mid-Cap Stocks!")
            print("\nWhat changed:")
            print("  1. MIN_PRICE: $15 → $10")
            print("  2. MAX_PRICE: $1000 → $30 (CRITICAL)")
            print("  3. MIN_ATR: 1.0% → 3.0% (more volatile stocks)")
            print("  4. MIN_AVG_DOLLAR_VOL: $5M → $1M (mid-cap liquidity)")
            print("\nExpected stocks:")
            print("  ✅ PLTR, RIVN, SNAP, SOFI (in $10-30 range)")
            print("  ❌ AMD, SHOP, XOM, UPS, AAPL (over $30)")
            print("\nNext step:")
            print("  - Restart bot to see new stock universe")
            print("  - Should see PLTR, RIVN, SNAP instead of AMD, SHOP, XOM")
            sys.exit(0)
        else:
            print("\n❌ TESTS FAILED - PreFilter Configuration Incorrect!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
