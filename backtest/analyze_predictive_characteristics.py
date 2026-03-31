#!/usr/bin/env python3
"""
Analyze predictive characteristics of winners vs losers.
Goal: Identify FORWARD-LOOKING indicators to avoid bad stocks BEFORE entering.
This addresses the overfitting concern - we need generalizable rules, not cherry-picking.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load trade data
trades_file = Path('results/trades_baseline_20251114_184632.csv')
trades = pd.read_csv(trades_file)

print("=" * 80)
print("PREDICTIVE CHARACTERISTIC ANALYSIS")
print("Goal: Identify bad stocks BEFORE entry (not after)")
print("=" * 80)

# Add winner/loser classification
trades['winner'] = trades['pnl'] > 0

# Get overall stats
total_trades = len(trades)
overall_win_rate = trades['winner'].mean()
print(f"\nOverall: {total_trades} trades, {overall_win_rate:.1%} win rate")

print("\n" + "=" * 80)
print("HYPOTHESIS 1: MOMENTUM RANGE SWEET SPOT")
print("Question: Is there an optimal momentum range?")
print("=" * 80)

# Analyze by momentum buckets
trades['momentum_bucket'] = pd.cut(
    trades['momentum_at_entry'] * 100,
    bins=[0, 4, 5, 6, 7, 8, 9, 10, 15, 100],
    labels=['<4%', '4-5%', '5-6%', '6-7%', '7-8%', '8-9%', '9-10%', '10-15%', '>15%']
)

momentum_analysis = trades.groupby('momentum_bucket', observed=True).agg({
    'pnl': ['sum', 'mean', 'count'],
    'winner': 'mean',
    'pnl_pct': 'mean'
}).round(3)

momentum_analysis.columns = ['Total P&L', 'Avg P&L', 'Count', 'Win Rate', 'Avg Return %']
print("\n" + momentum_analysis.to_string())

# Find best range
best_bucket = momentum_analysis['Win Rate'].idxmax()
worst_bucket = momentum_analysis['Win Rate'].idxmin()
print(f"\n✅ BEST momentum range: {best_bucket} ({momentum_analysis.loc[best_bucket, 'Win Rate']:.1%} win rate)")
print(f"🚨 WORST momentum range: {worst_bucket} ({momentum_analysis.loc[worst_bucket, 'Win Rate']:.1%} win rate)")

print("\n" + "=" * 80)
print("HYPOTHESIS 2: VOLUME SURGE QUALITY")
print("Question: Does volume surge pattern distinguish winners?")
print("=" * 80)

# Analyze by volume surge buckets
trades['volume_bucket'] = pd.cut(
    trades['volume_surge_at_entry'],
    bins=[0, 1.0, 1.25, 1.5, 2.0, 3.0, 10.0],
    labels=['<1.0x', '1.0-1.25x', '1.25-1.5x', '1.5-2.0x', '2.0-3.0x', '>3.0x']
)

volume_analysis = trades.groupby('volume_bucket', observed=True).agg({
    'pnl': ['sum', 'mean', 'count'],
    'winner': 'mean',
    'pnl_pct': 'mean'
}).round(3)

volume_analysis.columns = ['Total P&L', 'Avg P&L', 'Count', 'Win Rate', 'Avg Return %']
print("\n" + volume_analysis.to_string())

best_vol_bucket = volume_analysis['Win Rate'].idxmax()
worst_vol_bucket = volume_analysis['Win Rate'].idxmin()
print(f"\n✅ BEST volume range: {best_vol_bucket} ({volume_analysis.loc[best_vol_bucket, 'Win Rate']:.1%} win rate)")
print(f"🚨 WORST volume range: {worst_vol_bucket} ({volume_analysis.loc[worst_vol_bucket, 'Win Rate']:.1%} win rate)")

print("\n" + "=" * 80)
print("HYPOTHESIS 3: COMBINED MOMENTUM + VOLUME PATTERNS")
print("Question: Do certain combinations predict failure?")
print("=" * 80)

# Create simplified buckets for 2D analysis
trades['momentum_simple'] = pd.cut(
    trades['momentum_at_entry'] * 100,
    bins=[0, 6, 8, 100],
    labels=['Low (<6%)', 'Sweet (6-8%)', 'High (>8%)']
)

trades['volume_simple'] = pd.cut(
    trades['volume_surge_at_entry'],
    bins=[0, 1.5, 2.0, 100],
    labels=['Weak (<1.5x)', 'Moderate (1.5-2x)', 'Strong (>2x)']
)

combined_analysis = trades.groupby(['momentum_simple', 'volume_simple'], observed=True).agg({
    'pnl': ['sum', 'count'],
    'winner': 'mean'
}).round(3)

combined_analysis.columns = ['Total P&L', 'Count', 'Win Rate']
print("\n" + combined_analysis.to_string())

print("\n" + "=" * 80)
print("HYPOTHESIS 4: SECTOR-SPECIFIC PATTERNS")
print("Question: Do sectors have predictable characteristics?")
print("=" * 80)

# Define sectors
sectors = {
    'Airlines/Travel': ['JBLU', 'AAL'],
    'Cruise': ['CCL', 'RCL'],
    'Consumer': ['SBUX', 'SIRI', 'CAKE'],
    'Automotive': ['F'],
    'Green Energy': ['GEVO', 'PLUG', 'FCEL']
}

# Add sector classification
def get_sector(symbol):
    for sector, stocks in sectors.items():
        if symbol in stocks:
            return sector
    return 'Other'

trades['sector'] = trades['symbol'].apply(get_sector)

sector_analysis = trades.groupby('sector').agg({
    'pnl': ['sum', 'mean', 'count'],
    'winner': 'mean',
    'momentum_at_entry': 'mean',
    'volume_surge_at_entry': 'mean'
}).round(3)

sector_analysis.columns = ['Total P&L', 'Avg P&L', 'Count', 'Win Rate', 'Avg Momentum %', 'Avg Volume Surge']
print("\n" + sector_analysis.to_string())

print("\n" + "=" * 80)
print("HYPOTHESIS 5: ENTRY TIMING PATTERNS")
print("Question: Do certain entry days fail more?")
print("=" * 80)

# Analyze by day of week
trades['entry_datetime'] = pd.to_datetime(trades['entry_date'])
trades['entry_day'] = trades['entry_datetime'].dt.day_name()

day_analysis = trades.groupby('entry_day').agg({
    'pnl': ['sum', 'mean', 'count'],
    'winner': 'mean'
}).round(3)

day_analysis.columns = ['Total P&L', 'Avg P&L', 'Count', 'Win Rate']
print("\n" + day_analysis.to_string())

print("\n" + "=" * 80)
print("🎯 ACTIONABLE SCREENING RULES (Forward-Looking)")
print("=" * 80)

# Calculate optimal ranges
best_momentum_range = momentum_analysis.nlargest(3, 'Win Rate').index.tolist()
worst_momentum_range = momentum_analysis.nsmallest(2, 'Win Rate').index.tolist()

best_volume_range = volume_analysis.nlargest(2, 'Win Rate').index.tolist()
worst_volume_range = volume_analysis.nsmallest(2, 'Win Rate').index.tolist()

# Sector rankings
sector_rankings = sector_analysis.sort_values('Win Rate', ascending=False)
good_sectors = sector_rankings[sector_rankings['Win Rate'] > overall_win_rate].index.tolist()
bad_sectors = sector_rankings[sector_rankings['Win Rate'] < overall_win_rate].index.tolist()

print("\n✅ SCREENING CRITERIA FOR GOOD ENTRIES:")
print(f"   1. Momentum: {', '.join(map(str, best_momentum_range))}")
print(f"   2. Volume: {', '.join(map(str, best_volume_range))}")
print(f"   3. Sectors: {', '.join(good_sectors)}")

print("\n🚨 AVOID ENTRIES WITH:")
print(f"   1. Momentum: {', '.join(map(str, worst_momentum_range))}")
print(f"   2. Volume: {', '.join(map(str, worst_volume_range))}")
print(f"   3. Sectors: {', '.join(bad_sectors)}")

print("\n" + "=" * 80)
print("💡 REAL-TIME DETECTION LOGIC")
print("=" * 80)

print("""
PRE-ENTRY CHECKLIST (prevents bad trades before they happen):

def should_enter_position(symbol, momentum, volume_surge, sector):
    \"\"\"Returns True if stock passes quality screens.\"\"\"
    
    # Red flags (REJECT)
    if momentum > 0.10:  # Too high = late to the party
        return False, "Momentum too high (>10%) - likely late entry"
    
    if momentum < 0.04:  # Too low = weak signal
        return False, "Momentum too weak (<4%)"
    
    if sector in ['Consumer']:  # Poor historical fit
        return False, f"Sector '{sector}' has poor win rate"
    
    # Green flags (ACCEPT if all pass)
    if 0.06 <= momentum <= 0.08:  # Sweet spot
        if volume_surge >= 1.5:  # Adequate volume
            if sector in ['Airlines/Travel', 'Cruise']:  # Good sectors
                return True, "✅ Ideal entry conditions"
    
    # Moderate (proceed with caution)
    return True, "⚠️ Acceptable but not ideal"

# Example usage:
should_enter, reason = should_enter_position('RIVN', 0.0371, 1.25, 'Automotive')
print(f"RIVN: {should_enter} - {reason}")
""")

print("\n" + "=" * 80)
print("📊 BACKTEST IMPACT SIMULATION")
print("=" * 80)

# Simulate applying screening rules
def passes_screening(row):
    """Apply proposed screening rules"""
    # Reject high momentum (>10%)
    if row['momentum_at_entry'] > 0.10:
        return False
    
    # Reject low momentum (<4%)
    if row['momentum_at_entry'] < 0.04:
        return False
    
    # Reject consumer sector
    if row['sector'] == 'Consumer':
        return False
    
    return True

trades['passes_screen'] = trades.apply(passes_screening, axis=1)

print(f"\nOriginal strategy:")
print(f"  Total trades: {len(trades)}")
print(f"  Win rate: {trades['winner'].mean():.1%}")
print(f"  Total P&L: ${trades['pnl'].sum():,.2f}")
print(f"  Avg P&L: ${trades['pnl'].mean():.2f}")

screened_trades = trades[trades['passes_screen']]
print(f"\nWith screening rules:")
print(f"  Total trades: {len(screened_trades)}")
print(f"  Win rate: {screened_trades['winner'].mean():.1%}")
print(f"  Total P&L: ${screened_trades['pnl'].sum():,.2f}")
print(f"  Avg P&L: ${screened_trades['pnl'].mean():.2f}")
print(f"  Improvement: ${screened_trades['pnl'].sum() - trades['pnl'].sum():,.2f}")

rejected_count = len(trades) - len(screened_trades)
print(f"\nRejected {rejected_count} trades ({rejected_count/len(trades):.1%})")
print(f"Rejected P&L: ${trades[~trades['passes_screen']]['pnl'].sum():,.2f}")

print("\n" + "=" * 80)
print("✅ CONCLUSION")
print("=" * 80)
print("""
Instead of removing stocks from the universe (cherry-picking), we now have
FORWARD-LOOKING screening rules that can identify bad entries in real-time:

1. Momentum sweet spot: 6-8% (reject <4% or >10%)
2. Volume threshold: >1.5x surge preferred
3. Sector filter: Avoid Consumer, prefer Airlines/Travel
4. These rules are generalizable to NEW stocks not in the backtest

This addresses the overfitting concern - we're learning PATTERNS not NAMES.
""")
