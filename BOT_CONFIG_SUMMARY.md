# 🤖 BOT CONFIGURATION SUMMARY - November 5, 2025

## ❓ YOUR QUESTIONS ANSWERED

---

## 1️⃣ **What stocks is the bot watching for tomorrow?**

### ✅ Current Watchlist (15 stocks):

```
 1. RIVN    (Rivian Automotive)
 2. LLY     (Eli Lilly)
 3. AMZN    (Amazon)
 4. AMD     (Advanced Micro Devices)
 5. GOOGL   (Alphabet/Google)
 6. CAT     (Caterpillar)
 7. NVDA    (Nvidia)
 8. ROKU    (Roku)
 9. JPM     (JPMorgan Chase)
10. C       (Citigroup)
11. GS      (Goldman Sachs)
12. BMY     (Bristol Myers Squibb)
13. AVGO    (Broadcom)
14. MS      (Morgan Stanley)
15. IBM     (IBM)
```

### 📅 Watchlist Details:
- **Generated:** Nov 5, 2025 at 4:30 PM ET
- **Refresh Schedule:** Daily at 4:30 PM (after market close)
- **Source:** PreFilter system (liquidity, volatility, momentum filters)
- **File:** `logs/current_watchlist.json`

### 🔍 How Watchlist is Built:
1. Starts with 33 stock universe
2. Filters for:
   - Price $10-$35 (mid-cap sweet spot)
   - Min volume: 500K shares/day
   - Min dollar volume: $5M/day
   - Volatility: 3%-60% ATR
   - Data completeness (30+ days)
3. Ranks by momentum + volume
4. Selects top 15 quality stocks

---

## 2️⃣ **Is the bot on regular trading for Friday's with an exit for all positions at end of day?**

### ✅ YES - Friday is a NORMAL trading day

**Trading Schedule:**
```
Monday:    ✅ Trade normally
Tuesday:   ✅ Trade normally  
Wednesday: ✅ Trade normally (tomorrow)
Thursday:  ✅ Trade normally
Friday:    ✅ Trade normally
```

### ⏰ Daily Exit Schedule (EVERY DAY):

```
3:45 PM ET - FORCE CLOSE ALL POSITIONS
```

**Key Settings:**
- `max_hold_days = 0` → **Same-day trading ONLY**
- `force_exit_time = 15:45:00` → **3:45 PM hard cutoff**
- `enable_same_day_exit = True` → **Close positions same day as entry**

### 💡 What This Means:

**EVERY trading day (Mon-Fri):**
1. 9:30 AM - Market opens, bot starts scanning
2. 9:45 AM - Entry window opens (best entry time)
3. 10:00 AM - Late entry window starts (stricter threshold)
4. 2:30 PM - Last entry allowed (need 75 min to exit)
5. **3:45 PM - ALL POSITIONS CLOSED (no exceptions)**

**Friday specifically:**
- ✅ Trades normally throughout day
- ✅ Closes ALL positions at 3:45 PM
- ✅ Goes into weekend with 100% cash
- ✅ No special "exit-only" rules

**Why same-day only:**
- Cash account (no Pattern Day Trader restrictions)
- Avoids overnight risk (gaps, news)
- Fresh start each day
- T+2 settlement friendly

---

## 3️⃣ **Is the bot using momentum and reversion or just momentum?**

### 🎯 **PURE MOMENTUM ONLY** (No Mean Reversion)

### Entry Logic:

```python
# Calculate 4-period momentum
recent_returns = data.pct_change().tail(4)
momentum_score = recent_returns.mean()

# Entry requirement: POSITIVE momentum
if momentum_score > 0.0005 and volume_ratio >= 0.7:
    return BUY signal
```

### ✅ Bot BUYS When:
1. **Positive momentum** (stock moving UP)
2. **Volume elevated** (0.7x-2.5x normal)
3. **Quality confirmed** (multi-timeframe alignment)

### ❌ Bot DOES NOT:
- ❌ Buy dips (no mean reversion)
- ❌ Buy oversold conditions
- ❌ Counter-trend trade
- ❌ Use RSI or Bollinger Bands
- ❌ Catch falling knives
- ❌ Buy negative momentum

### 📊 Strategy Breakdown:

**Philosophy:** *"Ride the wave up, don't catch falling knives"*

**What Bot Looks For:**
```
Stock Price Action:
   Day 1:  📈 +0.3%
   Day 2:  📈 +0.4%
   Day 3:  📈 +0.2%
   Day 4:  📈 +0.5%
   
   Average: +0.35% → POSITIVE MOMENTUM ✅
   Volume: 1.2x normal → ELEVATED ✅
   
   → Bot generates BUY signal
```

**What Bot REJECTS:**
```
Stock Price Action:
   Day 1:  📉 -0.5%
   Day 2:  📉 -0.8%
   Day 3:  📈 +0.2%
   Day 4:  📉 -0.3%
   
   Average: -0.35% → NEGATIVE MOMENTUM ❌
   
   → Bot skips (even if "oversold")
```

### 🔍 Technical Details:

**Momentum Calculation:**
- **Lookback:** 4 periods (last 4 bars)
- **Method:** Simple moving average of returns
- **Threshold:** Must be > 0.0005 (0.05%)
- **Timeframe:** 5-minute intraday bars

**Volume Requirement:**
- **Normal volume:** 20-period average
- **Required ratio:** 0.7x - 2.5x normal
- **Purpose:** Confirm conviction behind move
- **Filters out:** Low-volume fake-outs

**Quality Enhancement:**
- **Multi-timeframe:** Checks 5m/15m/1h/4h alignment
- **Momentum consistency:** All timeframes up = strong
- **Statistical validation:** Breakout vs consolidation
- **Score:** 0-100, boosts confidence 1x-3x

### 💡 Why Momentum Only?

**Advantages:**
✅ Rides established trends
✅ Enters with confirmation (not hoping)
✅ Volume validates institutional interest
✅ Works well for intraday (3-6 hour holds)
✅ Avoids catching falling knives

**Trade-offs:**
⚠️ Misses bottom-fishing opportunities
⚠️ Enters after some move already happened
⚠️ Requires active market (not good in chop)

**Perfect For:**
- Small portfolios needing multiple shots
- Cash accounts (unlimited day trades)
- Same-day holds (no overnight risk)
- Momentum-driven markets

**NOT For:**
- Mean reversion traders
- Dip buyers
- Contrarians
- Long-term holders

---

## 📊 COMPLETE BOT SUMMARY

### Strategy Type:
**Intraday Momentum with Quality Filtering**

### Trading Style:
- **Direction:** Long only (no shorts)
- **Approach:** Momentum (not reversion)
- **Timeframe:** Same-day (0 overnight holds)
- **Frequency:** 10-15 trades/week target

### Entry Requirements:
1. Positive 4-period momentum (>0.05%)
2. Volume 0.7x-2.5x normal
3. Base confidence ≥5%
4. Quality scoring boost applied
5. Not in existing position (D+1 rule)

### Exit Rules:
1. **Profit targets:** 2-5% depending on quality
2. **Stop loss:** 1.5-2% depending on quality
3. **Time stops:** 5 hours max hold
4. **Force exit:** 3:45 PM EVERY DAY

### Position Sizing:
- **Max per position:** $300 (30% of portfolio)
- **Min per position:** $50 (5% of portfolio)
- **Max positions/day:** 3
- **Risk per trade:** $25 (2.5%)

### Universe:
- **Current watchlist:** 15 stocks
- **Refreshed:** Daily at 4:30 PM
- **Filtered for:** Liquidity, volatility, momentum
- **Price range:** $10-$35

---

## 🎯 TOMORROW'S EXPECTATIONS (Nov 6, 2025)

### 9:45 AM - Entry Window:
Bot will analyze all 15 watchlist stocks:
- Calculate momentum scores
- Check volume levels
- Run quality scoring
- Generate signals for stocks meeting 5% threshold

### Expected Outcomes:
- **Likely:** 2-5 qualifying signals
- **Enter:** 2-3 positions (max 3/day)
- **Strategy:** Pure momentum with volume confirmation
- **Hold:** 3-6 hours average
- **Exit:** All closed by 3:45 PM

### Watch For:
```bash
# Monitor morning entry window
tail -f logs/short_cycle_trader.log

# Look for these patterns:
🎯 SYMBOL: base_conf=X.XX, quality=XX.X, multiplier=X.XXx
🔎 SYMBOL: momentum=0.00XXX, vol_surge=X.XX, confidence=0.XX
📝 Paper trade: SYMBOL X shares
```

---

## 🔍 QUICK COMMANDS

```bash
# Check watchlist
cat logs/current_watchlist.json | grep symbols

# Verify bot is running
./check_bot_health.sh

# Watch live trading
tail -f logs/short_cycle_trader.log

# Check today's trades (after market)
grep '2025-11-06' logs/short_cycle_trader.log | grep -E 'ENTRY|EXIT'

# See quality scores generated
grep '🎯.*quality=' logs/short_cycle_trader.log | tail -20
```

---

## 📝 SUMMARY ANSWERS

| Question | Answer |
|----------|--------|
| **Stocks for tomorrow?** | 15 stocks: RIVN, LLY, AMZN, AMD, GOOGL, CAT, NVDA, ROKU, JPM, C, GS, BMY, AVGO, MS, IBM |
| **Friday trading?** | YES - Normal trading, all positions closed at 3:45 PM (like every day) |
| **Strategy type?** | PURE MOMENTUM only (no mean reversion, no dip buying) |
| **Hold time?** | Same-day only (3-6 hours average, max 3:45 PM exit) |
| **Entry logic?** | Positive momentum + elevated volume + quality confirmation |

---

**Last Updated:** November 5, 2025, 3:00 PM ET  
**Bot Status:** ✅ Running with enhanced quality scoring  
**Next Action:** Watch 9:45 AM entry window tomorrow
