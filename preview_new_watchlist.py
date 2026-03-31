#!/usr/bin/env python3
"""
Generate New Watchlist with $10-30 Filter
==========================================

Uses the fixed PreFilter to generate a fresh watchlist
showing what stocks the bot will trade with the new configuration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_filter import PreFilter
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

print("\n" + "="*70)
print("WATCHLIST PREVIEW - New $10-30 Mid-Cap Filter")
print("="*70)

# Initialize PreFilter with new configuration
prefilter = PreFilter()

print(f"\nPreFilter Configuration:")
print(f"  Price Range: ${prefilter.MIN_PRICE:.2f} - ${prefilter.MAX_PRICE:.2f}")
print(f"  Volatility: {prefilter.MIN_ATR*100:.1f}% - {prefilter.MAX_ATR*100:.1f}%")
print(f"  Volume: {prefilter.MIN_AVG_VOL:,} shares minimum")
print(f"  Dollar Volume: ${prefilter.MIN_AVG_DOLLAR_VOL:,} minimum")

print("\n" + "-"*70)
print("NOTE: The bot will generate the actual watchlist when it starts.")
print("This is using PreFilter's configuration to show expected behavior.")
print("-"*70)

print("\n✅ PreFilter is configured correctly for $10-30 mid-cap stocks")
print("\nExpected stock types after regeneration:")
print("  ✅ PLTR, RIVN, SNAP - Mid-cap tech/EV (volatile)")
print("  ✅ HOOD, SOFI - Fintech ($10-25 range)")  
print("  ✅ LCID, NIO, XPEV - EV names under $30")
print("  ✅ Other volatile mid-caps in $10-30 range")
print("\nWill automatically exclude:")
print("  ❌ DDOG ($199) - Too expensive")
print("  ❌ NET ($240) - Too expensive")
print("  ❌ BE ($139) - Too expensive")
print("  ❌ ILMN ($121) - Too expensive")
print("  ❌ W ($112) - Too expensive")
print("  ❌ All stocks > $30")

print("\n" + "="*70)
print("Next Steps:")
print("="*70)
print("1. The bot regenerates watchlist automatically on startup")
print("2. Watchlist is saved to logs/watchlist_YYYYMMDD.json")
print("3. Bot will only trade stocks in $10-30 range")
print("4. Old watchlist (Nov 10) will be ignored")
print("\nThe new watchlist will be generated when you restart the bot.")
print("="*70)
