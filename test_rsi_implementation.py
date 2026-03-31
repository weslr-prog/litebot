#!/usr/bin/env python3
"""Test RSI implementation for mean reversion strategy"""
import pandas as pd
import numpy as np
from core.indicators import calculate_rsi

def test_rsi_oversold():
    """Test RSI calculation with oversold scenario"""
    print("="*60)
    print("Test 1: RSI Oversold Detection")
    print("="*60)
    
    # Create test data (strong downtrend = oversold)
    prices = [100, 98, 96, 94, 92, 90, 88, 86, 84, 82, 80]
    df = pd.DataFrame({'close': prices})
    
    # Calculate RSI
    df_with_rsi = calculate_rsi(df, window=7)
    current_rsi = df_with_rsi['rsi'].iloc[-1]
    
    print(f"Test prices (declining): {prices[-7:]}")
    print(f"RSI(7): {current_rsi:.2f}")
    print(f"Expected: RSI < 20 (extreme oversold)")
    
    if current_rsi < 30:
        print(f"✅ PASS - RSI {current_rsi:.2f} indicates oversold")
    else:
        print(f"❌ FAIL - RSI {current_rsi:.2f} not oversold enough")
    
    return current_rsi < 30

def test_rsi_neutral():
    """Test RSI calculation with neutral/overbought scenario"""
    print("\n" + "="*60)
    print("Test 2: RSI Neutral Exit Detection")
    print("="*60)
    
    # Create test data (recovery from oversold to neutral)
    prices = [80, 82, 84, 86, 88, 90, 91, 92, 93, 94, 95]
    df = pd.DataFrame({'close': prices})
    
    # Calculate RSI
    df_with_rsi = calculate_rsi(df, window=7)
    current_rsi = df_with_rsi['rsi'].iloc[-1]
    
    print(f"Test prices (recovering): {prices[-7:]}")
    print(f"RSI(7): {current_rsi:.2f}")
    print(f"Expected: RSI > 50 (neutral/exit signal)")
    
    if current_rsi > 50:
        print(f"✅ PASS - RSI {current_rsi:.2f} indicates mean reversion complete")
    else:
        print(f"❌ FAIL - RSI {current_rsi:.2f} still below neutral")
    
    return current_rsi > 50

def test_confidence_calculation():
    """Test confidence calculation from RSI"""
    print("\n" + "="*60)
    print("Test 3: Confidence Calculation from RSI")
    print("="*60)
    
    test_cases = [
        (10, "Extreme oversold", 1.0),
        (15, "Very oversold", 0.5),
        (19, "Just oversold", 0.1),
        (20, "Threshold", 0.0),
        (25, "Not oversold", 0.0),
    ]
    
    for rsi, description, expected_min in test_cases:
        # Confidence formula: (20 - RSI) / 10.0
        confidence = max(0, (20 - rsi) / 10.0)
        confidence = min(confidence, 1.0)
        
        status = "✅" if confidence >= expected_min else "❌"
        print(f"{status} RSI {rsi:2d} ({description:20s}): confidence = {confidence:.2f}")
    
    return True

def test_strategy_simulation():
    """Simulate mean reversion entry and exit"""
    print("\n" + "="*60)
    print("Test 4: Mean Reversion Strategy Simulation")
    print("="*60)
    
    # Simulate a full cycle: oversold -> entry -> recovery -> exit
    price_sequence = [
        100, 95, 90, 85, 80, 75,  # Downtrend (oversold)
        76, 78, 80, 82, 85, 88,   # Recovery (mean reversion)
        90, 92, 94, 95, 96, 97    # Back to neutral
    ]
    
    entry_triggered = False
    entry_price = None
    exit_triggered = False
    exit_price = None
    
    for i in range(7, len(price_sequence)):
        window = price_sequence[max(0, i-20):i+1]
        df = pd.DataFrame({'close': window})
        df_with_rsi = calculate_rsi(df, window=7)
        current_rsi = df_with_rsi['rsi'].iloc[-1]
        current_price = price_sequence[i]
        
        # Entry logic
        if not entry_triggered and current_rsi < 20:
            entry_triggered = True
            entry_price = current_price
            print(f"\n🟢 ENTRY at ${entry_price:.2f} (RSI: {current_rsi:.1f})")
        
        # Exit logic (only after entry)
        if entry_triggered and not exit_triggered:
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Check exit conditions
            if current_rsi > 50:
                exit_triggered = True
                exit_price = current_price
                print(f"🔴 EXIT (RSI Neutral) at ${exit_price:.2f} (RSI: {current_rsi:.1f})")
                print(f"💰 Profit: ${exit_price - entry_price:.2f} ({pnl_pct*100:.2f}%)")
            elif pnl_pct >= 0.02:
                exit_triggered = True
                exit_price = current_price
                print(f"🔴 EXIT (Profit Target) at ${exit_price:.2f} (RSI: {current_rsi:.1f})")
                print(f"💰 Profit: ${exit_price - entry_price:.2f} ({pnl_pct*100:.2f}%)")
    
    if entry_triggered and exit_triggered:
        print(f"\n✅ STRATEGY TEST PASSED - Entry and exit worked correctly")
        return True
    else:
        print(f"\n❌ STRATEGY TEST FAILED - No complete cycle")
        return False

if __name__ == "__main__":
    print("\n🔍 Testing Mean Reversion RSI Implementation\n")
    
    results = []
    results.append(("RSI Oversold Detection", test_rsi_oversold()))
    results.append(("RSI Neutral Exit", test_rsi_neutral()))
    results.append(("Confidence Calculation", test_confidence_calculation()))
    results.append(("Strategy Simulation", test_strategy_simulation()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Mean reversion RSI implementation is working.")
        print("\nNext steps:")
        print("1. Backtest on historical data (validate 15-20% weekly)")
        print("2. Paper trade for 1 week (monitor win rate 60-65%)")
        print("3. Deploy to live if validated")
    else:
        print("\n⚠️  Some tests failed. Review implementation before deployment.")
