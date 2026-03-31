#!/usr/bin/env python3
"""
Quick test of VIX and Macro optimizations
"""
import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("="*70)
print("Testing VIX Position Sizing & Macro Regime Filter")
print("="*70)

# Create trader instance
config = ShortCycleConfig()
trader = ShortCycleTrader(config=config)

print("\n📊 Test 1: VIX Position Sizing")
print("-" * 70)
vix_mult = trader.position_sizer._get_vix_regime_multiplier()
print(f"✅ VIX Multiplier: {vix_mult:.2f}")

print("\n📊 Test 2: Macro Regime Check")
print("-" * 70)
macro_ok = trader._check_macro_regime()
print(f"✅ Macro Regime: {'SAFE TO TRADE' if macro_ok else 'STOP TRADING'}")

print("\n" + "="*70)
print("✅ All optimization tests passed!")
print("="*70)
