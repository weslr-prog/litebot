#!/usr/bin/env python3
"""
Debug Position Sizing - Find why shares = null
"""
import sys
sys.path.insert(0, '.')

from traders.short_cycle_trader import AIConfidencePositionSizer, ShortCycleConfig, AISignal
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 80)
print("🔍 Position Sizing Debug Test")
print("=" * 80)

# Create config
config = ShortCycleConfig()
print(f"\n📋 Config:")
print(f"   max_risk_per_trade_dollars: ${config.max_risk_per_trade_dollars:,.2f}")
print(f"   max_position_size_percent: {config.max_position_size_percent:.1%}")
print(f"   min_position_size_dollars: ${config.min_position_size_dollars:.2f}")
print(f"   daily_pool_dollars: ${config.daily_pool_dollars:,.2f}")

# Create position sizer
sizer = AIConfidencePositionSizer(config)
print(f"\n✅ Position sizer created")

# Create test signal (like INTC today)
signal = AISignal(
    symbol="INTC",
    action="BUY",
    confidence=0.75,
    time_horizon_days=1.0,  # D+1 strategy
    entry_price=41.79,
    target_price=45.00,
    stop_price=40.00,
    features_used={"momentum": 0.8, "volume_surge": 1.5}
)

print(f"\n📊 Test Signal:")
print(f"   Symbol: {signal.symbol}")
print(f"   Entry: ${signal.entry_price:.2f}")
print(f"   Target: ${signal.target_price:.2f}")
print(f"   Confidence: {signal.confidence:.1%}")

# Test position sizing
stop_price = 40.00
current_portfolio_value = 972000  # Actual account value

print(f"\n🧮 Calculating position size...")
print(f"   Portfolio value: ${current_portfolio_value:,.2f}")
print(f"   Stop price: ${stop_price:.2f}")
print(f"   Stop distance: ${signal.entry_price - stop_price:.2f}")

try:
    shares, position_value = sizer.calculate_position_size(
        signal, stop_price, current_portfolio_value
    )
    
    print(f"\n✅ Result:")
    print(f"   Shares: {shares}")
    print(f"   Type: {type(shares)}")
    print(f"   Position value: ${position_value:,.2f}")
    
    if shares is None:
        print(f"\n🚨 BUG FOUND: shares is None!")
    elif shares == 0:
        print(f"\n⚠️  Shares is 0 (position too small or constraint hit)")
    else:
        print(f"\n✅ Position sizing worked! {shares} shares")
        
except Exception as e:
    print(f"\n❌ ERROR in calculate_position_size:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test with different portfolio values
print(f"\n" + "=" * 80)
print(f"🔬 Testing with different portfolio values:")
print(f"=" * 80)

test_portfolios = [10000, 50000, 100000, 500000, 972000]

for pv in test_portfolios:
    try:
        shares, position_value = sizer.calculate_position_size(signal, stop_price, pv)
        print(f"   ${pv:>10,.0f} → {shares:>6} shares (${position_value:>10,.2f})")
    except Exception as e:
        print(f"   ${pv:>10,.0f} → ERROR: {e}")

print(f"\n" + "=" * 80)
print(f"✅ Test complete")
print(f"=" * 80)
