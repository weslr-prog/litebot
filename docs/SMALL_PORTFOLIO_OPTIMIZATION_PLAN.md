# Small Portfolio Optimization Plan (<$1,000)

## Current Performance Analysis (Oct 30, 2025)

### Today's Results
- **Account:** $970,890.60 equity
- **Daily P&L:** -$106.13 (-0.01%) - essentially flat
- **Positions:** 3 active, ranging $4,598 - $5,951 each
- **Average Position Size:** ~$5,480

### This Week's Results
- **Total Invested:** $148,798
- **Closed Positions:** 6 trades
- **Win Rate:** 50% (3 wins, 3 losses)
- **Winners:** AMD +$164 (+2.82%), IBM +$167 (+1.42%), QCOM +$120 (+0.50%)
- **Losers:** PYPL -$918 (-3.79%), MMM -$75 (-1.27%), SHOP -$71 (-0.60%)

### Key Observations
1. **Position sizes too large for small accounts** - $4,500-$6,000 positions
2. **Trading expensive stocks** - SHOP ($176), QCOM ($182), IBM ($313)
3. **Low % gains** - Winners: 0.5%, 1.4%, 2.8% (need bigger swings)
4. **Single big loser** - PYPL -$918 killed the week's performance

---

## 🎯 Small Portfolio Strategy (<$1,000)

### Core Philosophy
**From:** Large-cap stocks with small percentage moves  
**To:** Mid-cap volatile stocks with predictable 3-10% daily swings

### Target Profile
- **Portfolio Size:** $1,000
- **Position Size:** $100-$200 each (5-10 positions max)
- **Stock Price:** $10-$30 (sweet spot for volatility + affordability)
- **Daily Volatility:** 3-8% ATR (vs current 1.5-3.5%)
- **Market Cap:** $500M - $10B (mid-cap, less institutional)

---

## 📊 Proposed Parameter Changes

### 1. Portfolio & Position Sizing

| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **portfolio_value** | $963,000 | $1,000 | Your actual capital |
| **daily_pool_percent** | 60% | 80% | Small account = more aggressive deployment |
| **daily_pool_dollars** | $577,800 | $800 | 80% of $1,000 |
| **max_position_dollars** | $6,000 | $200 | 20% max per position |
| **min_position_size_dollars** | $25 | $100 | Avoid tiny positions |
| **max_positions_per_day** | 8 | 5 | Fewer, larger positions |
| **max_risk_per_trade_dollars** | $100 | $20 | 2% risk per trade |

**Impact:** Position sizes become $100-$200, manageable for $1K account

---

### 2. Risk Management

| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **max_risk_per_trade_dollars** | $100 | $20 | 2% of $1K portfolio |
| **max_loss_per_trade_dollars** | $400 | $50 | 5% max loss per trade |
| **max_daily_loss_percent** | 0.2% ($1,926) | 3% ($30) | Small accounts need tighter stops |
| **max_weekly_loss_percent** | 0.6% ($5,778) | 10% ($100) | Realistic for aggressive strategy |

**Impact:** Risk proportional to account size, prevents blowup

---

### 3. PreFilter - Target Mid-Cap Volatile Stocks

#### Price Range (MOST IMPORTANT)
| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **min_price** | $15 | $10 | Access more volatile mid-caps |
| **max_price** | $350 | $30 | Sweet spot for daily swings |

**Why $10-$30?**
- **Affordable:** $200 position = 7-20 shares (meaningful)
- **Volatile:** Mid-caps move 3-10% daily (vs 1-3% for large-caps)
- **Predictable:** Technical patterns clearer than penny stocks
- **Liquid enough:** Most trade >500K shares/day

**Example Stocks:**
- PLTR (Palantir): $15-20 range, 5-8% daily swings
- RIVN (Rivian): $12-18 range, 6-10% daily swings
- SNAP (Snapchat): $8-12 range, 4-8% daily swings
- PLUG (Plug Power): $3-7 range, 5-12% daily swings
- SOFI (SoFi): $6-10 range, 4-9% daily swings

#### Volatility (CRITICAL)
| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **min_volatility** | 1.5% | 3.0% | Need bigger daily swings |
| **max_volatility** | 35% | 15% | Avoid crazy penny stocks |

**Why 3-15% ATR?**
- **3% minimum:** Ensures meaningful intraday moves for D+1 exits
- **15% maximum:** Keeps stocks predictable, not chaotic
- **Current stocks:** AAPL/GOOGL/IBM = 1.5-2.5% ATR (too stable)
- **Target stocks:** RIVN/PLTR/SOFI = 5-8% ATR (perfect)

#### Momentum
| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **min_momentum** | 2% | 3% | Stronger moves needed |
| **max_momentum** | 30% | 40% | Mid-caps can run harder |

**Why higher momentum?**
- Mid-caps can sustain 20-40% weekly runs
- Large-caps rarely exceed 10% weekly
- You want to catch explosive moves early

#### Liquidity (Adjusted for smaller stocks)
| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **min_avg_volume** | 30,000/day | 100,000/day | Still liquid, but accessible |
| **min_dollar_volume** | $300,000/day | $500,000/day | Ensures exit liquidity |

**Why still care about liquidity?**
- $500K/day = enough for your $100-200 positions
- Avoids penny stocks with no volume
- Ensures you can exit fast if needed

#### Breakout (Already relaxed, keep it)
| Parameter | Current | Proposed | Keep/Adjust |
|-----------|---------|----------|-------------|
| **vol_spike_min** | 0.7 | 0.7 | ✅ Keep (already relaxed) |
| **breakout_min** | 0.0015 | 0.0020 | Tighten slightly for quality |

---

### 4. Exit Strategy Adjustments

#### D+1 Exit Zones (RETUNED FOR VOLATILITY)

**Current zones too tight for 3-10% daily ranges**

| Zone | Time | Current TP | Current SL | Proposed TP | Proposed SL |
|------|------|-----------|-----------|-------------|-------------|
| **Zone 1** (Morning) | 9:30-10:00 | ≥+1.5% | ≤-1.0% | ≥+3.0% | ≤-2.0% |
| **Zone 2** (Mid-Day) | 10:00-2:00 | ≥+2.0% | ≤-1.5% | ≥+4.0% | ≤-3.0% |
| **Zone 3** (Afternoon) | 2:00-3:45 | ≥+1.0% | ≤-1.0% | ≥+2.5% | ≤-2.0% |
| **Zone 4** (Power Hour) | 3:45-4:00 | Force exit | Force exit | Force exit | Force exit |

**Reasoning:**
- Mid-caps regularly swing 5-8% intraday
- Current 1.5% TP exits too early (leaves money on table)
- Current 1.0% SL too tight (gets stopped out on noise)
- Wider bands capture the bigger moves you need

#### Trailing Stops
| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| **trailing_trigger_pct** | 1.5% | 3.0% | Higher trigger for volatile stocks |
| **trailing_distance_pct** | 1.0% | 2.0% | Wider trail to avoid whipsaws |

**Why adjust?**
- 3-8% volatility means 2% noise is normal
- 1.5% trigger exits too early on 5%+ moves
- 2% trail distance prevents shakeouts

---

### 5. Dynamic Position Sizing (KEEP BUT ADJUST)

**Current tiers work, just adjust the base risk**

| Confidence | Multiplier | Current Risk | Proposed Risk | Position Size @ $20 stock |
|------------|-----------|--------------|---------------|---------------------------|
| **HIGH** (≥0.75) | 1.6-2.0x | $160-$200 | $32-$40 | 8-10 shares = $160-$200 |
| **MEDIUM** (0.55-0.75) | 1.2-1.6x | $120-$160 | $24-$32 | 6-8 shares = $120-$160 |
| **LOW** (<0.55) | 1.0-1.2x | $100-$120 | $20-$24 | 5-6 shares = $100-$120 |

**Math Check:**
- Base risk: $20 (2% of $1K)
- HIGH confidence: $20 × 2.0 = $40 risk
- With $2 stop distance: 20 shares × $20 = $400 position (too high!)
- **Solution:** Cap at $200 max position (overrides calculation)

---

## 🎯 Ideal Stock Characteristics for Small Account

### Target Universe (30-50 stocks)

**Sector Focus:**
1. **Tech (Growth):** PLTR, RIVN, SOFI, SNAP, HOOD
2. **Energy (Volatile):** PLUG, FCEL, BE (hydrogen/clean energy)
3. **Cannabis:** TLRY, CGC, SNDL (high volatility)
4. **Crypto-Related:** MARA, RIOT, COIN (follow BTC)
5. **Meme Stocks:** AMC, GME, BBBY (predictable retail patterns)

**Key Traits:**
- ✅ Price: $10-30
- ✅ Volume: >100K shares/day
- ✅ Volatility: 3-8% ATR
- ✅ Market Cap: $500M-$10B
- ✅ Retail interest (WSB, Stocktwits)
- ✅ Clear technical patterns
- ✅ News-driven (earnings, crypto, sector rotation)

**Avoid:**
- ❌ Blue chips (AAPL, GOOGL, MSFT) - too stable
- ❌ True penny stocks (<$5) - too risky
- ❌ Low volume (<50K/day) - can't exit
- ❌ Over $50 - too expensive for $200 positions

---

## 📈 Expected Performance Improvements

### With Current Settings (Large-Cap)
- **Win Rate:** 50%
- **Avg Win:** +1.4% ($77 on $5,500 position)
- **Avg Loss:** -2.0% ($110 on $5,500 position)
- **Profit Factor:** 0.7 (losing money slowly)

### With Proposed Settings (Mid-Cap)
- **Win Rate:** 50% (same)
- **Avg Win:** +4.0% ($8 on $200 position)
- **Avg Loss:** -3.0% ($6 on $200 position)
- **Profit Factor:** 1.33 (profitable!)

**Math:**
- 5 trades per day × 4 trading days = 20 trades/week
- 10 wins @ +$8 = +$80
- 10 losses @ -$6 = -$60
- **Net:** +$20/week (+2% weekly return)

**Realistic Weekly Target:** +$20-40 (+2-4%)

---

## 🛠️ Implementation Plan

### Phase 1: Paper Trading Test (1 week)
1. **Create small account config** with proposed parameters
2. **Run backtest** on last 30 days with $1K portfolio
3. **Identify 20-30 target stocks** in $10-30 range
4. **Validate:** Do they actually swing 3-8% daily?

### Phase 2: Live Testing ($500 to start)
1. **Fund with $500** (not full $1K yet)
2. **Trade 2-3 positions max** to test mechanics
3. **Run for 2 weeks** to validate:
   - Position sizing works correctly
   - Exit zones capture moves
   - Risk limits prevent blowup
4. **Iterate parameters** based on results

### Phase 3: Full Deployment ($1K)
1. **Scale to full $1K** if Phase 2 successful
2. **Trade 4-5 positions** per day
3. **Monitor weekly performance**
4. **Target:** +2-4% weekly return (+$20-40/week)

---

## ⚠️ Risks & Considerations

### Advantages of Small Account
- ✅ **Nimble:** Can enter/exit small stocks easily
- ✅ **Volatile stocks available:** Access to 3-10% daily movers
- ✅ **Lower stress:** Losing $20 vs $400 per trade
- ✅ **Learning opportunity:** Refine strategy cheaply

### Challenges of Small Account
- ❌ **Pattern Day Trader Rule:** Need $25K for unlimited day trades
  - **Solution:** Use cash account (no PDT rule) or limit to 3 day trades/week
- ❌ **Commission impact:** Even $0 commissions have spread costs
  - **Solution:** Trade liquid stocks (5 bp spread = $1 on $200 position)
- ❌ **Psychological:** Hard to stay disciplined with small gains
  - **Solution:** Track % returns, not dollar amounts
- ❌ **Scaling limits:** $1K → $2K easy, but $10K harder in mid-caps
  - **Solution:** Graduate to large-caps as account grows

---

## 🎯 Key Success Factors

### 1. Stock Selection is CRITICAL
- Wrong: Trading AAPL, GOOGL, IBM with $1K account (no movement)
- Right: Trading PLTR, RIVN, SOFI with $1K account (5%+ daily moves)

### 2. Position Sizing Must Be Precise
- $100-200 positions (10-20% of account)
- 5-10 shares per position
- Never exceed $200 per position

### 3. Risk Management Even More Important
- 2% risk per trade ($20) is sacred
- 5% max loss per trade ($50) hard stop
- 3% daily loss limit ($30) shuts down trading

### 4. Take Profits Faster
- Small accounts need winners 2-3x per week
- Don't wait for 10% moves - take 3-5% and move on
- Rinse and repeat

---

## 📊 Comparison Table: Current vs Proposed

| Metric | Current (Large Portfolio) | Proposed (Small Portfolio) |
|--------|--------------------------|---------------------------|
| **Portfolio** | $963,000 | $1,000 |
| **Position Size** | $5,000-6,000 | $100-200 |
| **Stock Price** | $15-350 | $10-30 |
| **Volatility** | 1.5-3.5% ATR | 3-8% ATR |
| **Avg Daily Move** | 1-2% | 4-8% |
| **Risk/Trade** | $100 | $20 |
| **Max Loss/Trade** | $400 | $50 |
| **Positions/Day** | 8 | 5 |
| **Exit Targets** | +1.5-2% | +3-4% |
| **Stop Loss** | -1.0-1.5% | -2-3% |
| **Weekly Target** | +0.25% ($2,400) | +2-4% ($20-40) |

---

## 🚀 Next Steps (Before Coding)

### 1. Validate Stock Universe (TODAY)
- [ ] Pull list of stocks $10-30 price range
- [ ] Filter by >100K volume/day
- [ ] Calculate ATR% for last 30 days
- [ ] Identify 30-50 stocks with 3-8% ATR

### 2. Backtest Proposed Settings (TODAY)
- [ ] Create new config file: `ShortCycleConfigSmall`
- [ ] Run backtest on last 30 days
- [ ] Verify position sizes work
- [ ] Check if profit targets are hit

### 3. Paper Trade Test (THIS WEEK)
- [ ] Set up $1K paper trading account
- [ ] Trade for 5 days with proposed settings
- [ ] Track: win rate, avg gain, avg loss, max drawdown

### 4. Review & Refine (NEXT WEEK)
- [ ] Analyze paper trading results
- [ ] Adjust parameters if needed
- [ ] Document learnings
- [ ] Prepare for live trading with real $500-1000

---

## 💡 Discussion Questions

Before we implement, let's confirm:

1. **Capital:** Are you starting with $500 or full $1,000?
2. **Account Type:** Cash account (no PDT) or margin?
3. **Risk Tolerance:** Comfortable with 3% daily loss limit ($30)?
4. **Time Horizon:** How long to test before live trading?
5. **Stock Preferences:** Any sectors to avoid/prefer?
6. **Exit Strategy:** Agree with wider targets (+3-4% vs +1.5%)?

---

**Status:** 📋 PLANNING PHASE - No code changes yet  
**Next:** Validate assumptions, then implement new config  
**Goal:** +2-4% weekly return on $1K portfolio via volatile mid-caps
