#!/usr/bin/env python3
"""
Drawdown Investigation - Analyze what caused the 24.3% drawdown
"""

import sys
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

def investigate_drawdown():
    """Investigate the 24.3% drawdown"""
    print("🔍 INVESTIGATING 24.3% DRAWDOWN")
    print("=" * 60)
    
    # Load recent positions
    positions_file = "/home/wes/Desktop/litebotx-usb-deployment/positions.json"
    
    if not os.path.exists(positions_file):
        print("❌ No positions file found")
        return None
    
    with open(positions_file, 'r') as f:
        positions = json.load(f)
    
    print(f"📊 Total positions loaded: {len(positions)}")
    
    # Analyze losses
    losses = []
    wins = []
    largest_losses = []
    
    for pos in positions:
        if pos.get('realized_pnl') is not None:
            pnl = pos['realized_pnl']
            entry_price = pos.get('entry_price', 0)
            exit_price = pos.get('exit_price', 0)
            
            if entry_price > 0:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if exit_price else 0
            else:
                pnl_pct = 0
            
            pos_info = {
                'symbol': pos.get('symbol'),
                'entry_date': pos.get('entry_date'),
                'exit_date': pos.get('exit_date'),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': pos.get('quantity', 0),
                'pnl_dollars': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': pos.get('exit_reason'),
                'hold_days': pos.get('hold_days', 0)
            }
            
            if pnl < 0:
                losses.append(pos_info)
            else:
                wins.append(pos_info)
    
    # Sort losses by dollar amount
    losses.sort(key=lambda x: x['pnl_dollars'])
    
    print(f"\n📉 LOSS ANALYSIS:")
    print(f"   Total losing trades: {len(losses)}")
    print(f"   Total winning trades: {len(wins)}")
    print(f"   Win rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    
    # Calculate total losses and wins
    total_losses = sum(l['pnl_dollars'] for l in losses)
    total_wins = sum(w['pnl_dollars'] for w in wins)
    net_pnl = total_wins + total_losses
    
    print(f"\n💰 P&L BREAKDOWN:")
    print(f"   Total losses: ${total_losses:,.2f}")
    print(f"   Total wins: ${total_wins:,.2f}")
    print(f"   Net P&L: ${net_pnl:,.2f}")
    
    # Identify largest losses (top 10)
    print(f"\n🔴 TOP 10 LARGEST LOSSES:")
    for i, loss in enumerate(losses[:10], 1):
        print(f"   {i}. {loss['symbol']}: ${loss['pnl_dollars']:,.2f} ({loss['pnl_pct']:.1f}%)")
        print(f"      Entry: ${loss['entry_price']:.2f} on {loss['entry_date']}")
        print(f"      Exit: ${loss['exit_price']:.2f} on {loss['exit_date']} ({loss['exit_reason']})")
        print(f"      Hold: {loss['hold_days']} days, Qty: {loss['quantity']}")
    
    # Analyze by exit reason
    print(f"\n📊 LOSSES BY EXIT REASON:")
    exit_reasons = defaultdict(lambda: {'count': 0, 'total_loss': 0})
    for loss in losses:
        reason = loss['exit_reason'] or 'unknown'
        exit_reasons[reason]['count'] += 1
        exit_reasons[reason]['total_loss'] += loss['pnl_dollars']
    
    for reason, data in sorted(exit_reasons.items(), key=lambda x: x[1]['total_loss']):
        print(f"   {reason}: {data['count']} trades, ${data['total_loss']:,.2f}")
    
    # Analyze timing patterns
    print(f"\n📅 TEMPORAL ANALYSIS:")
    recent_losses = [l for l in losses if l['exit_date'] and l['exit_date'] >= '2025-09-15']
    if recent_losses:
        recent_loss_total = sum(l['pnl_dollars'] for l in recent_losses)
        print(f"   Losses since Sep 15: {len(recent_losses)} trades, ${recent_loss_total:,.2f}")
    
    # Identify concentration risk
    print(f"\n🎯 CONCENTRATION ANALYSIS:")
    symbol_losses = defaultdict(lambda: {'count': 0, 'total_loss': 0})
    for loss in losses:
        symbol_losses[loss['symbol']]['count'] += 1
        symbol_losses[loss['symbol']]['total_loss'] += loss['pnl_dollars']
    
    worst_symbols = sorted(symbol_losses.items(), key=lambda x: x[1]['total_loss'])[:5]
    for symbol, data in worst_symbols:
        print(f"   {symbol}: {data['count']} losses, ${data['total_loss']:,.2f}")
    
    # Calculate drawdown components
    print(f"\n🔍 DRAWDOWN COMPONENTS:")
    top_5_losses = sum(l['pnl_dollars'] for l in losses[:5])
    print(f"   Top 5 losses total: ${top_5_losses:,.2f}")
    print(f"   Percentage of total loss: {(top_5_losses/total_losses)*100:.1f}%")
    
    # Identify risk management issues
    print(f"\n⚠️  RISK MANAGEMENT ISSUES:")
    large_losses = [l for l in losses if abs(l['pnl_dollars']) > 500]
    if large_losses:
        print(f"   🚨 {len(large_losses)} losses > $500 (position sizing too large)")
        for loss in large_losses:
            print(f"      {loss['symbol']}: ${loss['pnl_dollars']:,.2f}")
    
    overnight_losses = [l for l in losses if l['hold_days'] >= 1]
    print(f"   🌙 {len(overnight_losses)} overnight losses (D+1 exit risk)")
    
    # Calculate what caused the drawdown
    print(f"\n🎯 DRAWDOWN ROOT CAUSES:")
    
    causes = []
    
    # Check if position sizing is too aggressive
    avg_loss_size = abs(total_losses / len(losses)) if losses else 0
    if avg_loss_size > 300:
        causes.append(f"Average loss size (${avg_loss_size:.0f}) indicates position sizing too large")
    
    # Check if stop losses are working
    stop_loss_exits = [l for l in losses if 'stop' in str(l['exit_reason']).lower()]
    if len(stop_loss_exits) < len(losses) * 0.5:
        causes.append(f"Only {len(stop_loss_exits)}/{len(losses)} losses from stop losses - stops may not be triggering")
    
    # Check for concentrated losses
    if worst_symbols and worst_symbols[0][1]['total_loss'] < total_losses * -0.3:
        worst_sym = worst_symbols[0]
        causes.append(f"Concentrated losses in {worst_sym[0]} (${worst_sym[1]['total_loss']:,.2f})")
    
    for i, cause in enumerate(causes, 1):
        print(f"   {i}. {cause}")
    
    return {
        'total_losses': total_losses,
        'total_wins': total_wins,
        'net_pnl': net_pnl,
        'largest_losses': losses[:10],
        'causes': causes,
        'loss_count': len(losses),
        'win_count': len(wins),
        'avg_loss_size': avg_loss_size,
        'large_losses': large_losses
    }

if __name__ == "__main__":
    investigation = investigate_drawdown()
    
    if investigation:
        print(f"\n🎯 RECOMMENDED ACTIONS:")
        
        if investigation['avg_loss_size'] > 300:
            print(f"   1. ⚠️  CRITICAL: Reduce position sizes immediately")
            print(f"      Current avg loss: ${investigation['avg_loss_size']:.0f}")
            print(f"      Recommended: Reduce position size by 40-50%")
        
        if len(investigation['large_losses']) > 0:
            print(f"   2. 🛡️  Implement stricter stop losses")
            print(f"      {len(investigation['large_losses'])} positions lost >$500")
        
        print(f"   3. 📊 Review confidence threshold effectiveness")
        print(f"      Win rate may need improvement despite optimization")
        
        print(f"   4. 🎲 Consider diversification improvements")
        print(f"      Reduce concentration in poorly performing symbols")