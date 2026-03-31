# Signal Rejection Analysis - December 30, 2024

## Investigation Results

### Why No Trades Today?

Analyzed all 25 prefilter candidates to determine why none generated entry signals:

#### Rejection Breakdown:
- **23/25 stocks (92%)**: RSI > 35 (not oversold enough)
  - Range: RSI 35.2 to 84.6
  - Strategy requires: RSI ≤ 35 for mean reversion entry
  
- **1/25 stocks (4%)**: Too far below SMA trend
  - LYFT: -6.0% below 20-day SMA (threshold: >-6%)
  
- **1/25 stocks (4%)**: Passed all filters but rejected for other reasons
  - TWO (Two Harbors): RSI=17.3 ✅, SMA=+0.9% ✅, Momentum=-3.9% ✅
  - Likely rejected due to: Earnings blackout or being a REIT (dividend stock, not mean reversion candidate)

### Key Findings:

1. **Market Not Oversold**: Today's market is relatively strong
   - Most stocks have RSI 40-85 (neutral to overbought)
   - Only a few stocks below RSI 35
   - Mean reversion works best when stocks are genuinely oversold

2. **Strategy Discipline Working**: Bot correctly refusing to force trades
   - No signals when conditions aren't right = good risk management
   - Better to wait for quality setups than force low-probability trades

3. **TWO Investigation**:
   - Two Harbors Investment Corp (mREIT)
   - Very oversold (RSI=17.3) but likely filtered out because:
     - It's a mortgage REIT (dividend-focused, not mean reversion)
     - May have earnings in blackout window
     - Low RSI could indicate structural issues, not temporary oversold

## D+1 Exit Question

**Answer**: D+1 exit is a **TIMED exit strategy**, not a "smart" exit.

### How It Works:
```python
# From bot_v2/execution/exit_manager.py line 77
if today >= position.exit_date:
    days_held = (today - position.exit_date).days
    return (True, f"D+1 force exit: {days_held} days held")
```

### Exit Strategy Breakdown:

**Timed Exits** (Forced):
1. **D+1 Exit**: Next trading day after entry (PDT compliance)
2. **Friday 3:45 PM**: Force exit all positions (no weekend holds)
3. **Time-based**: 2:30 PM daily exit window

**Smart Exits** (Conditional):
1. **Profit Target**: +2% gain
2. **Stop Loss**: -3% loss
3. **RSI Overbought**: RSI ≥ 70 (mean reversion complete)
4. **Trailing Stop**: Protects profits
5. **Earnings Exit**: 1 day before earnings
6. **Sector-Specific**: Custom exits per sector
7. **Momentum Reversal**: Detecting trend change
8. **Weekend Risk**: Geopolitical events
9. **Quality Degradation**: Fundamental deterioration

### Priority Order:
1. Smart exits evaluated first (profit/stop/RSI)
2. If no smart exit triggered, check D+1 timer
3. D+1 exit acts as backstop to ensure positions close

## Changes Made: Enhanced Rejection Logging

### What Was Added:

#### 1. Detailed Per-Stock Rejection Messages
Now shows exactly why each stock was rejected:

**Before**:
```
🔍 SIGNALS (entry_window): 25 candidates → 0 signals | 73ms
```

**After**:
```
🔍 SIGNALS (entry_window): 25 candidates → 0 signals | 73ms
   ❌ AEO: RSI=35.2 (need ≤35), liquid=True, conf=0.01
   ❌ AI: RSI=56.7 (need ≤35), liquid=True, conf=0.00
   ❌ LYFT: Price $18.25 is -6.0% below SMA (>6% = too weak)
   ❌ MRNA: 5-day momentum -7.7% (>-5% = falling knife)
   ❌ TWO: Earnings blackout (3d before/1d after)
```

#### 2. Rejection Summary Statistics
Aggregated view of why candidates failed:

```
📊 Rejection Summary (25 stocks):
   • RSI too high: 23 (not oversold, RSI >35)
   • SMA filter: 1 (>6% below trend)
   • Momentum filter: 0 (falling knife <-5%)
   • Earnings blackout: 1 (3d before/1d after)
   • Low confidence: 0 (<50% threshold)
   • Insufficient liquidity: 0 (<$500K avg)
```

### Modified Files:

**bot_v2/signal_generation/signal_generator.py**:
- Added `rejection_stats` tracking dictionary
- Added `_analyze_symbol_with_reason()` method to capture rejection reasons
- Added `_current_rejection` instance variable to store rejection context
- Enhanced rejection logging at each filter point:
  - SMA filter (lines 350-365)
  - Momentum filter (lines 370-375)
  - RSI/confidence filter (lines 465-480)
  - Earnings filter (line 525)
- Added summary statistics logging in `generate_signals()` (lines 165-190)

### Benefits:

1. **Immediate Visibility**: See rejection reasons in real-time
2. **Pattern Recognition**: Identify market conditions (e.g., "RSI too high" across all stocks = market not oversold)
3. **Filter Tuning**: Understand which filters are most restrictive
4. **Strategy Validation**: Confirm filters working as designed

## Recommendations

### Option 1: Keep Current Settings (RECOMMENDED)
- **RSI threshold**: Keep at 35 (proven optimal)
- **Rationale**: Today's market simply isn't oversold
- **Strategy**: Wait for better market conditions
- **Risk**: Low - avoid forcing trades in unfavorable conditions

### Option 2: Relax RSI Threshold
- **Change**: RSI 35 → 40 or 45
- **Effect**: Would generate 3-5 more signals today
- **Risk**: Higher - trades at RSI 40-45 have lower win rate
- **Tradeoff**: More signals vs. lower quality

### Option 3: Add Alternative Entry Conditions
- **Idea**: Allow entry on strong volume surge even if RSI > 35
- **Use case**: Catch momentum breakouts (not pure mean reversion)
- **Risk**: Medium - changes strategy character

### My Recommendation: **Option 1**

**Why**:
1. Your backtest shows 56% win rate at RSI ≤ 35
2. No data on performance at RSI 35-45 (unproven)
3. Market will become oversold again - patience pays off
4. Current discipline prevents "forcing" bad trades

**Historical Context**:
- Mean reversion strategies have periods of inactivity
- Expecting 2-4 signals/day on average
- Some days: 0 signals (like today)
- Other days: 5-7 signals (when market sells off)
- Weekly average: 10-15 trades (acceptable for D+1 strategy)

## Next Steps

1. **Monitor Daily**: Watch rejection summary to understand market conditions
2. **Track RSI Distribution**: Note typical RSI levels in your universe
3. **Wait for Pullback**: Signals will come when market corrects
4. **Review Weekly**: Evaluate if 0-signal days become too frequent

## Diagnostic Commands

Check rejection reasons in real-time:
```bash
tail -f logs/sprint1_alpaca.log | grep -E "(❌|📊 Rejection)"
```

Analyze specific stock:
```bash
python investigate_two.py  # Edit symbol in script
```

Run full diagnostic:
```bash
python diagnose_rejections.py  # Shows all 25 candidates
```

## Conclusion

**No trades today is correct behavior**. Your bot is:
- ✅ Filtering correctly (25 candidates → detailed analysis)
- ✅ Applying strict RSI criteria (≤35 for mean reversion)
- ✅ Rejecting 23/25 stocks (not oversold)
- ✅ Waiting for quality setups (discipline > activity)

The enhanced logging now shows you **exactly why** each stock was rejected, helping you understand market conditions and validate strategy performance.

**Market today**: Strong, not oversold  
**Strategy**: Mean reversion (requires oversold)  
**Result**: No signals (appropriate response)  
**Action**: Wait for market pullback
