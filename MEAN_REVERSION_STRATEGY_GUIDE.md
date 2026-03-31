# Mean Reversion Strategy Guide: The 24-Hour "Rubber Band Trade"

**What You're Trying To Accomplish:** Catch short-term overreactions in quality, liquid, fast-moving stocks and exit within 24 hours when they normalize.

---

## The Perfect 24-Hour Mean Reversion Stock

### 1. **It Just Got Oversold (But Not Broken)**

**What You Want:**
- Stock dropped 3-5% in the last 5 days
- RSI below 30 (means it's "oversold" - sold too aggressively)
- BUT price isn't more than 6% below its 20-day average

**Why This Matters:**
- Small drops (1-2%) = Not enough fear, won't bounce much
- Big drops (8-10%+) = Something might be actually wrong with the company
- **Sweet spot (3-5%)** = Panic selling, but company is fine

**Your PreFilter Checks:**
```
✅ 5-day momentum: -3% to -6% (falling, but not collapsing)
✅ Price vs 20-SMA: Within 6% (stretched but not broken)
```

**Your Strategy Checks:**
```
✅ RSI < 30 (oversold - was 35, you lowered to 30 for tighter entries)
✅ Volume spike (confirms the panic selling)
```

---

### 2. **It Normally Moves Fast (High Volatility)**

**What You Want:**
- ATR (Average True Range) between 1.5% - 8.0% per day
- Stock typically swings 2-4% daily

**Why This Matters:**
A stock that normally moves 0.5%/day won't give you a 2% bounce in 24 hours. You need stocks that are naturally "springy" - they move big and fast both ways.

**Your PreFilter:**
```
✅ ATR% filter: 1.5%-8.0% (eliminates boring, slow-moving stocks)
```

**Think of it like:**
- Low volatility (1%) = Heavy rubber band (barely moves)
- Good volatility (3-4%) = Normal rubber band (snaps back nicely)
- Too high volatility (10%+) = Wild, unpredictable (might snap in your face)

---

### 3. **People Actually Trade It (Liquidity)**

**What You Want:**
- Average volume > 500K shares/day
- Dollar volume > $10M/day
- Current volume > 1.5x average (spike = attention)

**Why This Matters:**
You need OTHER people to buy the stock after you do. If nobody trades it, you're stuck holding it. Volume spike means institutions or retail traders are paying attention.

**Your PreFilter:**
```
✅ Min volume: 500K shares
✅ Min dollar volume: $10M
✅ Volume quality check
```

**Your Strategy:**
```
✅ Volume spike: 1.5x+ average (confirmation of panic/reversal)
```

---

### 4. **It's In a Sector That Bounces Fast**

**What You Want:**
- Tech, Finance, Consumer Discretionary
- NOT utilities, REITs, slow dividend stocks

**Why This Matters:**
Different sectors behave differently:
- **Fast sectors** (Tech/Finance): Emotional, overreact, bounce quickly
- **Slow sectors** (Utilities/Staples): Stable, don't panic-sell or bounce much

**Your System:**
```
✅ Universe focuses on: SOFI, UPST, RIVN, DKNG (fast-moving sectors)
❌ Blacklist eliminates: T, TU, OGE, BXMT (slow utilities/REITs)
```

---

### 5. **The Price Is Right ($5-$50 Range)**

**What You Want:**
- Not penny stocks ($1-$2) - too sketchy
- Not mega-caps ($200+) - too slow
- Sweet spot: $10-$40

**Why This Matters:**
- Cheap stocks ($2-$5): High risk of going to zero
- Mid-range ($10-$40): Big enough to be legitimate, small enough to be volatile
- Expensive ($100+): Harder for retail traders to move, slower bounces

**Your PreFilter:**
```
✅ Price range checks (implicit in universe selection)
```

---

## How Your System Finds These Stocks: The Full Flow

### **Morning (Pre-Market 9:00 AM)**
```
1. PreFilter scans 107 stocks in universe
2. Removes slow-movers (ATR < 1.5% or > 8.0%)
3. Removes illiquid stocks (volume < 500K)
4. → Result: ~75 "fast-moving candidates"
```

### **Entry Window (9:45-10:30 AM)**
```
5. Strategy checks each of 75 candidates:
   - Is RSI < 30? (oversold)
   - Did it drop 3-5% in 5 days? (pulled down)
   - Is volume spiking 1.5x+? (panic selling)
   - Is price within 6% of 20-day avg? (not broken)
   
6. Blacklist filter removes chronic losers (JD, T, VIPS, etc.)
7. D+1 rule: Can't re-enter stocks you already own
8. → Result: 0-3 high-quality entry signals
```

### **Holding (24 Hours)**
```
9. Smart Exit Manager watches 9 exit triggers:
   - Quick profit: +1.5% after 4 hours ✅ (take the win)
   - Standard profit: +2% anytime ✅ (your target)
   - RSI normalized: RSI > 50 ✅ (rubber band snapped back)
   - Stop loss: -4% ❌ (cut losers fast)
   - Time safety: 24 hours ⏰ (don't hold too long)
```

---

## Real Example: Why STLA (Stellantis) Qualified

**PreFilter Stage:**
- ✅ ATR: 3.2% (good volatility - moves 3%/day typically)
- ✅ Volume: 12M shares/day average
- ✅ Dollar volume: $180M/day
- → **PASSED: Fast-moving, liquid stock**

**Strategy Stage:**
- ✅ RSI: 28 (oversold - panic selling)
- ✅ 5-day drop: -4.2% (moderate pullback)
- ✅ Price: $15.20 vs 20-SMA $16.10 (5.6% below - stretched but not broken)
- ✅ Volume: 18M shares (1.5x spike - attention)
- → **SIGNAL: Enter at $15.20**

**Exit Plan:**
- Target: $15.50 (+2% = $0.30 profit)
- Stop: $14.60 (-4% = $0.60 loss)
- Time limit: 24 hours max
- Smart exits watching for early +1.5% or RSI>50

---

## The Key Insight: Why 24 Hours?

Mean reversion trades are **time-sensitive**:

1. **First 4 hours**: Panic sellers exhaust themselves
2. **4-24 hours**: Bargain hunters step in, price recovers
3. **24-48 hours**: Recovery complete OR new information confirms the drop was real

**Your edge is being early** - you buy during the panic (RSI<30), then exit during the recovery (2% profit or RSI>50), before the crowd realizes what happened.

---

## What You're NOT Trying To Do

❌ **Not buy-and-hold investing** (weeks/months)
❌ **Not trend-following** (riding momentum up)
❌ **Not catching falling knives** (stocks down 20%+)
❌ **Not penny stock gambling** (sketchy $2 stocks)

✅ **You ARE** catching short-term overreactions in quality, liquid, fast-moving stocks and exiting within 24 hours when they normalize.

---

## Bottom Line: The "Rubber Band Snapping Machine"

**Your system is designed to:**
- PreFilter finds stocks with stretchy rubber bands (high ATR, good liquidity)
- Strategy identifies when the band is stretched (RSI<30, 3-5% drop)
- Smart exits catch the snap-back (2% profit, RSI>50, 24h limit)
- Blacklist removes broken rubber bands (chronic losers)

**The goal:** Small, fast, consistent wins (2% in 24 hours = 730% annualized if you could do it daily), not home runs.

---

## Key Metrics To Watch

**Entry Quality:**
- RSI < 30 (tighter = better entries)
- Volume spike 1.5x+ (confirmation)
- 3-5% pullback (sweet spot)

**Exit Efficiency:**
- Win rate > 55% (means you're picking good bounces)
- Avg hold time < 30 hours (fast turnaround)
- Smart exits > 70% (AI exits working better than time limits)

**Risk Management:**
- Max 12 positions (diversification)
- 4% stop loss (cut losers fast)
- Blacklist chronic losers (don't repeat mistakes)
