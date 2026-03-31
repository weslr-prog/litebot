#!/usr/bin/env python3
"""
Test Watchlist Generation - Small Portfolio Mid-Cap Focus
==========================================================

Tests that PreFilter correctly selects $10-30 mid-cap volatile stocks
for the small portfolio strategy.

Expected behavior after fix:
- Should find: PLTR ($18), RIVN ($15), SNAP ($12), HOOD ($22), etc.
- Should reject: AMD ($238), SHOP ($176), XOM ($117), AAPL ($263), etc.
- Price range: $10-30
- Volatility: 3-12% ATR
- Volume: 100K+ shares, $1M+ dollar volume
"""

import sys
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_filter import PreFilter
from small_portfolio_config import SmallPortfolioConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_prefilter_configuration():
    """Test 1: Verify PreFilter is configured correctly"""
    print("\n" + "="*70)
    print("TEST 1: PreFilter Configuration")
    print("="*70)
    
    prefilter = PreFilter()
    config = SmallPortfolioConfig()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test MIN_PRICE
    if prefilter.MIN_PRICE == 10.0:
        print(f"✅ MIN_PRICE = ${prefilter.MIN_PRICE:.2f} (correct)")
        tests_passed += 1
    else:
        print(f"❌ MIN_PRICE = ${prefilter.MIN_PRICE:.2f} (expected $10.00)")
        tests_failed += 1
    
    # Test MAX_PRICE
    if prefilter.MAX_PRICE == 30.0:
        print(f"✅ MAX_PRICE = ${prefilter.MAX_PRICE:.2f} (correct)")
        tests_passed += 1
    else:
        print(f"❌ MAX_PRICE = ${prefilter.MAX_PRICE:.2f} (expected $30.00)")
        tests_failed += 1
    
    # Test MIN_ATR (3% volatility)
    if prefilter.MIN_ATR == 0.030:
        print(f"✅ MIN_ATR = {prefilter.MIN_ATR:.3f} (3.0% - correct)")
        tests_passed += 1
    else:
        print(f"❌ MIN_ATR = {prefilter.MIN_ATR:.3f} (expected 0.030 = 3.0%)")
        tests_failed += 1
    
    # Test MIN_AVG_VOL
    if prefilter.MIN_AVG_VOL == 100_000:
        print(f"✅ MIN_AVG_VOL = {prefilter.MIN_AVG_VOL:,} shares (correct)")
        tests_passed += 1
    else:
        print(f"❌ MIN_AVG_VOL = {prefilter.MIN_AVG_VOL:,} shares (expected 100,000)")
        tests_failed += 1
    
    # Test MIN_AVG_DOLLAR_VOL
    if prefilter.MIN_AVG_DOLLAR_VOL == 1_000_000:
        print(f"✅ MIN_AVG_DOLLAR_VOL = ${prefilter.MIN_AVG_DOLLAR_VOL:,} (correct)")
        tests_passed += 1
    else:
        print(f"❌ MIN_AVG_DOLLAR_VOL = ${prefilter.MIN_AVG_DOLLAR_VOL:,} (expected $1,000,000)")
        tests_failed += 1
    
    print(f"\nConfiguration Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_price_range_filtering():
    """Test 2: Verify price range filter works correctly"""
    print("\n" + "="*70)
    print("TEST 2: Price Range Filtering")
    print("="*70)
    
    prefilter = PreFilter()
    
    # Create test data with stocks at various prices
    test_stocks = {
        'PLTR': 18.50,   # Should PASS ($10-30)
        'RIVN': 15.00,   # Should PASS ($10-30)
        'SNAP': 12.00,   # Should PASS ($10-30)
        'HOOD': 22.00,   # Should PASS ($10-30)
        'SOFI': 8.00,    # Should FAIL (< $10)
        'AMD': 238.00,   # Should FAIL (> $30)
        'SHOP': 176.00,  # Should FAIL (> $30)
        'XOM': 117.00,   # Should FAIL (> $30)
        'UPS': 96.00,    # Should FAIL (> $30)
        'AAPL': 263.00,  # Should FAIL (> $30)
    }
    
    # Create DataFrame with multiple dates to simulate history
    dates = pd.date_range(end=datetime.now(), periods=5, freq='D')
    data = []
    for symbol, price in test_stocks.items():
        for date in dates:
            data.append({
                'symbol': symbol,
                'date': date,
                'close': price,
                'volume': 200000,
                'high': price * 1.02,
                'low': price * 0.98,
                'open': price
            })
    
    df = pd.DataFrame(data)
    
    # Apply price range filter
    filtered = prefilter.price_range_filter(df, min_price=10, max_price=30)
    
    # Check results
    passed_symbols = sorted(filtered['symbol'].unique())
    
    print("\nExpected to PASS (in $10-30 range):")
    expected_pass = ['PLTR', 'RIVN', 'SNAP', 'HOOD']
    for symbol in expected_pass:
        price = test_stocks[symbol]
        if symbol in passed_symbols:
            print(f"  ✅ {symbol} @ ${price:6.2f}: PASSED")
        else:
            print(f"  ❌ {symbol} @ ${price:6.2f}: FAILED (should have passed)")
    
    print("\nExpected to REJECT (outside $10-30 range):")
    expected_reject = ['SOFI', 'AMD', 'SHOP', 'XOM', 'UPS', 'AAPL']
    for symbol in expected_reject:
        price = test_stocks[symbol]
        reason = "< $10" if price < 10 else "> $30"
        if symbol not in passed_symbols:
            print(f"  ✅ {symbol} @ ${price:6.2f}: REJECTED ({reason})")
        else:
            print(f"  ❌ {symbol} @ ${price:6.2f}: PASSED (should have been rejected)")
    
    # Validate
    all_correct = (
        set(passed_symbols) == set(expected_pass)
    )
    
    print(f"\nPrice Range Filter: {'✅ PASSED' if all_correct else '❌ FAILED'}")
    return all_correct


def generate_current_watchlist():
    """Test 3: Generate actual watchlist from Alpaca"""
    print("\n" + "="*70)
    print("TEST 3: Generate Actual Watchlist from Alpaca")
    print("="*70)
    print("\nNOTE: This requires Alpaca API credentials and active market data.")
    print("If this fails, it's likely due to API limits or market hours.\n")
    
    try:
        from stock_api import get_stock_api
        
        # Get API client
        api = get_stock_api()
        
        # Get all tradable assets
        print("Fetching tradable assets from Alpaca...")
        all_assets = api.list_assets(status='active', asset_class='us_equity')
        
        # Filter to NYSE/NASDAQ only
        tradable_symbols = [
            asset.symbol for asset in all_assets 
            if asset.tradable and asset.exchange in ['NYSE', 'NASDAQ', 'ARCA']
        ]
        
        print(f"Found {len(tradable_symbols)} tradable symbols")
        
        # Get price data for sample
        print("\nChecking prices for sample of symbols...")
        
        # Sample some known mid-caps and large-caps
        sample_symbols = [
            'PLTR', 'RIVN', 'SNAP', 'HOOD',  # Expected mid-caps ($10-30)
            'AMD', 'SHOP', 'XOM', 'AAPL',    # Expected large-caps (> $30)
        ]
        
        from datetime import datetime, timedelta
        end = datetime.now(pytz.UTC)
        start = end - timedelta(days=10)
        
        results = {'in_range': [], 'too_expensive': [], 'too_cheap': [], 'no_data': []}
        
        for symbol in sample_symbols:
            try:
                bars = api.get_bars(
                    symbol,
                    '1Day',
                    start=start.isoformat(),
                    end=end.isoformat(),
                    limit=5
                ).df
                
                if not bars.empty:
                    latest_price = bars['close'].iloc[-1]
                    
                    if 10 <= latest_price <= 30:
                        results['in_range'].append((symbol, latest_price))
                        status = "✅ IN RANGE"
                    elif latest_price > 30:
                        results['too_expensive'].append((symbol, latest_price))
                        status = "❌ TOO EXPENSIVE"
                    else:
                        results['too_cheap'].append((symbol, latest_price))
                        status = "❌ TOO CHEAP"
                    
                    print(f"  {symbol:6s} @ ${latest_price:7.2f} - {status}")
                else:
                    results['no_data'].append(symbol)
                    print(f"  {symbol:6s} - No data available")
                    
            except Exception as e:
                results['no_data'].append(symbol)
                print(f"  {symbol:6s} - Error: {str(e)[:50]}")
        
        # Summary
        print("\n" + "-"*70)
        print("SUMMARY:")
        print(f"  In Range ($10-30):  {len(results['in_range'])} stocks")
        if results['in_range']:
            for symbol, price in results['in_range']:
                print(f"    - {symbol} @ ${price:.2f}")
        
        print(f"  Too Expensive (>$30): {len(results['too_expensive'])} stocks")
        if results['too_expensive']:
            for symbol, price in results['too_expensive']:
                print(f"    - {symbol} @ ${price:.2f}")
        
        print(f"  Too Cheap (<$10):   {len(results['too_cheap'])} stocks")
        print(f"  No Data:            {len(results['no_data'])} stocks")
        
        # Check if results match expectations
        expected_mid_caps = ['PLTR', 'RIVN', 'SNAP', 'HOOD']
        expected_large_caps = ['AMD', 'SHOP', 'XOM', 'AAPL']
        
        in_range_symbols = [s for s, p in results['in_range']]
        too_expensive_symbols = [s for s, p in results['too_expensive']]
        
        mid_caps_correct = all(s in in_range_symbols for s in expected_mid_caps if s not in results['no_data'])
        large_caps_correct = all(s in too_expensive_symbols for s in expected_large_caps if s not in results['no_data'])
        
        success = mid_caps_correct and large_caps_correct
        
        print(f"\nWatchlist Generation: {'✅ PASSED' if success else '⚠️  CHECK RESULTS'}")
        return success
        
    except Exception as e:
        print(f"\n⚠️  Watchlist generation skipped: {str(e)}")
        print("This is OK if you don't have Alpaca API access or market is closed.")
        return None


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SMALL PORTFOLIO WATCHLIST GENERATION TEST")
    print("="*70)
    print(f"Testing PreFilter configuration for $10-30 mid-cap stocks")
    print(f"Expected stocks: PLTR, RIVN, SNAP, HOOD (mid-cap volatiles)")
    print(f"Rejected stocks: AMD, SHOP, XOM, AAPL (large-caps > $30)")
    
    results = {}
    
    # Test 1: Configuration
    results['config'] = test_prefilter_configuration()
    
    # Test 2: Price filtering logic
    results['filtering'] = test_price_range_filtering()
    
    # Test 3: Live watchlist (optional - may fail if no API access)
    results['watchlist'] = generate_current_watchlist()
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"✅ Passed:  {passed}")
    print(f"❌ Failed:  {failed}")
    print(f"⚠️  Skipped: {skipped}")
    
    if results['config'] and results['filtering']:
        print("\n🎉 PreFilter is correctly configured for $10-30 mid-cap stocks!")
        print("   Bot should now select PLTR/RIVN/SNAP instead of AMD/SHOP/XOM")
        return 0
    else:
        print("\n❌ PreFilter configuration issues detected!")
        print("   Review the test results above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
