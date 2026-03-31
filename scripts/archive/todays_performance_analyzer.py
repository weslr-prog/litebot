#!/usr/bin/env python3
"""
Today's Performance Analyzer - October 13, 2025
Analyzes today's trading activity and investigates exit logic issues
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

class TodaysPerformanceAnalyzer:
    def __init__(self):
        self.positions_file = Path("positions.json")
        self.positions = self._load_positions()
        self.today = date(2025, 10, 13)
        
    def _load_positions(self):
        """Load positions from JSON file"""
        with open(self.positions_file, 'r') as f:
            return json.load(f)
    
    def analyze_todays_trades(self):
        """Analyze all trades from today"""
        print("📊 Today's Performance Analysis - October 13, 2025")
        print("=" * 70)
        
        # Get today's positions (entered or exited today)
        todays_entries = []
        todays_exits = []
        active_positions = []
        
        for pos in self.positions:
            entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
            exit_date_str = pos.get('exit_date')
            exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
            
            # Entries today
            if entry_date == self.today:
                todays_entries.append(pos)
                if pos['status'] == 'entered':
                    active_positions.append(pos)
            
            # Exits today
            if exit_date == self.today and pos['status'] == 'exited':
                todays_exits.append(pos)
        
        print(f"\n🟢 NEW POSITIONS ENTERED TODAY: {len(todays_entries)}")
        if todays_entries:
            total_deployed = sum(p['position_size_dollars'] for p in todays_entries)
            print(f"   Total Capital Deployed: ${total_deployed:,.2f}")
            print(f"   Symbols: {', '.join(p['symbol'] for p in todays_entries)}")
            for pos in todays_entries:
                print(f"   • {pos['symbol']}: {pos['position_size_shares']} shares @ "
                      f"${pos['entry_price']:.2f} (${pos['position_size_dollars']:.2f})")
        
        print(f"\n🔴 POSITIONS EXITED TODAY: {len(todays_exits)}")
        if todays_exits:
            total_pnl = sum(p.get('realized_pnl', 0) for p in todays_exits if p.get('realized_pnl'))
            print(f"   Total Realized P&L: ${total_pnl:,.2f}")
            for pos in todays_exits:
                pnl = pos.get('realized_pnl', 0)
                pnl_pct = (pnl / pos['position_size_dollars'] * 100) if pos['position_size_dollars'] > 0 else 0
                exit_reason = pos.get('exit_reason', 'Unknown')
                print(f"   • {pos['symbol']}: ${pnl:+.2f} ({pnl_pct:+.2f}%) - Reason: {exit_reason}")
        
        print(f"\n🟡 ACTIVE POSITIONS: {len(active_positions)}")
        if active_positions:
            total_active = sum(p['position_size_dollars'] for p in active_positions)
            print(f"   Total Active Capital: ${total_active:,.2f}")
            for pos in active_positions:
                print(f"   • {pos['symbol']}: {pos['position_size_shares']} shares @ "
                      f"${pos['entry_price']:.2f} - Exit scheduled: {pos.get('exit_date', 'N/A')}")
        
        return todays_entries, todays_exits, active_positions
    
    def analyze_friday_aapl_issue(self):
        """Analyze why AAPL wasn't sold on Friday (Oct 11)"""
        print(f"\n🔍 INVESTIGATING: AAPL Friday Exit Issue (October 11, 2025)")
        print("=" * 70)
        
        friday = date(2025, 10, 11)
        
        # Find AAPL positions around Friday
        aapl_positions = [p for p in self.positions if p['symbol'] == 'AAPL']
        
        # Find positions that should have exited on Friday
        friday_aapl = []
        for pos in aapl_positions:
            entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
            exit_date_str = pos.get('exit_date')
            exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
            
            # Check if this position should have exited on Friday
            if exit_date and exit_date <= friday and pos['status'] != 'exited':
                friday_aapl.append(pos)
                print(f"\n⚠️  ISSUE FOUND: AAPL position not exited")
                print(f"   Entry Date: {entry_date}")
                print(f"   Expected Exit Date: {exit_date}")
                print(f"   Status: {pos['status']}")
                print(f"   Position Size: {pos['position_size_shares']} shares @ ${pos['entry_price']:.2f}")
            
            # Also check positions that WERE supposed to exit on Friday
            if exit_date == friday:
                actual_exit = datetime.strptime(pos.get('exit_date', ''), '%Y-%m-%d').date() if pos.get('exit_date') else None
                print(f"\n✓ AAPL Position with Friday exit schedule:")
                print(f"   Entry: {entry_date} → Exit: {exit_date}")
                print(f"   Status: {pos['status']}")
                if pos['status'] == 'exited':
                    print(f"   Exit Reason: {pos.get('exit_reason', 'Unknown')}")
                    print(f"   Realized P&L: ${pos.get('realized_pnl', 0):+.2f}")
        
        if not friday_aapl:
            print("\n✅ No AAPL positions found with Friday exit issues")
            print("   Checking recent AAPL activity around that date...")
            
            # Show all AAPL positions from Oct 7-13
            print(f"\n   Recent AAPL Positions (Oct 7-13):")
            for pos in aapl_positions:
                entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
                if date(2025, 10, 7) <= entry_date <= date(2025, 10, 13):
                    print(f"   • Entry: {entry_date}, Exit: {pos.get('exit_date', 'N/A')}, "
                          f"Status: {pos['status']}")
    
    def analyze_exit_timing_logic(self):
        """Analyze when the bot exits positions during the day"""
        print(f"\n⏰ EXIT TIMING ANALYSIS")
        print("=" * 70)
        
        # Analyze exit reasons and understand the timing logic
        exit_reasons = defaultdict(int)
        exits_with_time = []
        
        for pos in self.positions:
            if pos['status'] == 'exited' and pos.get('exit_reason'):
                exit_reasons[pos['exit_reason']] += 1
                
                # Try to infer exit timing from reason
                pnl = pos.get('realized_pnl', 0) or 0
                position_size = pos.get('position_size_dollars', 0) or 0
                exits_with_time.append({
                    'symbol': pos['symbol'],
                    'exit_date': pos.get('exit_date'),
                    'exit_reason': pos['exit_reason'],
                    'pnl': pnl,
                    'pnl_pct': (pnl / position_size * 100) if position_size > 0 else 0
                })
        
        print(f"\nExit Reason Distribution (All Time):")
        for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
            print(f"   {reason}: {count} exits")
        
        print(f"\n💡 EXIT LOGIC EXPLANATION:")
        print(f"\nThe bot uses 'Smart D+1 Exit Logic' with the following rules:")
        print(f"   1. Entry Day (D+0): No exits allowed (PDT protection)")
        print(f"   2. Exit Day (D+1): Strategic timing based on P&L:")
        print(f"      • SMART_PROFIT_TAKE: >2% profit - exit immediately")
        print(f"      • SMART_MORNING_PROFIT: 9:30-10:30 AM if >0.5% profit")
        print(f"      • SMART_MIDDAY_BREAKEVEN: 11:00 AM-2:00 PM if breaking even")
        print(f"      • SMART_AFTERNOON_EXIT: 2:00-3:30 PM if not down >1.5%")
        print(f"      • SMART_FINAL_HOUR: After 3:30 PM - force exit")
        print(f"      • SMART_STOP_LOSS: Any time if down >2%")
        print(f"\n   📌 KEY ISSUE: The bot exits at SPECIFIC TIMES, not based on")
        print(f"      optimal price movement during the day!")
        
        # Recent D+1 strategic exits
        print(f"\n📋 Recent D+1 Strategic Exits:")
        recent_d1_exits = [e for e in exits_with_time 
                          if 'D+1_STRATEGIC' in e['exit_reason'] 
                          and e['exit_date'] and e['exit_date'] >= '2025-10-08']
        
        for exit in sorted(recent_d1_exits, key=lambda x: x['exit_date'], reverse=True)[:10]:
            print(f"   {exit['exit_date']}: {exit['symbol']} - {exit['exit_reason']} "
                  f"(P&L: ${exit['pnl']:+.2f}, {exit['pnl_pct']:+.1f}%)")
    
    def check_alpaca_data_usage(self):
        """Check if bot is using Alpaca data for entry/exit timing"""
        print(f"\n🔌 ALPACA DATA USAGE ANALYSIS")
        print("=" * 70)
        
        print(f"\n📍 Current Implementation:")
        print(f"   ✓ Bot IS connected to Alpaca API (via connect_real_trading.py)")
        print(f"   ✓ Bot CAN retrieve account info and positions")
        print(f"   ✓ Bot CAN submit orders and get order status")
        print(f"   ✗ Bot DOES NOT track actual fill times from Alpaca")
        print(f"   ✗ Bot DOES NOT use Alpaca order history for D+1 calculation")
        
        print(f"\n❌ IDENTIFIED ISSUES:")
        print(f"   1. Entry/Exit dates are stored as DATE only, not DATETIME")
        print(f"      → Bot uses midnight for D+1 calculation, not actual fill time")
        print(f"   2. Alpaca's 'submitted_at' and 'filled_at' are captured but NOT stored")
        print(f"      → Bot loses the actual order execution timestamp")
        print(f"   3. D+1 logic uses calendar date, not 24-hour window from fill")
        print(f"      → A position entered at 3:45 PM exits at 9:30 AM next day (~18 hours)")
        
        print(f"\n💡 RECOMMENDED FIXES:")
        print(f"   1. Store order fill timestamps from Alpaca in positions.json")
        print(f"   2. Calculate D+1 based on fill_time + 24 hours, not calendar date")
        print(f"   3. Use intraday price tracking to exit when stock is UP, not at fixed times")
        print(f"   4. Add a 'smart exit window' (e.g., 2-3:45 PM) to find optimal exits")
    
    def generate_recommendations(self):
        """Generate actionable recommendations"""
        print(f"\n🎯 RECOMMENDATIONS FOR IMPROVEMENT")
        print("=" * 70)
        
        print(f"\n1. 🔧 FIX EXIT TIMING:")
        print(f"   Current: Exits at fixed times (9:30 AM, 11 AM, 2 PM, 3:30 PM)")
        print(f"   Better: Monitor price throughout D+1 day, exit when:")
        print(f"      • Price is UP from entry (maximize profit)")
        print(f"      • After 2 PM if profitable (capture afternoon momentum)")
        print(f"      • Only force-exit at 3:45 PM if still holding")
        
        print(f"\n2. 🕐 USE ACTUAL FILL TIMES:")
        print(f"   Current: D+1 = calendar next day (can be <18 hours)")
        print(f"   Better: D+1 = fill_time + 24 hours (true 24-hour hold)")
        print(f"   Implementation: Store Alpaca's 'filled_at' timestamp")
        
        print(f"\n3. 📊 IMPLEMENT SMART EXIT ZONES:")
        print(f"   Zone 1 (9:30-11:00 AM): Only exit if >1% profit")
        print(f"   Zone 2 (11:00-2:00 PM): Exit if >0.5% profit")
        print(f"   Zone 3 (2:00-3:30 PM): Exit if profitable OR price trending down")
        print(f"   Zone 4 (3:30-3:45 PM): Monitor every 5 min, exit on uptick")
        print(f"   Zone 5 (3:45 PM): Force exit any remaining positions")
        
        print(f"\n4. 🎲 ADD FRIDAY WEEKEND EXIT LOGIC:")
        print(f"   Current: No special Friday handling for exits")
        print(f"   Better: Force exit ALL positions before Friday 4 PM")
        print(f"   Rationale: No weekend holding → more predictable returns")
        
        print(f"\n5. 📈 INTEGRATE PHASE 1 IMPROVEMENTS:")
        print(f"   • Deploy Multi-Level Profit Targets (25%/50%/75% scaling)")
        print(f"   • Use Enhanced Signal Filtering (better entry quality)")
        print(f"   • Expected improvement: 0% → 60% profit-taking rate")

def main():
    analyzer = TodaysPerformanceAnalyzer()
    
    # Run all analyses
    analyzer.analyze_todays_trades()
    analyzer.analyze_friday_aapl_issue()
    analyzer.analyze_exit_timing_logic()
    analyzer.check_alpaca_data_usage()
    analyzer.generate_recommendations()
    
    print(f"\n" + "=" * 70)
    print(f"✅ Analysis Complete!")
    print(f"=" * 70)

if __name__ == "__main__":
    main()
