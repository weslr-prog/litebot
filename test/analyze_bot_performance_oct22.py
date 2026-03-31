#!/usr/bin/env python3
"""
Comprehensive Bot Performance Analysis for October 22, 2025
Analyzes trading decisions, D+1 logic violations, and provides improvement recommendations
"""

import json
from datetime import datetime, date
from typing import Dict, List, Tuple
import os

def load_positions():
    """Load positions.json"""
    with open('positions.json', 'r') as f:
        return json.load(f)

def load_trade_explanations():
    """Load trade explanations"""
    with open('logs/trade_explanations_2025-10-22.json', 'r') as f:
        lines = f.readlines()
        return [json.loads(line) for line in lines]

def analyze_crm_violation():
    """Analyze the CRM double-buy PDT violation"""
    print("=" * 80)
    print("🚨 CRM PDT RULE VIOLATION ANALYSIS")
    print("=" * 80)
    
    positions = load_positions()
    crm_positions = [p for p in positions if p['symbol'] == 'CRM']
    
    print(f"\n📊 Found {len(crm_positions)} CRM position records in positions.json:\n")
    
    for i, pos in enumerate(crm_positions, 1):
        print(f"Position #{i}:")
        print(f"  Entry Date: {pos['entry_date']}")
        print(f"  Exit Date: {pos['exit_date']}")
        print(f"  Entry Price: ${pos['entry_price']:.2f}")
        print(f"  Shares: {pos['position_size_shares']}")
        print(f"  Status: {pos['status']}")
        print(f"  Entry Timestamp: {pos.get('entry_timestamp', 'N/A')}")
        print(f"  Exit Reason: {pos.get('exit_reason', 'N/A')}")
        pnl = pos.get('realized_pnl')
        if pnl is not None:
            print(f"  Realized P&L: ${pnl:.2f}")
        else:
            print(f"  Realized P&L: N/A (not exited yet)")
        print()
    
    print("\n🔍 ACTUAL ALPACA ORDERS (from API query):")
    print("  Oct 21, 17:37: BUY 23 shares @ $263.97")
    print("  Oct 22, 13:52: BUY 22 shares @ $259.41")
    print("  Oct 22, 15:32: SELL 45 shares @ $259.79")
    
    print("\n❌ VIOLATION IDENTIFIED:")
    print("  • Bot bought CRM on Oct 21 (23 shares) - scheduled for D+1 exit on Oct 22")
    print("  • Bot bought CRM AGAIN on Oct 22 (22 shares) - scheduled for D+1 exit on Oct 23")
    print("  • Bot sold ALL 45 shares on Oct 22 - violating the D+1 rule for the Oct 22 position")
    
    print("\n🔬 ROOT CAUSE ANALYSIS:")
    print("  1. POSITION TRACKING FAILURE:")
    print("     - The bot's self.positions array likely didn't properly track the Oct 21 position")
    print("     - When selecting new entries on Oct 22, CRM appeared as an 'available' symbol")
    print("     - No logic prevented re-buying a symbol that already has an active position")
    
    print("\n  2. EXIT AGGREGATION BUG:")
    print("     - D+1 exit logic triggered for Oct 21 position (correct)")
    print("     - Exit engine sold ALL shares (45) instead of just the Oct 21 position (23)")
    print("     - This violated the D+1 rule for the Oct 22 position (should exit Oct 23)")
    
    print("\n  3. SYNC LOGIC FLAW:")
    print("     - _sync_positions_with_portfolio() detected 22-share Oct 22 buy")
    print("     - Created a position tracker for it")
    print("     - BUT the exit logic summed ALL CRM shares and sold them together")

def analyze_daily_performance():
    """Analyze overall trading performance"""
    print("\n" + "=" * 80)
    print("📊 DAILY PERFORMANCE SUMMARY - October 22, 2025")
    print("=" * 80)
    
    trades = load_trade_explanations()
    
    exits = [t for t in trades if t['action'] == 'EXIT']
    entries = [t for t in trades if t['action'] == 'ENTRY']
    
    print(f"\n🔄 TRADES EXECUTED:")
    print(f"  Exits: {len(exits)}")
    print(f"  Entries: {len(entries)}")
    
    print(f"\n💰 EXIT PERFORMANCE (D+1 exits from Oct 21):")
    print(f"{'Symbol':<8} {'Entry':<10} {'Exit':<10} {'Return':<8} {'P&L':<12} {'Reason':<25}")
    print("-" * 80)
    
    total_pnl = 0
    winners = 0
    losers = 0
    
    for trade in exits:
        if 'performance' in trade:
            perf = trade['performance']
            pnl = perf.get('realized_pnl', 0)
            total_pnl += pnl
            
            if pnl > 0:
                winners += 1
                emoji = "✅"
            else:
                losers += 1
                emoji = "❌"
            
            print(f"{emoji} {trade['symbol']:<6} "
                  f"${perf['entry_price']:<9.2f} "
                  f"${perf['exit_price']:<9.2f} "
                  f"{perf['return_pct']:>6.2f}% "
                  f"${pnl:>10.2f} "
                  f"{trade['exit_reason']:<25}")
    
    print("-" * 80)
    print(f"{'TOTAL':<6} {'':19} {'':>6} ${total_pnl:>10.2f}")
    
    win_rate = (winners / len(exits) * 100) if exits else 0
    
    print(f"\n📈 STATISTICS:")
    print(f"  Win Rate: {win_rate:.1f}% ({winners}/{len(exits)})")
    print(f"  Average Winner: ${sum(t['performance']['realized_pnl'] for t in exits if t['performance']['realized_pnl'] > 0) / winners if winners else 0:.2f}")
    print(f"  Average Loser: ${sum(t['performance']['realized_pnl'] for t in exits if t['performance']['realized_pnl'] < 0) / losers if losers else 0:.2f}")
    
    print(f"\n📉 MAJOR LOSSES:")
    big_losses = sorted([t for t in exits if t['performance']['realized_pnl'] < -100], 
                       key=lambda x: x['performance']['realized_pnl'])
    for trade in big_losses:
        perf = trade['performance']
        print(f"  • {trade['symbol']}: ${perf['realized_pnl']:.2f} ({perf['return_pct']:.2f}%) - {trade['exit_reason']}")
    
    print(f"\n📊 NEW ENTRIES FOR OCT 23:")
    for trade in entries:
        if 'position_sizing' in trade and 'ai_decision' in trade:
            sizing = trade['position_sizing']
            ai = trade['ai_decision']
            features = ai.get('features_used', {})
            momentum = features.get('momentum_score', 0)
            
            # Try to get entry price from various sources
            entry_price = None
            if 'entry_price' in ai:
                entry_price = ai['entry_price']
            elif 'value' in sizing and 'shares' in sizing and sizing['shares'] > 0:
                entry_price = sizing['value'] / sizing['shares']
            
            if entry_price:
                print(f"  • {trade['symbol']}: {sizing['shares']} shares @ ${entry_price:.2f} "
                      f"(confidence: {ai['confidence']:.2f}, momentum: {momentum:.3f})")
            else:
                print(f"  • {trade['symbol']}: {sizing['shares']} shares "
                      f"(confidence: {ai['confidence']:.2f}, momentum: {momentum:.3f})")

def analyze_stock_selection():
    """Analyze what stocks were selected and why"""
    print("\n" + "=" * 80)
    print("🎯 STOCK SELECTION ANALYSIS")
    print("=" * 80)
    
    # Get yesterday's entries
    try:
        with open('logs/trade_explanations_2025-10-21.json', 'r') as f:
            lines = f.readlines()
            yesterday_trades = [json.loads(line) for line in lines]
        
        yesterday_entries = [t for t in yesterday_trades if t['action'] == 'ENTRY']
        
        print(f"\n📅 YESTERDAY (Oct 21) - STOCKS SELECTED:")
        for trade in yesterday_entries:
            print(f"  • {trade['symbol']}")
        
    except FileNotFoundError:
        print("\n⚠️ No trade log found for Oct 21")
    
    # Today's entries
    trades = load_trade_explanations()
    today_entries = [t for t in trades if t['action'] == 'ENTRY']
    
    print(f"\n📅 TODAY (Oct 22) - STOCKS SELECTED:")
    for trade in today_entries:
        print(f"  • {trade['symbol']}")
    
    print(f"\n🔄 OVERLAP ANALYSIS:")
    yesterday_symbols = {t['symbol'] for t in yesterday_entries} if 'yesterday_entries' in locals() else set()
    today_symbols = {t['symbol'] for t in today_entries}
    overlap = yesterday_symbols & today_symbols
    
    if overlap:
        print(f"  ⚠️ REPEATED SYMBOLS: {', '.join(overlap)}")
        print(f"     This indicates potential D+1 rule violation!")
    else:
        print(f"  ✅ No overlap - proper D+1 separation")

def analyze_prefilter_results():
    """Check what PreFilter recommended today"""
    print("\n" + "=" * 80)
    print("🔍 PREFILTER UNIVERSE ANALYSIS")
    print("=" * 80)
    
    # Check if watchlist was generated
    watchlist_files = [f for f in os.listdir('logs') if 'watchlist_2025-10-22' in f or 'watchlist_20251022' in f]
    
    if watchlist_files:
        latest = max(watchlist_files)
        with open(f'logs/{latest}', 'r') as f:
            watchlist = json.load(f)
        
        print(f"\n📋 PREFILTER CANDIDATES (from {latest}):")
        if isinstance(watchlist, list):
            print(f"  Total: {len(watchlist)} stocks")
            for symbol in watchlist:
                print(f"    • {symbol}")
        elif isinstance(watchlist, dict) and 'symbols' in watchlist:
            symbols = watchlist['symbols']
            print(f"  Total: {len(symbols)} stocks")
            for symbol in symbols:
                print(f"    • {symbol}")
    else:
        print("\n⚠️ No watchlist found for Oct 22")
        print("  Bot may have used fallback universe or cached data")

def provide_recommendations():
    """Provide improvement recommendations"""
    print("\n" + "=" * 80)
    print("💡 RECOMMENDED IMPROVEMENTS")
    print("=" * 80)
    
    print("""
🔧 CRITICAL FIXES NEEDED:

1. PREVENT SAME-SYMBOL RE-ENTRY (D+1 Rule Enforcement)
   Priority: 🔴 CRITICAL
   
   Problem: Bot bought CRM on consecutive days, violating D+1 logic
   
   Solution: Add pre-entry validation in signal selection:
   
   ```python
   def _validate_entry_candidates(self, candidates: List[str]) -> List[str]:
       '''Remove any symbols that already have active positions'''
       active_symbols = {pos.symbol for pos in self.positions 
                        if pos.status == PositionStatus.ENTERED}
       
       valid = [sym for sym in candidates if sym not in active_symbols]
       
       filtered = set(candidates) - set(valid)
       if filtered:
           self.logger.warning(
               f"⚠️ Filtered out {len(filtered)} symbols with active positions: {filtered}"
           )
       
       return valid
   ```

2. FIX EXIT AGGREGATION BUG
   Priority: 🔴 CRITICAL
   
   Problem: Exit logic sold ALL shares of CRM (45) instead of just the D+1 position (23)
   
   Solution: Exit only the shares associated with the specific position object:
   
   ```python
   def _exit_position(self, position: ShortCyclePosition):
       '''Exit a specific position by its tracked share count'''
       shares_to_exit = position.position_size_shares  # NOT portfolio total!
       
       # Execute sell order for THIS position's shares only
       self.execution_engine.sell(
           symbol=position.symbol,
           shares=shares_to_exit,
           order_tag=f"D+1_EXIT_{position.entry_date}"
       )
   ```

3. IMPROVE POSITION SYNC LOGIC
   Priority: 🟡 HIGH
   
   Problem: _sync_positions_with_portfolio() can create duplicate trackers
   
   Solution: Check if position already tracked before creating new one:
   
   ```python
   # Before creating new position tracker:
   existing = [p for p in self.positions 
              if p.symbol == symbol_key and p.status == PositionStatus.ENTERED]
   
   if existing:
       self.logger.info(f"Position for {symbol_key} already tracked, skipping")
       continue
   ```

4. ADD DAILY POSITION RECONCILIATION
   Priority: 🟡 HIGH
   
   Add a reconciliation check at start of each day:
   
   ```python
   def _reconcile_positions_at_open(self):
       '''Ensure position tracker matches broker reality'''
       broker_positions = self.execution_engine.get_positions()
       
       # Log any mismatches
       for pos in self.positions:
           if pos.status == PositionStatus.ENTERED:
               broker_qty = broker_positions.get(pos.symbol, {}).get('qty', 0)
               if broker_qty != pos.position_size_shares:
                   self.logger.error(
                       f"MISMATCH: {pos.symbol} tracked={pos.position_size_shares} "
                       f"broker={broker_qty}"
                   )
   ```

5. IMPROVE STOP LOSS DETECTION
   Priority: 🟢 MEDIUM
   
   Problem: NFLX and TSLA hit emergency stop losses (-7.6%, -2.5%)
   
   Recommendation: 
   - Review stop loss placement (currently too wide?)
   - Consider ATR-based dynamic stops
   - Add pre-market gap detection to avoid big losses on gaps

6. ENHANCE SIGNAL QUALITY
   Priority: 🟢 MEDIUM
   
   Problem: 25% win rate (2/8) is below target
   
   Recommendations:
   - Strengthen PreFilter's breakout detection (currently passing 0 stocks)
   - Add sector rotation analysis
   - Implement relative strength filtering
   - Consider market regime detection (trending vs choppy)

7. ADD PDT RULE VALIDATOR
   Priority: 🔴 CRITICAL
   
   Add a final safety check before ANY trade execution:
   
   ```python
   def _validate_pdt_compliance(self, symbol: str, action: str) -> bool:
       '''Ensure we don't violate PDT rules'''
       # For D+1 strategy: Never buy a symbol we already hold
       if action == 'BUY':
           active = [p for p in self.positions 
                    if p.symbol == symbol and p.status == PositionStatus.ENTERED]
           if active:
               self.logger.error(
                   f"PDT VIOLATION PREVENTED: Cannot buy {symbol}, "
                   f"already have {len(active)} active position(s)"
               )
               return False
       return True
   ```

📊 PERFORMANCE TARGETS:

Current Performance:
  • Win Rate: 25% (2/8)
  • Daily P&L: -$672
  • Biggest Loss: NFLX -$378 (-7.6%)

Target Performance (After Fixes):
  • Win Rate: 55-65%
  • Daily P&L: +$300-500 average
  • Max Single Loss: <$150 (1.5% of $10k)

⏱️ IMPLEMENTATION TIMELINE:

Day 1 (IMMEDIATE):
  • Fix #1: Prevent same-symbol re-entry
  • Fix #2: Fix exit aggregation
  • Fix #7: Add PDT validator

Day 2:
  • Fix #3: Improve position sync
  • Fix #4: Add reconciliation

Day 3-5:
  • Fix #5: Improve stop losses
  • Fix #6: Enhance signal quality

""")

def main():
    """Run complete analysis"""
    print("🤖 LiteBotX Performance Analysis - October 22, 2025")
    print("=" * 80)
    
    try:
        analyze_crm_violation()
        analyze_daily_performance()
        analyze_stock_selection()
        analyze_prefilter_results()
        provide_recommendations()
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        print("\n🎯 NEXT STEPS:")
        print("  1. Review the CRM violation root cause")
        print("  2. Implement the 7 critical fixes above")
        print("  3. Test with paper trading for 3-5 days")
        print("  4. Monitor win rate improvement")
        print("  5. Gradually increase position sizes as confidence builds")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
