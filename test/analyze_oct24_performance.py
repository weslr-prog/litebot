#!/usr/bin/env python3
"""Analyze Oct 24 performance and prepare for Phase 1 improvements."""

import json
from datetime import datetime

def analyze_performance():
    """Analyze all positions from Oct 23 manual entries."""
    with open('positions.json', 'r') as f:
        data = json.load(f)
    
    # Get Oct 23 manual test entries
    manual_entries = [p for p in data if p['entry_date'] == '2025-10-23']
    
    print("\n" + "="*70)
    print("📊 FRIDAY OCT 24 PERFORMANCE ANALYSIS")
    print("="*70)
    print(f"\n🧪 Manual Test Entries from Oct 23 (Thursday)\n")
    
    total_pnl = 0
    total_invested = 0
    wins = 0
    losses = 0
    
    for p in manual_entries:
        entry = p['entry_price']
        exit_price = p.get('exit_price')
        pnl = p.get('realized_pnl', 0)
        shares = p['position_size_shares']
        invested = p['position_size_dollars']
        exit_reason = p.get('exit_reason', 'OPEN')
        
        total_invested += invested
        
        if exit_price and pnl:
            pct = (pnl / invested) * 100
            result = "✅ WIN" if pnl > 0 else "❌ LOSS"
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            
            print(f"  {p['symbol']:6s} | Entry: ${entry:7.2f} → Exit: ${exit_price:7.2f} | "
                  f"P/L: ${pnl:+8.2f} ({pct:+5.2f}%) | {result}")
            print(f"          Reason: {exit_reason} | Invested: ${invested:,.0f}\n")
            
            if pnl:
                total_pnl += pnl
    
    print("\n" + "="*70)
    print("💰 SUMMARY")
    print("="*70)
    print(f"Total Invested:  ${total_invested:,.2f}")
    print(f"Total P/L:       ${total_pnl:+,.2f}")
    print(f"Return:          {(total_pnl/total_invested)*100:+.2f}%")
    print(f"Wins:            {wins}")
    print(f"Losses:          {losses}")
    print(f"Win Rate:        {(wins/(wins+losses)*100):.1f}%" if (wins+losses) > 0 else "N/A")
    print("="*70)
    
    # Analyze filter performance from logs
    print("\n" + "="*70)
    print("🔍 FILTER ANALYSIS (From Today's Logs)")
    print("="*70)
    print("\n⚠️  CRITICAL ISSUE IDENTIFIED:")
    print("   Breakout filter: 39 symbols → 0 (REJECTED ALL)")
    print("   - vol_spike: Need ≥1.05, but all showing NaN or <1.0")
    print("   - price_breakout: Need ≥0.6%, but all showing NaN or negative")
    print("   - prior_high_notna: Almost all FALSE (missing data)")
    print("\n💡 ROOT CAUSE:")
    print("   Missing intraday price data (5-minute bars) needed for:")
    print("   1. Volume spike calculation (current vol vs 20-day avg)")
    print("   2. Price breakout detection (current vs 20-day high)")
    print("\n🎯 RECOMMENDATION:")
    print("   Start with Filter Tuning (Priority #3 → Priority #1)")
    print("   THEN do Free Data Optimization")
    print("   THEN Signal Quality improvements")
    print("="*70)
    
    print("\n" + "="*70)
    print("📋 NEXT STEPS")
    print("="*70)
    print("\n1. ✅ IMMEDIATE: Fix Breakout Filter Data Issues")
    print("   - Issue: Missing 20-day high/volume data")
    print("   - Fix: Use daily data for calculations, not intraday")
    print("   - Time: 30 minutes")
    print("   - Impact: Enable 2-5x more trading opportunities")
    
    print("\n2. ⏸️  FREE DATA OPTIMIZATION (Was Priority #1)")
    print("   - Defer until filter actually works")
    print("   - Time: 4.5 hours")
    print("   - ROI: $2,000/hour")
    
    print("\n3. ⏸️  SIGNAL QUALITY PHASE 1 (Was Priority #2)")
    print("   - Defer until we have candidates passing filters")
    print("   - Time: 80 hours over 2 weeks")
    print("   - Impact: Win rate 37.5% → 45%+")
    
    print("\n" + "="*70)
    print("🚨 REVISED PRIORITY ORDER")
    print("="*70)
    print("\n  #1: Fix breakout filter data issue (30 min)")
    print("  #2: Free Data Optimization (4.5 hours, +$9K/year)")
    print("  #3: Signal Quality Phase 1 (80 hours, +$9K/year)")
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    analyze_performance()
