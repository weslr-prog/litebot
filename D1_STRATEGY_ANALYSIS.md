# D+1 Strategy Analysis for $1000 Portfolio
**Date**: December 4, 2025  
**Current Market**: Recovering from oversold (most stocks RSI > 35)

---

## Your Question Breakdown

You asked about:
1. **D+1 strategy** (buy today, sell tomorrow) - best approach?
2. **$250 position size** - kills diversification at $1K portfolio
3. **Is this a crazy market or is the bot too safe?**
4. **Should you adjust to be riskier or wait?**

---

## Current Bot Configuration

### Position Sizing
```
Portfolio: $1,000
Max per position: $200 (20%)
Max positions: 12 concurrent
Risk per trade: $20 (2% stop loss)
```

**Reality Check**:
- At $200/position, you can only hold **5 positions max** ($1000 ÷ $200)
- Your config says "12 concurrent" but that's impossible with $200 positions
- **This is a math error in your config**

### Profit Targets (Already Adjusted Nov 28)
```
Profit target: 4% (good for D+1)
Stop loss: 2% (tight - good)
Risk:Reward = 2:1 (excellent)
```

### Entry Filters (VERY STRICT)
```
1. RSI(7) ≤ 35 (oversold)
2. Price within 3% of 20-SMA (not falling knife)
3. 5-day momentum > -3% (bouncing, not crashing)
4. Dollar volume ≥ $500K (liquid)
5. Entry quality screening (momentum ≥ 4%)
```

---

## The Real Problem: Market vs Bot Safety

### Today's Market Scan Results

**12:00 PM Scan**:
- Universe: 262 stocks
- PreFilter passed: 103 stocks
- **Signals generated: 0**

**Why 0 signals?**

| Stock | RSI | SMA Distance | 5-Day Momentum | Result |
|-------|-----|--------------|----------------|--------|
| KO | 24.1 | -0.3% ✅ | 0.0% ❌ | Rejected: "Momentum too weak (0.0% < 4%)" |
| AFL | 42.7 ❌ | -1.5% | -0.8% | Not oversold anymore |
| ATO | 36.9 ❌ | -1.8% | -2.6% | Not oversold anymore |
| DTE | 33.0 ✅ | -1.9% | -2.3% | Likely rejected by momentum |
| ALL | 31.5 ✅ | -0.2% | ? | Didn't make it to logs |

**Conclusion**: This is NOT a crazy market. The market WAS oversold (Dec 2-3) but has been recovering today. Your bot is correctly identifying that stocks aren't setup for clean D+1 bounces right now.

---

## Is Your Bot Too Safe?

### SHORT ANSWER: **YES and NO**

**YES - Entry Quality Screening is TOO STRICT**:
```python
# Current code (intraday_quality_scorer.py):
if momentum_5d < 0.04:  # 4% momentum required
    return "REJECT: Momentum too weak"
```

**This is killing you!** KO had:
- RSI 24.1 (deeply oversold) ✅
- -0.3% from SMA (perfect mean reversion setup) ✅  
- 0.0% 5-day momentum (flat/stabilizing) ❌ **REJECTED**

**The 4% momentum requirement is for MOMENTUM strategies, not MEAN REVERSION**.

**NO - The Other Filters Are Actually Smart**:
- RSI ≤ 35: Catches true oversold
- 20-SMA tolerance: Prevents falling knives
- Liquidity check: Ensures you can exit

---

## D+1 Strategy: Best Approach for $1K

### Option 1: Current Setup (RECOMMENDED)
**Keep D+1, fix the entry quality screening**

```
Strategy: Mean Reversion D+1
Entry: RSI ≤ 35, near 20-SMA
Exit: Next day at 3:45 PM OR +4% target OR -2% stop
Position size: Smaller positions for diversification
```

**Math**:
```
$1000 ÷ $83 per position = 12 positions possible
$83 × 12 = $996 (full portfolio deployed)

Win rate: 56%
Avg win: +4%
Avg loss: -2%
Expected per trade: +1.36%

12 positions × 1.36% = +16.3% portfolio gain per cycle
BUT: You need 12 SIGNALS, not 0!
```

**Recommended Position Sizing**:
```python
max_position_dollars: 83.0  # $1000 ÷ 12 = $83 per position
max_positions_per_day: 12
```

### Option 2: Concentrated Bets (RISKIER)
**Fewer, larger positions**

```
Position size: $200-250 (your current setting)
Max positions: 4-5 concurrent
Win rate needed: 60%+ (to compensate for lower frequency)
```

**Math**:
```
4 positions × $200 = $800 deployed
4 × 1.36% EV = +5.4% per cycle

But if you lose 2/4 instead of 1/4:
2 wins × +4% × $200 = +$16
2 losses × -2% × $200 = -$8
Net: +$8 on $800 = +1% (worse than diversified)
```

**Conclusion**: Concentrated bets are WORSE for mean reversion because win rate is only 56%, not 70%+.

### Option 3: Hybrid (BEST FOR YOUR SITUATION)
**Use smaller positions, multiple strategies**

```
Mean Reversion: $50-80 positions (oversold stocks)
Gap & Go: $100-150 positions (morning momentum)
Combined frequency: 5-7 trades/week instead of 0-2
```

---

## Specific Recommendations

### IMMEDIATE FIXES (Do This Now)

#### 1. Fix Entry Quality Screening (5 minutes)
**File**: `intraday_quality_scorer.py`

Find this code:
```python
if momentum_5d < 0.04:  # 4% momentum required
    return "REJECT: Momentum too weak"
```

Change to:
```python
# For mean reversion, we want STABILIZING not SURGING
if momentum_5d < -0.02:  # Allow flat to slightly up (≥ -2%)
    return "REJECT: Still falling too fast"
```

**Why**: KO at 0.0% momentum is PERFECT for mean reversion. It's stabilized and ready to bounce. Requiring 4% momentum means you're buying AFTER the bounce (too late).

#### 2. Adjust Position Sizing (2 minutes)
**File**: `bot_v2/config/trading_config.py`

```python
# Current (wrong):
max_position_dollars: float = 200.0
max_positions_per_day: int = 12  # Impossible with $200 positions!

# Fixed (realistic):
max_position_dollars: float = 80.0  # $1000 ÷ 12 = $83
max_positions_per_day: int = 12
```

**OR if you prefer concentrated bets**:
```python
max_position_dollars: float = 200.0
max_positions_per_day: int = 5  # Realistic: $1000 ÷ $200 = 5
```

#### 3. Lower RSI Threshold Slightly (Optional, 1 minute)
**File**: `bot_v2/signal_generation/signal_generator.py`

```python
# Current:
rsi_entry_threshold = 35

# More aggressive:
rsi_entry_threshold = 40  # Catch earlier oversold
```

**Trade-off**: More signals, but slightly lower win rate (maybe 54% instead of 56%).

---

## Should You Wait or Adjust?

### WAIT if:
- ✅ You're comfortable with 1-2 trades per week
- ✅ Market is recovering (like today) - better setups coming Mon-Tue
- ✅ You want to preserve capital during choppy conditions

### ADJUST if:
- ❌ 0 trades in 5 days is unacceptable (compounding requires frequency)
- ❌ You want 5-7 trades/week to hit 3%+ weekly returns
- ❌ You're willing to accept 54-56% win rate instead of 60%+

---

## Market Conditions Reality Check

**This week's market**:
- Mon-Tue (Dec 2-3): Oversold selloff - GOOD setups
- Wed (Dec 4): Recovery bounce - stocks no longer oversold
- **Your bot was RIGHT to wait today**

**Historical pattern**:
- Mean reversion setups cluster around:
  - Monday/Tuesday (weekend fear)
  - After Fed announcements (overreaction)
  - Earnings gaps (one-day panic)

**Expecting 5-7 trades EVERY week is unrealistic**. More realistic:
- 3 trades/week average
- Some weeks: 7-10 trades (high volatility)
- Some weeks: 0-2 trades (trending market)

---

## Final Recommendation: HYBRID APPROACH

### Keep D+1 Strategy ✅
It's perfect for $1K + PDT restrictions.

### Make These Changes:

1. **Fix momentum filter** (most important):
   - Change from 4% requirement to -2% (allow stabilization)

2. **Reduce position size** for diversification:
   - $80 positions → 12 max positions
   - OR keep $200 but accept 4-5 positions max

3. **Wait for better setups**:
   - Don't force trades in recovering markets
   - Best setups: Mon-Tue after weekend or selloff days

4. **Consider adding Gap & Go** (optional):
   - Morning momentum for 9:45-10:30 AM
   - Increases frequency without lowering standards

### Expected Results After Fixes:

**Before (current)**:
- Trades/week: 0-1
- Weekly return: 0%

**After fixes**:
- Trades/week: 3-5 (realistic)
- Weekly return: 1.5-2.5% (with 56% WR)
- Good weeks: 4-6%
- Bad weeks: 0% or small loss

---

## Bottom Line

**Your bot is NOT playing it too safe - it's working correctly!**

The problem is:
1. Entry quality screening is TOO STRICT for mean reversion (4% momentum requirement)
2. This week's market recovered, so oversold setups dried up
3. Your position sizing math doesn't add up ($200 × 12 > $1000)

**Fix the momentum filter and you'll start seeing 3-5 trades/week.**

Don't lower standards just to force trades. The best traders wait for their pitch.

