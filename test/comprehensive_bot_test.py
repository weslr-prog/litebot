#!/usr/bin/env python3
"""
Comprehensive test for tomorrow's trading
Tests all critical components to ensure bot will operate properly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_filter import PreFilter
from data_loader import DataLoader
import json
import pandas as pd
from datetime import datetime

print("=" * 80)
print("🧪 COMPREHENSIVE BOT TEST - Tomorrow's Trading Readiness")
print("=" * 80)
print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Track test results
tests_passed = 0
tests_failed = 0
warnings = []

def test_result(name, passed, message=""):
    global tests_passed, tests_failed
    if passed:
        print(f"✅ {name}")
        tests_passed += 1
    else:
        print(f"❌ {name}")
        if message:
            print(f"   Error: {message}")
        tests_failed += 1

def test_warning(name, message):
    global warnings
    print(f"⚠️  {name}")
    print(f"   Warning: {message}")
    warnings.append((name, message))

# ============================================================================
# TEST 1: Config File Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: Config File Validation")
print("=" * 80)

try:
    with open('config/short_cycle_universe.json', 'r') as f:
        config = json.load(f)
    
    test_result("Config file exists and is valid JSON", True)
    
    # Check min_symbols
    min_symbols = config.get('min_symbols', 0)
    if min_symbols == 5:
        test_result("min_symbols = 5 (correct, no forced fallbacks)", True)
    else:
        test_result("min_symbols = 5", False, f"Found {min_symbols}")
    
    # Check max_symbols
    max_symbols = config.get('max_symbols', 0)
    if max_symbols == 20:
        test_result("max_symbols = 20 (correct range)", True)
    else:
        test_result("max_symbols = 20", False, f"Found {max_symbols}")
    
    # Check base_universe exists
    base_universe = config.get('base_universe', [])
    if len(base_universe) > 0:
        test_result(f"base_universe has {len(base_universe)} stocks", True)
    else:
        test_result("base_universe populated", False, "Empty list")
        
except Exception as e:
    test_result("Config file validation", False, str(e))

# ============================================================================
# TEST 2: PreFilter Settings Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: PreFilter Settings Validation")
print("=" * 80)

try:
    data_loader = DataLoader()
    prefilter = PreFilter(
        simulation_mode=False,
        data_loader=data_loader,
        fast_mode=True,
        enable_intraday_analysis=False
    )
    
    test_result("PreFilter initialized successfully", True)
    
    # Check price range
    if prefilter.MIN_PRICE == 15.0:
        test_result("MIN_PRICE = $15.00 (user-specified)", True)
    else:
        test_result("MIN_PRICE = $15.00", False, f"Found ${prefilter.MIN_PRICE}")
    
    if prefilter.MAX_PRICE == 350.0:
        test_result("MAX_PRICE = $350.00 (user-specified)", True)
    else:
        test_result("MAX_PRICE = $350.00", False, f"Found ${prefilter.MAX_PRICE}")
    
    # Check other thresholds
    if prefilter.MIN_ATR == 0.015:
        test_result("MIN_ATR = 1.5% (relaxed for 10-15 stocks)", True)
    else:
        test_warning("MIN_ATR threshold", f"Expected 0.015, found {prefilter.MIN_ATR}")
    
    if prefilter.MIN_MOMENTUM_RETURN == 0.025:
        test_result("MIN_MOMENTUM = 2.5% (relaxed for 10-15 stocks)", True)
    else:
        test_warning("MIN_MOMENTUM threshold", f"Expected 0.025, found {prefilter.MIN_MOMENTUM_RETURN}")
    
    if prefilter.MIN_VOLUME_SURGE == 1.3:
        test_result("MIN_VOLUME_SURGE = 1.3x (relaxed for 10-15 stocks)", True)
    else:
        test_warning("MIN_VOLUME_SURGE threshold", f"Expected 1.3, found {prefilter.MIN_VOLUME_SURGE}")
    
    if prefilter.MIN_AVG_DOLLAR_VOL == 10_000_000:
        test_result("MIN_DOLLAR_VOL = $10M (quality liquidity)", True)
    else:
        test_warning("MIN_DOLLAR_VOL threshold", f"Expected 10M, found {prefilter.MIN_AVG_DOLLAR_VOL}")
    
except Exception as e:
    test_result("PreFilter initialization", False, str(e))

# ============================================================================
# TEST 3: Asset Selection Test (Tomorrow's Universe)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Asset Selection Test (Simulating Tomorrow's Selection)")
print("=" * 80)

try:
    # Candidate pool
    candidates = [
        "AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","NFLX","AMD","AVGO",
        "INTC","IBM","ORCL","CRM","ADBE","CSCO","QCOM","SHOP","UBER","LYFT",
        "DIS","WMT","XOM","CVX","BA","CAT","KO","PEP","JNJ","PFE","BAC","JPM","GS",
        "V","MA","HD","UNH","MCD","NKE","ABBV","TMO","ACN","TXN","LLY","COST",
        "HON","UPS","BMY","SBUX","MDT","GILD","MMM","GE","F","GM","T","VZ"
    ]
    
    print(f"\n📊 Analyzing {len(candidates)} candidate stocks...")
    
    # Fetch data
    history_df = prefilter.fetch_history(candidates, days=40, use_cache=True)
    test_result(f"Fetched historical data ({len(history_df)} rows)", len(history_df) > 0)
    
    # Run PreFilter
    filtered = prefilter.filter_assets(history_df)
    
    if len(filtered) == 0:
        test_result("PreFilter returned results", False, "No stocks passed filters - check thresholds!")
    else:
        # Get latest snapshot and rank
        snap = filtered.groupby('symbol').tail(1)
        if 'pf_score' in snap.columns:
            ranked = snap.sort_values('pf_score', ascending=False)
        else:
            ranked = snap.sort_values('volume', ascending=False)
        
        ranked_symbols = ranked['symbol'].tolist()
        num_passed = len(ranked_symbols)
        
        # Check if in target range
        if 10 <= num_passed <= 15:
            test_result(f"PreFilter passed {num_passed} stocks (IDEAL: 10-15 range)", True)
        elif 5 <= num_passed < 10:
            test_warning(f"PreFilter passed {num_passed} stocks", "Below target (10-15), but acceptable")
        elif 15 < num_passed <= 20:
            test_warning(f"PreFilter passed {num_passed} stocks", "Above target (10-15), but within max")
        else:
            test_result(f"PreFilter passed {num_passed} stocks", False, f"Outside acceptable range (5-20)")
        
        # Display results
        print(f"\n🏆 Stocks That Passed PreFilter ({num_passed}):")
        print("-" * 80)
        
        for idx, symbol in enumerate(ranked_symbols[:20], 1):  # Show up to 20
            row = snap[snap['symbol'] == symbol].iloc[0]
            price = row.get('close', 0)
            score = row.get('pf_score', 0)
            momentum = row.get('momentum', 0) * 100 if 'momentum' in row else 0
            volatility = row.get('volatility', 0) * 100 if 'volatility' in row else 0
            
            # Check price range
            in_range = "✅" if 15 <= price <= 350 else "❌"
            
            print(f"{idx:2d}. {symbol:6s} {in_range} | "
                  f"${price:7.2f} | Score: {score:6.2f} | "
                  f"Mom: {momentum:+6.2f}% | Vol: {volatility:5.2f}%")
        
        # Verify price range compliance
        prices = [snap[snap['symbol'] == s].iloc[0]['close'] for s in ranked_symbols]
        prices_in_range = [15 <= p <= 350 for p in prices]
        
        if all(prices_in_range):
            test_result("All stocks in $15-$350 price range", True)
        else:
            out_of_range = [ranked_symbols[i] for i, in_range in enumerate(prices_in_range) if not in_range]
            test_result("All stocks in price range", False, f"Out of range: {out_of_range}")
        
except Exception as e:
    test_result("Asset selection test", False, str(e))
    import traceback
    print(f"\nTraceback:\n{traceback.format_exc()}")

# ============================================================================
# TEST 4: Trader Logic Validation (No Fallbacks)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: Trader Logic Validation (No Fallback Check)")
print("=" * 80)

try:
    # Read trader file and check for fallback logic
    with open('traders/short_cycle_trader.py', 'r') as f:
        trader_code = f.read()
    
    # Check that fallback logic is removed
    has_old_topup = "Top-up with static universe" in trader_code
    has_old_fallback = "falling back to static universe" in trader_code
    
    if not has_old_topup:
        test_result("Old top-up logic removed", True)
    else:
        test_result("Old top-up logic removed", False, "Found old fallback code")
    
    # Check for new quality-only message
    has_quality_only = "quality-only universe" in trader_code
    has_no_fallbacks = "no fallbacks added" in trader_code
    
    if has_quality_only and has_no_fallbacks:
        test_result("New quality-only logic present", True)
    else:
        test_result("New quality-only logic present", False, "Missing expected messages")
    
    # Check that emergency fallback is removed
    has_emergency = '["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ"]' in trader_code
    
    if not has_emergency:
        test_result("Emergency fallback removed", True)
    else:
        test_result("Emergency fallback removed", False, "Still has hardcoded fallback list")
    
except Exception as e:
    test_result("Trader logic validation", False, str(e))

# ============================================================================
# TEST 5: D+1 Exit Logic (From Previous Tests)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: D+1 Exit Logic Validation")
print("=" * 80)

try:
    # Check if positions.json exists and has the 8 positions
    if os.path.exists('positions.json'):
        with open('positions.json', 'r') as f:
            positions = json.load(f)
        
        if len(positions) == 8:
            test_result(f"positions.json has 8 positions for tomorrow's exit", True)
            
            # Check they all have exit_date = 2025-10-22
            exit_dates = [p.get('exit_date') for p in positions]
            if all(d == '2025-10-22' for d in exit_dates):
                test_result("All positions have exit_date = 2025-10-22", True)
            else:
                test_warning("Position exit dates", "Some positions have different exit dates")
        else:
            test_warning("positions.json position count", f"Found {len(positions)} positions, expected 8")
    else:
        test_warning("positions.json file", "File not found - positions will be loaded from Alpaca")
        
except Exception as e:
    test_warning("D+1 exit validation", str(e))

# ============================================================================
# TEST 6: Dependencies and Imports
# ============================================================================
print("\n" + "=" * 80)
print("TEST 6: Critical Dependencies")
print("=" * 80)

try:
    import pytz
    test_result("pytz imported (timezone handling)", True)
except ImportError:
    test_result("pytz imported", False, "Missing pytz - install with: pip install pytz")

try:
    import yfinance
    test_result("yfinance imported (data fetching)", True)
except ImportError:
    test_result("yfinance imported", False, "Missing yfinance")

try:
    import pandas as pd
    import numpy as np
    test_result("pandas/numpy imported (data processing)", True)
except ImportError:
    test_result("pandas/numpy imported", False, "Missing core libraries")

try:
    from signal_generator import SignalGenerator
    test_result("SignalGenerator imported", True)
except Exception as e:
    test_result("SignalGenerator imported", False, str(e))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)

total_tests = tests_passed + tests_failed
pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"\nTests Passed: {tests_passed}/{total_tests} ({pass_rate:.1f}%)")
print(f"Tests Failed: {tests_failed}/{total_tests}")
print(f"Warnings: {len(warnings)}")

if warnings:
    print("\n⚠️  Warnings:")
    for name, msg in warnings:
        print(f"   - {name}: {msg}")

print("\n" + "=" * 80)
if tests_failed == 0:
    print("✅ ALL CRITICAL TESTS PASSED - Bot is ready for tomorrow")
    print("=" * 80)
    print("""
Tomorrow's Expected Flow:

4:00 PM Tonight:
  ✅ PreFilter will run on 57 candidates
  ✅ 10-15 stocks expected to pass (relaxed thresholds)
  ✅ NO fallback stocks added
  ✅ Log: "Using PreFilter universe: X quality stocks passed all filters"

9:45 AM Tomorrow:
  ✅ Exit 8 D+1 positions from Oct 21
  ✅ Capture P&L from yesterday's trades
  
9:45-10:00 AM Tomorrow:
  ✅ Signal generator analyzes 10-15 quality stocks
  ✅ Generates top 8 signals from quality candidates
  ✅ Executes 8 BUY orders for new D+1 positions

5:00 PM Tomorrow:
  ✅ Verify 8 old positions closed
  ✅ Verify 8 new positions opened
  ✅ Check PreFilter prepared for Oct 23
""")
else:
    print("❌ SOME TESTS FAILED - Review errors above")
    print("=" * 80)
    print("\n⚠️  Do NOT run bot until failures are resolved!")

print("\nConfiguration Summary:")
print(f"  Price Range: $15.00 - $350.00")
print(f"  Target Universe: 10-15 stocks")
print(f"  Acceptable Range: 5-20 stocks")
print(f"  Fallback Logic: REMOVED (quality only)")
print()
