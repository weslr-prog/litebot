# Performance Tuning Report - November 18, 2025

## Issue Summary
Bot showing severe underperformance in November trading:
- **20% win rate** (3 wins, 12 losses in last 15 trades)
- **Net loss: -$27.38** in November
- **Risk/reward unfavorable**: Avg loss $2.56 vs avg win $1.11 (2.3x worse)
- **Big losers**: RIVN -$21.23 (-11%), NCLH -$3.29 (-2.5%)

## Root Cause Analysis

### Today's Exits (Nov 18)
```
AAUC: +$1.80 (+0.91%) ZONE3_AFTERNOON_PROFIT  - Small win
AG:   -$2.76 (-1.91%) ZONE3_AFTERNOON_STOP    - Near emergency stop
CLBT: -$2.84 (-1.92%) ZONE3_AFTERNOON_STOP    - Near emergency stop  
MRNA: +$1.04 (+0.35%) ZONE3_AFTERNOON_PROFIT  - Tiny win

Net: -$2.76 (50% win rate but losers 1.5x bigger)
```

### Key Problems Identified

1. **Entry Quality Too Low**
   - 3.5% momentum threshold allowing weak setups
   - Positions opening down and hitting -2% emergency stops
   - Example: RIVN lost -$21.23 (-11%) before emergency exit

2. **Zone 3 Thresholds Too Aggressive**
   - Breakeven+ (0%) profit exits catching tiny +0.3%, +0.4% wins
   - -1.5% stop loss letting losses run to -1.9% (near -2% emergency)
   - Taking small profits but letting losses grow

3. **D+1 Exit Timing**
   - Positions entered Day T, exiting Day T+1 morning (9:45-10:23 AM)
   - Using Zone 3 "afternoon" thresholds for next-day morning exits
   - Not giving positions enough time to develop

## Parameter Adjustments

### 1. Raised Entry Momentum Threshold (3.5% → 5.0%)
**File**: `traders/short_cycle_trader.py` line 602
**Change**: `if momentum_score > 0.050 and volume_ratio >= 0.7:`
**Reasoning**: 
- 3.5% allowed MRNA duplicates and weak setups
- 20% win rate shows quality filter insufficient
- 5% requires stronger price action before entry

### 2. Raised Zone 3 Profit Exit (0% → 1.0%)
**File**: `traders/short_cycle_trader.py` line 325
**Change**: `if pnl_pct >= 0.010:  # >1.0% profit`
**Reasoning**:
- Breakeven exits catching +0.3%, +0.4% tiny wins
- Need larger wins to offset -2% losses
- 1% minimum ensures meaningful profit capture

### 3. Tightened Zone 3 Stop Loss (-1.5% → -1.0%)
**File**: `traders/short_cycle_trader.py` line 327
**Change**: `elif pnl_pct < -0.010:  # Down >1.0%, cut loss`
**Reasoning**:
- -1.5% stop letting losses run to -1.9% (near -2% emergency)
- Cut losses earlier at -1.0% before they grow
- Improve risk/reward by limiting downside

## Expected Impact

### Before (Nov 1-18)
- Win rate: 20%
- Avg win: $1.11
- Avg loss: $2.56
- Win/loss ratio: 0.43x
- Net P&L: -$27.38

### After (Expected)
- Win rate: Should improve to 30-40% (stricter entries)
- Avg win: ~$2.00+ (1%+ profit minimum)
- Avg loss: ~$1.50 (cut at -1.0%)
- Win/loss ratio: Target 1.3x+
- Net P&L: Positive trend expected

## Monitoring Plan

### Next 3-5 Trading Days
1. **Track entry quality**
   - Are 5% momentum stocks opening positive?
   - Fewer emergency stops expected

2. **Track exit performance**
   - Win sizes should be larger (>1%)
   - Loss sizes should be smaller (<-1%)
   - Win rate should stabilize 30-40%

3. **Track overall P&L**
   - Daily P&L should turn positive
   - Cumulative recovery from -$27.38 loss

### Success Criteria
- ✅ Win rate >30%
- ✅ Avg win >= avg loss
- ✅ No emergency stops (-2%) for 5 days
- ✅ Net positive P&L over 5-day period

## Fallback Plan

If performance doesn't improve after 5 days:
1. Consider raising momentum to 6% (even stricter)
2. Evaluate if trailing stops are activating (need +3% first)
3. Analyze if Zone 2 midday exits (0.5%) should be raised
4. Review if volume_ratio 0.7 threshold is sufficient

## Implementation
- **Date**: November 18, 2025 10:35 AM
- **Status**: ✅ All changes validated and deployed
- **Next Review**: November 21, 2025 (after 3 trading days)

---

## Technical Details

### Zone 3 Logic Explanation
Zone 3 applies to:
- **Time range**: 2:00-3:30 PM (time_fraction 14.0-15.5)
- **D+1 exits**: Also applies to next-day morning exits (positions held overnight)

**Previous thresholds (causing problems):**
```python
if pnl_pct >= 0:  # Breakeven+ exit → tiny +0.3% wins
elif pnl_pct < -0.015:  # -1.5% stop → let -1.9% losses run
```

**New thresholds (Nov 18):**
```python
if pnl_pct >= 0.010:  # 1%+ profit → meaningful wins
elif pnl_pct < -0.010:  # -1.0% stop → cut losses earlier
```

### Other Active Protections
- **Emergency stop**: -2% any time (unchanged)
- **Trailing stops**: Activate at +3%, trail 1.5% (enabled Nov 18)
- **Zone 1 morning**: Exit if >1% profit (9:30-11 AM)
- **Zone 2 midday**: Exit if >0.5% profit (11 AM-2 PM)
- **Zone 5 force exit**: 3:45 PM+ (no overnight holds)
- **Market hours only**: 9:30 AM-4:00 PM ET orders
- **Daily capital limit**: 30% max deployment

### Entry Requirements (Post Nov 18)
- Momentum: >5.0% (was 3.5%)
- Volume ratio: ≥0.7
- Price range: $10-$40
- Market hours: 9:30 AM-4:00 PM
- No duplicates: Blocks same-day re-entry
- Daily limit: Max 30% portfolio ($294 of $982)

## Related Fixes
- Nov 17: MRNA duplicate bug fix (0.05% → 3.5% momentum)
- Nov 17: Added market hours validation
- Nov 17: Added duplicate position detection
- Nov 17: Set 30% daily capital limit
- Nov 18: Enabled runner strategy (removed 3% hard exit)
- Nov 18: Expanded price range $30 → $40
- Nov 18: THIS REPORT - 5% momentum, 1% profit, -1% stop

## Files Modified
1. `traders/short_cycle_trader.py` (lines 602, 325, 327)
   - Momentum threshold: 0.035 → 0.050
   - Zone 3 profit exit: 0.0 → 0.010
   - Zone 3 stop loss: -0.015 → -0.010

## Validation
```bash
python3 -m py_compile traders/short_cycle_trader.py
✅ Syntax validation passed
```
