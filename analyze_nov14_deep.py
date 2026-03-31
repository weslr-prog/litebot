#!/usr/bin/env python3
"""
Deep Dive: Nov 14 Anomaly Analysis
What made Thursday so bad? Can we identify patterns to avoid future disasters?
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

print("="*75)
print("NOV 14, 2025 ANOMALY DEEP DIVE")
print("="*75)
print()

# Load positions.json to analyze Nov 14 specifically
positions_file = Path('positions.json')
if not positions_file.exists():
    print("❌ positions.json not found")
    exit(1)

with open(positions_file, 'r') as f:
    positions = json.load(f)

# Filter to Nov 14 exits
nov14_exits = []
for pos in positions:
    if 'exit_timestamp' in pos and pos['exit_timestamp']:
        exit_date = pos['exit_timestamp'].split('T')[0]
        if exit_date == '2025-11-14':
            nov14_exits.append(pos)

print(f"Found {len(nov14_exits)} positions exited on Nov 14\n")

print("="*75)
print("NOV 14 EXITS ANALYSIS")
print("="*75)
print()

total_nov14_pnl = 0
emergency_stops = 0
profit_takes = 0
time_exits = 0

for pos in sorted(nov14_exits, key=lambda x: x['pnl']):
    symbol = pos['symbol']
    entry_time = pos['entry_timestamp'].split('T')[0]
    entry_price = pos['entry_price']
    exit_price = pos['exit_price']
    pnl = pos['pnl']
    pnl_pct = pos['pnl_pct']
    exit_reason = pos['exit_reason']
    shares = pos['shares']
    
    # Get entry stats
    momentum = pos.get('momentum_score', 0)
    volume_surge = pos.get('volume_surge', 0)
    
    total_nov14_pnl += pnl
    
    if 'EMERGENCY' in exit_reason or 'STOP' in exit_reason:
        emergency_stops += 1
        status = "🚨 EMERGENCY STOP"
    elif 'PROFIT' in exit_reason:
        profit_takes += 1
        status = "✅ PROFIT"
    else:
        time_exits += 1
        status = "⏰ TIME EXIT"
    
    print(f"{symbol:6} {status}")
    print(f"  Entry: {entry_time} @ ${entry_price:.2f}")
    print(f"  Exit:  2025-11-14 @ ${exit_price:.2f}")
    print(f"  P&L: ${pnl:+.2f} ({pnl_pct*100:+.2f}%)")
    print(f"  Shares: {shares}, Exit: {exit_reason}")
    print(f"  Entry Momentum: {momentum*100:.2f}%, Volume Surge: {volume_surge:.2f}x")
    print()

print("="*75)
print("NOV 14 SUMMARY")
print("="*75)
if len(nov14_exits) > 0:
    print(f"Total P&L: ${total_nov14_pnl:+.2f}")
    print(f"Emergency Stops: {emergency_stops}/{len(nov14_exits)} ({emergency_stops/len(nov14_exits)*100:.1f}%)")
    print(f"Profit Takes: {profit_takes}/{len(nov14_exits)}")
    print(f"Time Exits: {time_exits}/{len(nov14_exits)}")
else:
    print("No exits found on Nov 14, 2025")
    print("Note: Check if positions.json has data for this date")
print()

# Analyze entries from Nov 13 (most likely culprits)
print("="*75)
print("NOV 13 ENTRIES (That Exited Nov 14)")
print("="*75)
print()

nov13_entries = []
for pos in positions:
    if 'entry_timestamp' in pos and pos['entry_timestamp']:
        entry_date = pos['entry_timestamp'].split('T')[0]
        if entry_date == '2025-11-13':
            nov13_entries.append(pos)

print(f"Found {len(nov13_entries)} entries on Nov 13\n")

# Which ones failed on Nov 14?
nov13_that_failed = [p for p in nov13_entries if p.get('exit_timestamp', '').startswith('2025-11-14') and p['pnl'] < 0]
print(f"Nov 13 entries that LOST on Nov 14: {len(nov13_that_failed)}")

for pos in sorted(nov13_that_failed, key=lambda x: x['pnl']):
    symbol = pos['symbol']
    entry_price = pos['entry_price']
    exit_price = pos['exit_price']
    pnl = pos['pnl']
    pnl_pct = pos['pnl_pct']
    momentum = pos.get('momentum_score', 0)
    volume_surge = pos.get('volume_surge', 0)
    
    print(f"\n{symbol}: ${pnl:+.2f} ({pnl_pct*100:+.2f}%)")
    print(f"  Entry momentum: {momentum*100:.2f}%")
    print(f"  Volume surge: {volume_surge:.2f}x")
    print(f"  Entry price: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
    print(f"  Exit reason: {pos['exit_reason']}")

print()
print("="*75)
print("PATTERN ANALYSIS - What Do Failed Trades Have In Common?")
print("="*75)
print()

# Calculate averages for winners vs losers
winners = [p for p in nov14_exits if p['pnl'] > 0]
losers = [p for p in nov14_exits if p['pnl'] <= 0]

if winners:
    avg_winner_momentum = sum(p.get('momentum_score', 0) for p in winners) / len(winners)
    avg_winner_volume = sum(p.get('volume_surge', 0) for p in winners) / len(winners)
    avg_winner_pnl = sum(p['pnl_pct'] for p in winners) / len(winners)
    
    print(f"WINNERS on Nov 14 ({len(winners)} trades):")
    print(f"  Avg entry momentum: {avg_winner_momentum*100:.2f}%")
    print(f"  Avg volume surge: {avg_winner_volume:.2f}x")
    print(f"  Avg P&L: {avg_winner_pnl*100:+.2f}%")
    print()

if losers:
    avg_loser_momentum = sum(p.get('momentum_score', 0) for p in losers) / len(losers)
    avg_loser_volume = sum(p.get('volume_surge', 0) for p in losers) / len(losers)
    avg_loser_pnl = sum(p['pnl_pct'] for p in losers) / len(losers)
    
    print(f"LOSERS on Nov 14 ({len(losers)} trades):")
    print(f"  Avg entry momentum: {avg_loser_momentum*100:.2f}%")
    print(f"  Avg volume surge: {avg_loser_volume:.2f}x")
    print(f"  Avg P&L: {avg_loser_pnl*100:+.2f}%")
    print()
    
    if winners:
        print("DIFFERENCE:")
        print(f"  Momentum: {(avg_loser_momentum - avg_winner_momentum)*100:+.2f}% (losers vs winners)")
        print(f"  Volume: {(avg_loser_volume - avg_winner_volume):+.2f}x")
        print()

# Check if there was a market-wide event on Nov 14
print("="*75)
print("MARKET CONTEXT - Was Nov 14 a Market-Wide Event?")
print("="*75)
print()

# Analyze by sector
sectors = {
    'Airlines/Travel': ['JBLU', 'AAL'],
    'Cruise': ['CCL', 'RCL', 'NCLH'],
    'Green Energy': ['GEVO', 'PLUG', 'FCEL'],
    'Consumer': ['SBUX', 'SIRI', 'CAKE'],
    'Automotive': ['F', 'RIVN'],
    'Other': []
}

def get_sector(symbol):
    for sector, stocks in sectors.items():
        if symbol in stocks:
            return sector
    return 'Other'

sector_performance = {}
for pos in nov14_exits:
    sector = get_sector(pos['symbol'])
    if sector not in sector_performance:
        sector_performance[sector] = {'pnl': 0, 'count': 0, 'wins': 0}
    sector_performance[sector]['pnl'] += pos['pnl']
    sector_performance[sector]['count'] += 1
    if pos['pnl'] > 0:
        sector_performance[sector]['wins'] += 1

print("Sector performance on Nov 14:")
for sector, stats in sorted(sector_performance.items(), key=lambda x: x[1]['pnl'], reverse=True):
    win_rate = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
    print(f"  {sector:20} ${stats['pnl']:+8.2f}  ({stats['count']} trades, {win_rate:.0f}% win rate)")

print()
print("="*75)
print("HYPOTHESIS TESTING")
print("="*75)
print()

print("1. MOMENTUM EXHAUSTION HYPOTHESIS:")
print("   Do stocks with higher momentum (>6%) fail more on Nov 14?")
high_momentum_losses = [p for p in losers if p.get('momentum_score', 0) > 0.06]
low_momentum_losses = [p for p in losers if p.get('momentum_score', 0) <= 0.06]
print(f"   High momentum (>6%) losers: {len(high_momentum_losses)}/{len(losers)}")
print(f"   Low momentum (≤6%) losers: {len(low_momentum_losses)}/{len(losers)}")
if high_momentum_losses:
    avg_loss_high = sum(p['pnl_pct'] for p in high_momentum_losses) / len(high_momentum_losses)
    print(f"   Avg loss (high momentum): {avg_loss_high*100:.2f}%")
if low_momentum_losses:
    avg_loss_low = sum(p['pnl_pct'] for p in low_momentum_losses) / len(low_momentum_losses)
    print(f"   Avg loss (low momentum): {avg_loss_low*100:.2f}%")
print()

print("2. VOLUME SPIKE HYPOTHESIS:")
print("   Do stocks with higher volume (>1.5x) fail more?")
high_volume_losses = [p for p in losers if p.get('volume_surge', 0) > 1.5]
low_volume_losses = [p for p in losers if p.get('volume_surge', 0) <= 1.5]
print(f"   High volume (>1.5x) losers: {len(high_volume_losses)}/{len(losers)}")
print(f"   Low volume (≤1.5x) losers: {len(low_volume_losses)}/{len(losers)}")
print()

print("3. ENTRY DAY HYPOTHESIS:")
print("   Did Wed Nov 13 entries fail more than older positions?")
wed_entries = len(nov13_that_failed)
total_wed = len([p for p in nov13_entries if p.get('exit_timestamp', '').startswith('2025-11-14')])
wed_fail_rate = wed_entries / total_wed * 100 if total_wed > 0 else 0
print(f"   Wed Nov 13 entries that failed: {wed_entries}/{total_wed} ({wed_fail_rate:.1f}%)")
print()

print("4. SECTOR CONCENTRATION HYPOTHESIS:")
print("   Was the loss concentrated in specific sectors?")
worst_sector = min(sector_performance.items(), key=lambda x: x[1]['pnl'])
print(f"   Worst sector: {worst_sector[0]} (${worst_sector[1]['pnl']:+.2f})")
total_sector_loss = sum(s['pnl'] for s in sector_performance.values() if s['pnl'] < 0)
worst_sector_pct = abs(worst_sector[1]['pnl']) / abs(total_sector_loss) * 100 if total_sector_loss < 0 else 0
print(f"   Worst sector accounted for: {worst_sector_pct:.1f}% of total loss")
print()

print("="*75)
print("CONCLUSIONS")
print("="*75)
print()
print("Based on this analysis:")
print(f"• {emergency_stops}/{len(nov14_exits)} trades hit emergency stops ({emergency_stops/len(nov14_exits)*100:.0f}%)")
print(f"• Most losses came from {worst_sector[0]} sector")
print(f"• Nov 13 entries had {wed_fail_rate:.0f}% failure rate")
print()
print("This suggests Nov 14 was likely:")
if emergency_stops > len(nov14_exits) * 0.5:
    print("  ⚠️  SYSTEMATIC ISSUE - Multiple emergency stops indicate market-wide or strategy flaw")
else:
    print("  📊 NORMAL VARIANCE - Mix of wins/losses, not systematic")
print()
