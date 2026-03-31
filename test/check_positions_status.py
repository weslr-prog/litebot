#!/usr/bin/env python3
"""
Quick diagnostic to check positions.json status
"""
import json
from collections import Counter

# Load positions
with open('positions.json', 'r') as f:
    positions = json.load(f)

print("=" * 80)
print("📊 POSITIONS.JSON DIAGNOSTIC")
print("=" * 80)

total = len(positions)
print(f"\n📋 Total positions in file: {total}")

# Status breakdown
statuses = Counter(p.get('status', 'unknown') for p in positions)
print(f"\n📈 Status Breakdown:")
for status, count in statuses.most_common():
    print(f"   {status:15} : {count:3} positions")

# Share count issues
zero_shares = [p for p in positions if p.get('position_size_shares', 0) == 0]
active_with_zero = [p for p in zero_shares if p.get('status') == 'entered']
exited_with_zero = [p for p in zero_shares if p.get('status') == 'exited']

print(f"\n⚠️  Positions with 0 shares:")
print(f"   Total: {len(zero_shares)}")
print(f"   Active (entered): {len(active_with_zero)}")
print(f"   Exited: {len(exited_with_zero)}")

if active_with_zero:
    print(f"\n❌ PROBLEM: {len(active_with_zero)} active positions have 0 shares!")
    print("   These will need to be synced from Alpaca:")
    for p in active_with_zero[:5]:  # Show first 5
        print(f"   - {p['symbol']} (entry: ${p['entry_price']:.2f}, value: ${p['position_size_dollars']:.2f})")
else:
    print(f"\n✅ GOOD: No active positions with 0 shares")

if exited_with_zero:
    print(f"\n✅ OK: {len(exited_with_zero)} exited positions have 0 shares (normal)")

print("\n" + "=" * 80)
print("🔧 FIX APPLIED:")
print("   • Modified save logic to only sync ACTIVE positions")
print("   • Exited positions will correctly save with 0 shares")
print("   • No more spam warnings for historical positions")
print("=" * 80)
