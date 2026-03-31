#!/usr/bin/env python3
"""
PDT Violation & No Trades Fix Script
=====================================

Issues Found:
1. Multiple same-day entries on Sept 23 (AAPL entered 11 times in one day)
2. No trades on Oct 3 - breakout filter returning 0 symbols (vol_spike=nan, prior_high_notna=False)
3. _has_same_day_activity() not being properly enforced

Root Causes:
- Breakout filter needs sufficient historical data (20-day lookback) but showing NaN
- Same-day activity check happens AFTER trade execution, not before
- Need strict D+1 enforcement: Entry Day 0, Exit Day 1 ONLY

Fixes:
1. Move PDT check BEFORE trade execution in _execute_signal()
2. Add hard block on same-day entries (check before signal processing)
3. Fix breakout filter data requirements (check for sufficient history)
4. Add explicit D+1 validation (no same-day exits allowed)
"""

import json
from datetime import datetime, date

# Analyze current positions for PDT violations
print("=" * 80)
print("ANALYZING PDT VIOLATIONS IN positions.json")
print("=" * 80)

with open('positions.json', 'r') as f:
    positions = json.load(f)

# Group by date and symbol
violations = {}
for pos in positions:
    entry_date = pos['entry_date']
    symbol = pos['symbol']
    entry_ts = pos.get('ai_signal', {}).get('timestamp', '')
    
    key = f"{entry_date}_{symbol}"
    if key not in violations:
        violations[key] = []
    violations[key].append({
        'entry_time': entry_ts,
        'exit_reason': pos.get('exit_reason', 'N/A'),
        'exit_date': pos.get('exit_date', 'N/A')
    })

print("\nSAME-DAY ENTRY VIOLATIONS (Multiple entries same symbol same day):")
print("-" * 80)
pdt_count = 0
for key, entries in violations.items():
    if len(entries) > 1:
        parts = key.split('_')
        entry_date = parts[0]
        symbol = '_'.join(parts[1:])
        print(f"\n{symbol} on {entry_date}: {len(entries)} entries")
        for i, entry in enumerate(entries, 1):
            print(f"  {i}. Entry: {entry['entry_time']}, Exit: {entry['exit_reason']}")
        pdt_count += 1

print(f"\n⚠️ TOTAL PDT VIOLATIONS: {pdt_count} symbol-days with multiple entries")

print("\n" + "=" * 80)
print("CHECKING DATA AVAILABILITY FOR BREAKOUT FILTER")
print("=" * 80)

# The log shows all stocks have vol_spike=nan and prior_high_notna=False
# This means insufficient historical data for breakout calculations
print("""
LOG ANALYSIS - Oct 3 Breakout Filter Failures:
- AMD: vol_spike=nan (need>=1.05), price_breakout=nan, prior_high_notna=False
- NVDA: vol_spike=nan (need>=1.05), price_breakout=nan, prior_high_notna=False
- QCOM: vol_spike=1.00 (need>=1.05), price_breakout=0.0158, prior_high_notna=True ⭐ CLOSE!

ROOT CAUSE: Breakout filter requires 20-day rolling average for volume comparison
but data loader not providing enough historical bars.

FIX REQUIRED:
1. Ensure data loader fetches at least 30 days of history (20 + 10 buffer)
2. Add fallback if insufficient data: skip breakout filter or lower requirements
3. Log warning when data insufficient for proper analysis
""")

print("\n" + "=" * 80)
print("REQUIRED CODE CHANGES")
print("=" * 80)

changes = """
CRITICAL CHANGES NEEDED:

1. traders/short_cycle_trader.py - _execute_signal() method (around line 1200):
   BEFORE: No PDT check until after execution
   AFTER: Add PDT check at START of method:
   
   if self._has_same_day_activity(signal.symbol):
       self.logger.warning(f"❌ {signal.symbol}: Blocked - same-day activity (PDT protection)")
       return

2. traders/short_cycle_trader.py - _has_same_day_activity() method (around line 1337):
   CURRENT: Checks entry_date == today for same-day entries
   ISSUE: This allows MULTIPLE entries same day (AAPL had 11!)
   FIX: Return True if ANY position exists for this symbol today:
   
   same_day_entries = sum(1 for p in self.positions 
                          if p.symbol == symbol and p.entry_date == today)
   if same_day_entries > 0:
       return True  # Block ANY additional entries same day

3. pre_filter.py - RelaxedFilter or data loading (check min_rows requirement):
   CURRENT: Requires 30 rows minimum
   ISSUE: Need at least 40 rows for 20-day breakout window + buffer
   FIX: Increase min_rows to 40 or add conditional breakout filter skip

4. traders/short_cycle_trader.py - Exit logic:
   CURRENT: Allows same-day exits (FAST_EXIT on entry day)
   ISSUE: Creates day trades
   FIX: Block all exits until exit_date (D+1):
   
   if position.entry_date == dt.date.today():
       self.logger.debug(f"⏳ {position.symbol}: No exit allowed until D+1 ({position.exit_date})")
       continue  # Skip to next position

5. config settings - Breakout filter relaxation:
   Add fallback mode when no breakouts found after full adaptive relaxation:
   - Use top momentum-ranked symbols without breakout gate
   - This is already implemented but needs data to work

TESTING CHECKLIST:
□ Verify no same-day entries possible for same symbol
□ Verify no same-day exits (only D+1 exits)
□ Check logs show PDT protection blocks
□ Validate breakout filter gets sufficient data
□ Test Oct 3 scenario produces trades with fixes
"""

print(changes)

print("\n" + "=" * 80)
print("IMMEDIATE ACTIONS")
print("=" * 80)
print("""
1. Edit traders/short_cycle_trader.py:
   - Add PDT check at top of _execute_signal()
   - Fix _has_same_day_activity() to block ALL same-day re-entries
   - Add exit_date validation to prevent same-day exits
   
2. Edit pre_filter.py or data loader:
   - Increase historical data fetch to 40+ days
   - Add warning when insufficient data for breakout filter
   
3. Test with simulation:
   - Run with Oct 3 data
   - Verify trades execute
   - Check no PDT violations possible

4. Monitor logs for:
   - "Blocked - same-day activity (PDT protection)" messages
   - "No exit allowed until D+1" messages  
   - Breakout filter getting valid vol_spike calculations
""")

print("\n✅ Analysis complete. Review code changes above and implement.")
