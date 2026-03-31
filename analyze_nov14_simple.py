#!/usr/bin/env python3
"""
Nov 14 Deep Dive - Simplified and Robust
"""

import json
import pandas as pd

print("="*75)
print("NOV 14, 2025 - DETAILED ANALYSIS")
print("="*75)
print()

# Load positions
with open('positions.json', 'r') as f:
    positions = json.load(f)

# Convert to DataFrame for easier analysis
df = pd.DataFrame(positions)

# Filter to exits on Nov 14
df['exit_date_only'] = df['exit_timestamp'].apply(lambda x: x.split('T')[0] if pd.notna(x) else None)
nov14 = df[df['exit_date_only'] == '2025-11-14'].copy()

print(f"Total positions exited on Nov 14: {len(nov14)}")
print()

if len(nov14) == 0:
    print("⚠️  No exits found for Nov 14. Checking available dates...")
    print("Available exit dates:")
    print(df['exit_date_only'].value_counts().head(10))
    exit()

# Add entry date
nov14['entry_date_only'] = nov14['entry_timestamp'].apply(lambda x: x.split('T')[0] if pd.notna(x) else None)

# Calculate P&L percentage
nov14['pnl_pct'] = ((nov14['exit_price'] - nov14['entry_price']) / nov14['entry_price']) * 100

# Summary stats
total_pnl = nov14['realized_pnl'].sum()
winners = len(nov14[nov14['realized_pnl'] > 0])
losers = len(nov14[nov14['realized_pnl'] <= 0])

print("="*75)
print("SUMMARY")
print("="*75)
print(f"Total P&L: ${total_pnl:+.2f}")
print(f"Winners: {winners}")
print(f"Losers: {losers}")
print(f"Win Rate: {winners/len(nov14)*100:.1f}%")
print()

# Exit reasons
print("Exit Reasons:")
print(nov14['exit_reason'].value_counts())
print()

print("="*75)
print("ALL NOV 14 EXITS (sorted by P&L)")
print("="*75)
print()

for idx, row in nov14.sort_values('realized_pnl').iterrows():
    status = "🚨" if 'EMERGENCY' in row['exit_reason'] or 'STOP' in row['exit_reason'] else ("✅" if row['realized_pnl'] > 0 else "⏰")
    
    print(f"{status} {row['symbol']:6} ${row['realized_pnl']:+8.2f} ({row['pnl_pct']:+.2f}%)")
    print(f"   Entry: {row['entry_date_only']} @ ${row['entry_price']:.2f}")
    print(f"   Exit:  {row['exit_date_only']} @ ${row['exit_price']:.2f}")
    print(f"   Reason: {row['exit_reason']}")
    
    # Get signal data if available
    if 'ai_signal' in row and pd.notna(row['ai_signal']) and row['ai_signal']:
        signal = row['ai_signal']
        if isinstance(signal, str):
            signal = json.loads(signal)
        if isinstance(signal, dict):
            mom = signal.get('momentum_score', signal.get('momentum', 0))
            vol = signal.get('volume_surge', signal.get('volume', 0))
            if mom or vol:
                print(f"   Entry Signal: {mom*100:.2f}% momentum, {vol:.2f}x volume")
    print()

# Analysis by entry date
print("="*75)
print("ANALYSIS BY ENTRY DATE")
print("="*75)
print()

entry_date_analysis = nov14.groupby('entry_date_only').agg({
    'realized_pnl': ['sum', 'count', 'mean'],
    'symbol': 'count'
}).round(2)

print("Which entry dates led to Nov 14 exits?")
for entry_date in nov14['entry_date_only'].unique():
    entry_trades = nov14[nov14['entry_date_only'] == entry_date]
    entry_pnl = entry_trades['realized_pnl'].sum()
    entry_winners = len(entry_trades[entry_trades['realized_pnl'] > 0])
    entry_losers = len(entry_trades[entry_trades['realized_pnl'] <= 0])
    
    print(f"\n{entry_date}: {len(entry_trades)} positions")
    print(f"  Total P&L: ${entry_pnl:+.2f}")
    print(f"  Win/Loss: {entry_winners}W / {entry_losers}L")
    print(f"  Stocks: {', '.join(entry_trades['symbol'].tolist())}")

# Check for patterns
print()
print("="*75)
print("PATTERN ANALYSIS")
print("="*75)
print()

winners_df = nov14[nov14['realized_pnl'] > 0]
losers_df = nov14[nov14['realized_pnl'] <= 0]

print(f"Winners ({len(winners_df)}):")
if len(winners_df) > 0:
    print(f"  Avg P&L: ${winners_df['realized_pnl'].mean():+.2f} ({winners_df['pnl_pct'].mean():+.2f}%)")
    print(f"  Entry dates: {winners_df['entry_date_only'].value_counts().to_dict()}")

print()
print(f"Losers ({len(losers_df)}):")
if len(losers_df) > 0:
    print(f"  Avg P&L: ${losers_df['realized_pnl'].mean():+.2f} ({losers_df['pnl_pct'].mean():+.2f}%)")
    print(f"  Entry dates: {losers_df['entry_date_only'].value_counts().to_dict()}")
    print(f"  Emergency stops: {len(losers_df[losers_df['exit_reason'].str.contains('EMERGENCY|STOP', na=False)])}/{len(losers_df)}")

# Wednesday curse?
print()
print("="*75)
print("WED NOV 13 ENTRY ANALYSIS (The Suspected Culprit)")
print("="*75)
print()

wed_entries = nov14[nov14['entry_date_only'] == '2025-11-13']
if len(wed_entries) > 0:
    wed_pnl = wed_entries['realized_pnl'].sum()
    wed_winners = len(wed_entries[wed_entries['realized_pnl'] > 0])
    wed_losers = len(wed_entries[wed_entries['realized_pnl'] <= 0])
    
    print(f"Wed Nov 13 entries that exited Thu Nov 14: {len(wed_entries)}")
    print(f"Total P&L: ${wed_pnl:+.2f}")
    print(f"Win Rate: {wed_winners}/{len(wed_entries)} = {wed_winners/len(wed_entries)*100:.1f}%")
    print()
    
    print("Individual Wed entries:")
    for idx, row in wed_entries.sort_values('realized_pnl').iterrows():
        print(f"  {row['symbol']:6} ${row['realized_pnl']:+8.2f} ({row['pnl_pct']:+.2f}%) - {row['exit_reason']}")
    
    if wed_losers > wed_winners:
        print()
        print("🚨 CONCLUSION: Wed Nov 13 entries were the problem!")
        print(f"   {wed_losers} losers vs {wed_winners} winners")
        print(f"   Total damage: ${wed_pnl:+.2f}")
else:
    print("No Wed Nov 13 entries found")

print()
print("="*75)
print("OVERALL CONCLUSION")
print("="*75)
print()

emergency_count = len(nov14[nov14['exit_reason'].str.contains('EMERGENCY|STOP', na=False)])
if emergency_count > len(nov14) * 0.5:
    print("⚠️  SYSTEMATIC PROBLEM DETECTED")
    print(f"   {emergency_count}/{len(nov14)} trades hit emergency stops")
    print("   This suggests a market-wide event or strategy flaw")
elif losers > winners * 1.5:
    print("⚠️  UNUSUAL LOSS DAY")
    print(f"   {losers} losers vs {winners} winners")
    print("   More losers than normal but may be variance")
else:
    print("📊 WITHIN NORMAL VARIANCE")
    print("   Mix of wins and losses, not necessarily systematic")

print()
