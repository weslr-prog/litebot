#!/usr/bin/env python3
"""
Demo: Regime-Aware Strategy Control
Shows how different market regimes dramatically change trading behavior
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

import pandas as pd
import numpy as np
from regime_aware_controller import RegimeAwareController

def create_regime_scenario(scenario_name: str, price_trend: str, volatility: str):
    """Create market data for different regime scenarios"""
    
    # Base parameters
    days = 100
    base_price = 400
    base_volume = 50_000_000
    
    # Generate price data based on scenario
    if price_trend == "strong_up":
        prices = [base_price + i*2 + np.random.normal(0, 1) for i in range(days)]
    elif price_trend == "strong_down":
        prices = [base_price - i*1.5 + np.random.normal(0, 1) for i in range(days)]
    elif price_trend == "up":
        prices = [base_price + i*0.5 + np.random.normal(0, 1) for i in range(days)]
    elif price_trend == "down":
        prices = [base_price - i*0.3 + np.random.normal(0, 1) for i in range(days)]
    else:  # sideways
        prices = [base_price + np.random.normal(0, 2) for _ in range(days)]
    
    # Adjust volatility
    if volatility == "high":
        prices = [p + np.random.normal(0, 10) for p in prices]
    elif volatility == "low":
        prices = [p + np.random.normal(0, 1) for p in prices]
    else:  # medium
        prices = [p + np.random.normal(0, 3) for p in prices]
    
    # Generate volume data
    volumes = [base_volume + np.random.normal(0, 5_000_000) for _ in range(days)]
    
    return pd.DataFrame({
        'close': prices,
        'volume': volumes
    })

def demo_regime_scenarios():
    print("🌐 REGIME-AWARE STRATEGY CONTROL DEMONSTRATION")
    print("=" * 80)
    print("This shows how different market conditions dramatically change strategy execution\n")
    
    controller = RegimeAwareController()
    
    # Define test scenarios
    scenarios = [
        ("🚀 STRONG BULL MARKET", "strong_up", "low"),
        ("📈 BULL TREND", "up", "medium"), 
        ("⚡ VOLATILE UPTREND", "up", "high"),
        ("📊 SIDEWAYS MARKET", "sideways", "medium"),
        ("🌪️ HIGH VOLATILITY", "sideways", "high"),
        ("📉 BEAR TREND", "down", "medium"),
        ("💥 MARKET CRASH", "strong_down", "high"),
        ("🧊 SLOW DECLINE", "down", "low")
    ]
    
    print("Scenario Analysis:")
    print("-" * 80)
    print(f"{'Regime':<15} {'Exposure':<10} {'Positions':<10} {'Confidence':<12} {'Lookback':<10}")
    print("-" * 80)
    
    for scenario_name, trend, vol in scenarios:
        # Create market data for this scenario
        spy_data = create_regime_scenario(scenario_name, trend, vol)
        market_data = {'SPY': spy_data}
        
        # Detect regime
        regime, confidence = controller.detect_market_regime(market_data)
        summary = controller.get_regime_summary()
        
        print(f"{regime:<15} {summary['max_exposure_pct']:>6.0%}    {summary['max_positions']:>6}      {summary['min_signal_confidence']:>7.0%}      {summary['lookback_multiplier']:>6.1f}x")
    
    print("\n" + "=" * 80)
    print("💡 KEY INSIGHTS:")
    print("\n1. 📈 BULL MARKETS (UP_LOWVOL, bull):")
    print("   • High exposure (90-95%) - capitalize on trends")
    print("   • More positions (12-15) - diversification")
    print("   • Low signal threshold (30-40%) - accept more trades")
    print("   • Shorter lookbacks (0.8-1.0x) - catch momentum quickly")
    
    print("\n2. 🌪️ VOLATILE MARKETS (UP_HIGHVOL, volatile):")
    print("   • Moderate exposure (45-75%) - protect from whipsaws")
    print("   • Fewer positions (6-10) - focus on best ideas")
    print("   • Higher thresholds (50-70%) - quality over quantity")
    print("   • Longer lookbacks (1.2-1.3x) - filter noise")
    
    print("\n3. 📉 BEAR MARKETS (bear, DOWN_LOWVOL):")
    print("   • Low exposure (20-30%) - capital preservation")
    print("   • Very few positions (3-4) - only exceptional opportunities")
    print("   • Very high thresholds (80%+) - extreme selectivity")
    print("   • Long lookbacks (1.4-1.6x) - avoid false signals")
    
    print("\n4. 💥 MARKET CRASHES (DOWN_HIGHVOL):")
    print("   • Minimal exposure (10%) - essentially cash mode")
    print("   • Single position max - extreme concentration")
    print("   • Near-impossible threshold (95%) - almost no trading")
    print("   • Maximum lookbacks (2.0x) - wait for real stability")
    
    print("\n🎯 PROFITABILITY IMPACT:")
    print("Without regime awareness: Bot loses money in bear markets, whipsawed in volatility")
    print("With regime awareness: Bot preserves capital in bad times, maximizes gains in good times")
    print("\nThis is the difference between boom-bust cycles and consistent profitable growth!")

if __name__ == "__main__":
    demo_regime_scenarios()
