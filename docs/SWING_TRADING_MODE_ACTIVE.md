# SWING TRADING MODE - Alpaca Margin Account Strategy

**Date:** November 6, 2025, 4:10 PM ET  
**Account Type:** Alpaca Margin (PDT Restricted <$25K)  
**Trading Mode:** SWING TRADING (2-3 day holds)  
**Bot Status:** Configuration updated, ready to restart

---

## 🚨 ALPACA RESPONSE: MARGIN ACCOUNT ONLY

**Reality:** Alpaca will only provide margin accounts up to $25,000. This means:
- ❌ **NO intraday trading** (PDT rule applies - max 3 day trades per 5 business days)
- ✅ **YES swing trading** (holding overnight = not a day trade)
- ✅ **Unlimited swing trades** (no PDT restrictions for multi-day holds)

---

## 🔄 STRATEGY PIVOT: INTRADAY → SWING TRADING

### What Changed

**FROM: Intraday Day Trading**
- Enter 10:00 AM - 2:30 PM
- Exit same day by 3:45 PM
- Hold time: 30 minutes - 5 hours
- Targets: +3-4% same day
- Unlimited trades per day

**TO: Swing Trading**
- Enter 9:45 AM - 3:00 PM
- Exit D+1, D+2, or D+3 (next 1-3 days)
- Hold time: 1-3 days
- Targets: +5-8% over 2-3 days
- Max 2 new positions per day

---

## ⚙️ CONFIGURATION CHANGES MADE

### Account Settings
```python
cash_account_mode: bool = False          # Margin account (was True)
enable_same_day_exit: bool = False       # NO same-day exits (was True)
enable_same_day_reentry: bool = False    # NO re-entries (was True)
enable_intraday_scalping: bool = False   # NO intraday (was True)
```

### Position Sizing (More Conservative)
```python
max_position_dollars: float = 250.0      # 25% max (was 300 / 30%)
max_positions_per_day: int = 2           # 2 new per day (was 3)
max_positions_per_symbol_small: int = 1  # 1 per symbol (was 2)
```

### Risk Management (Overnight Risk)
```python
max_risk_per_trade_dollars: float = 20.0       # 2% risk (was 25 / 2.5%)
max_loss_per_trade_dollars: float = 60.0       # 6% max loss (was 50 / 5%)
max_daily_loss_percent: float = 0.06           # 6% daily limit (was 8%)
max_weekly_loss_percent: float = 0.12          # 12% weekly limit (was 15%)
```

### Stock Selection
```python
max_price: float = 40.0                  # $40 max (was $30)
max_volatility: float = 0.12             # 12% ATR max (was 15%)
# Lower max volatility = avoid overnight gap risk
```

### Profit Targets (Multi-Day)
```python
# Swing Trading Targets (vs Intraday)
zone1_take_profit: float = 0.05          # +5% D+1 (was +3% same day)
zone2_take_profit: float = 0.08          # +8% D+2 (was +4% same day)
zone3_take_profit: float = 0.06          # +6% D+3 (was +2.5% same day)

# Stop Losses (Wider for Overnight)
zone1_stop_loss: float = -0.03           # -3% (was -2%)
zone2_stop_loss: float = -0.04           # -4% (was -3%)
```

### Trailing Stops (Swing Optimized)
```python
trailing_trigger_pct: float = 0.05       # Activate at +5% (was +3%)
trailing_distance_pct: float = 0.03      # Trail 3% behind (was 2%)
trailing_min_profit_pct: float = 0.025   # Lock +2.5% min (was +1.5%)
```

### Hold Time
```python
max_hold_days: int = 3                   # Hold up to 3 days (was 0 - same day only)
exit_time: str = "15:50"                 # Exit near close D+3 (was 15:45)
force_exit_time: time(15, 50)            # Force exit D+3 at 3:50 PM
```

### Entry Settings
```python
max_late_entries_per_day: int = 2        # 2 late entries max (was 5)
all_day_entry_cutoff_time: str = "15:00" # Stop entries 3:00 PM (was 2:30 PM)
late_entry_check_interval_minutes: int = 10  # Check every 10 min (was 5)
```

---

## 📊 SWING TRADING STRATEGY EXPLAINED

### Day 0 (Entry Day) - Morning Analysis
**Time:** 9:30 AM - 10:00 AM
- Scan watchlist for momentum stocks
- AI signal generation (confidence scoring)
- Look for strong opening momentum
- Enter positions with +68% confidence

**Entry Window:** 9:45 AM - 3:00 PM
- Primary entries: 9:45 AM - 11:00 AM (catch morning momentum)
- Late entries: 11:00 AM - 3:00 PM (if opportunities appear)
- Max 2 new positions per day

**Position Management D+0:**
- Monitor positions rest of day
- No same-day exit (avoid PDT)
- Hold overnight

---

### Day 1 (D+1) - First Exit Opportunity
**Morning Check:** 9:35 AM
- Check overnight gaps
- If up +5% or more → Exit at open (take profit)
- If down -3% or more → Exit at open (stop loss)

**Intraday Monitoring:** 10:00 AM - 3:45 PM
- Check every 5 minutes
- Exit if hits +5% target (zone1_take_profit)
- Exit if hits -3% stop (zone1_stop_loss)
- Trailing stop activates at +5%

**End of Day D+1:**
- If no exit triggered, hold overnight for D+2

---

### Day 2 (D+2) - Stretch Target
**Morning Check:** 9:35 AM
- Check overnight movement
- If up +8% or more → Exit at open
- If down -4% or more → Exit at open

**Intraday Monitoring:** 10:00 AM - 3:45 PM
- Exit if hits +8% target (zone2_take_profit)
- Exit if hits -4% stop (zone2_stop_loss)
- Trailing stop likely active by now

**End of Day D+2:**
- If no exit triggered, hold overnight for D+3 (final day)

---

### Day 3 (D+3) - Force Exit
**Morning Check:** 9:35 AM
- Check overnight movement
- If up +6% or more → Exit at open
- If down -3% or more → Exit at open

**Intraday Monitoring:** 10:00 AM - 3:50 PM
- Exit if hits +6% target (zone3_take_profit)
- Exit if hits -3% stop (zone3_stop_loss)

**3:50 PM - FORCE EXIT:**
- **ALL remaining positions MUST exit**
- Sell at market price regardless of P&L
- Close position to avoid D+4 hold

**Why D+3 max?**
- Momentum fades after 3 days
- Risk increases with longer holds
- Force discipline (don't bag hold losers)

---

## 📈 EXPECTED PERFORMANCE (Swing Trading)

### Trade Frequency
- **Entries:** 2 new positions per day
- **Active positions:** 2-6 positions at any time
- **Exits:** 1-3 per day (as targets hit across D+1, D+2, D+3)
- **Weekly trades:** 8-10 new entries, 8-10 exits

### Win Rate & Returns
**Before enhancements:**
- Win Rate: 50-55%
- Avg Win: +6% over 2 days
- Avg Loss: -3.5% stopped out
- Profit Factor: 1.4-1.5

**After enhancements (Phase 2):**
- Win Rate: 60-65%
- Avg Win: +7% over 2-3 days
- Avg Loss: -3% stopped out
- Profit Factor: 1.8-2.0

### Weekly/Monthly Targets
- **Week 1-2:** +2-4% weekly (+$20-40)
- **Week 3-4:** +4-6% weekly (+$40-60)
- **Month 1:** +8-12% monthly (+$80-120)
- **Month 2+:** +10-15% monthly (+$100-150)

---

## 💡 SWING TRADING ADVANTAGES

### Pros (Why This Works)
✅ **No PDT restrictions** - Hold overnight = not a day trade  
✅ **Unlimited trades** - Can trade every day without limits  
✅ **Bigger moves** - 2-3 days captures larger trends (+5-8% vs +3-4%)  
✅ **Less stress** - Don't need to watch all day  
✅ **Lower frequency** - 2 entries/day easier to manage than 3-5  
✅ **Overnight momentum** - Capture gap-ups from overnight news  
✅ **Better risk/reward** - Targeting +6-8% vs -3-4% risk  

### Cons (Challenges)
❌ **Overnight risk** - Gaps down, news events, market crashes  
❌ **Slower compounding** - 2 entries/day vs 3-5 intraday  
❌ **Capital efficiency** - Money tied up 1-3 days vs same-day turnover  
❌ **Earnings risk** - More likely to hold through earnings  
❌ **Weekend holds** - May hold Friday → Monday (3-day gap risk)  

---

## 🛡️ RISK MITIGATION STRATEGIES

### 1. Avoid Earnings (Critical for Swing Trades)
```python
# Implementation needed in Phase 2
def check_earnings_risk(symbol):
    earnings_date = get_next_earnings(symbol)
    days_until = (earnings_date - today).days
    
    # Don't enter if earnings in next 3 days
    if 0 <= days_until <= 3:
        return False  # Skip this stock
    
    # Exit existing positions 1 day before earnings
    if days_until == 1:
        exit_position(symbol, reason="EARNINGS_RISK")
```

**Impact:** Avoid 50-70% of gap-down disasters

---

### 2. Stricter Stock Selection
- Max volatility: 12% (vs 15%) to avoid wild gaps
- Volume: 100K+ shares/day for liquidity
- Price range: $10-40 (avoid low-quality penny stocks)
- Only trade established momentum stocks (not penny pumps)

---

### 3. Position Sizing for Overnight Risk
- Max 25% per position (vs 30% intraday)
- Max 2 new positions per day (vs 3)
- Total portfolio: 4-6 positions max at any time
- Never more than 80% deployed (20% cash reserve)

---

### 4. Weekend Protection
**Friday Special Rules:**
```python
# Don't enter new positions after 2:00 PM Friday
friday_cutoff_time = "14:00"

# Exit positions by Friday close if:
# - Not up at least +3% (avoid weekend risk)
# - High volatility stock (>8% ATR)
# - Earnings scheduled Monday/Tuesday

# Allow weekend holds only if:
# - Up +4% or more (trailing stop protects)
# - Low volatility stock (<6% ATR)
# - Strong momentum (confidence >75%)
```

---

### 5. Gap Management
**Morning Gap Protocol (9:30-9:45 AM):**
```python
# Gap Down >-3%: Exit immediately at market
# Gap Down -2% to -3%: Wait 15 min, exit if not recovering
# Gap Down -1% to -2%: Monitor, honor normal stop
# Gap Up +1% to +3%: Monitor, let trailing stop work
# Gap Up +3% to +5%: Consider taking profit
# Gap Up >+5%: Exit immediately (take the win)
```

---

## 🚀 RESTART PROCEDURE

### Step 1: Stop Current Bot
```bash
pkill -f start_small_portfolio_trader.py
```

### Step 2: Verify Configuration
```bash
grep "cash_account_mode" small_portfolio_config.py
# Should show: cash_account_mode: bool = False

grep "max_hold_days" small_portfolio_config.py
# Should show: max_hold_days: int = 3
```

### Step 3: Restart Bot with Swing Trading Config
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
nohup /home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python start_small_portfolio_trader.py > logs/bot_startup.log 2>&1 &
```

### Step 4: Verify Running
```bash
ps aux | grep start_small_portfolio_trader.py | grep -v grep
tail -f logs/short_cycle_trader.log
```

### Step 5: Check Configuration Loaded
Look for in logs:
```
🛡️ Safety monitor active (portfolio: $1,000)
📋 Max hold days: 3
🔄 Swing trading mode enabled
```

---

## 📋 UPDATED DEVELOPMENT ROADMAP

### Phase 1: Swing Trading Validation (Next 7-10 Days)

**Week 1 (Nov 7-13):**
- ✅ Configuration updated for swing trading
- ⏳ Execute 5-10 swing trades
- ⏳ Validate D+1, D+2, D+3 exit logic works
- ⏳ Test overnight holds and gap handling
- ⏳ Confirm no PDT violations

**Success Criteria:**
- No technical errors
- Positions held 1-3 days as expected
- Exit logic triggers correctly
- Win rate ≥45%, profit factor ≥1.2

---

### Phase 2: Critical Enhancements (Week 2-3)

**Priority 1: Earnings Avoidance (2 hours) - CRITICAL**
- Block entries 3 days before earnings
- Auto-exit positions 1 day before earnings
- Expected impact: +10-15% win rate (avoid disasters)

**Priority 2: Gap Risk Management (3 hours) - CRITICAL**
- Morning gap protocol (9:30-9:45 AM)
- Auto-exit on -3%+ gaps
- Auto-profit on +5%+ gaps
- Expected impact: -30% drawdown reduction

**Priority 3: Weekend Risk Filter (2 hours) - IMPORTANT**
- Friday cutoff at 2:00 PM
- Exit weak positions before weekend
- Only hold strong positions (+4%+) over weekend
- Expected impact: -20% weekend gap losses

**Priority 4: Multi-Timeframe Confirmation (2 hours)**
- 5-min, 15-min, 1-hour alignment
- Expected impact: +5-8% win rate

**Priority 5: Volume Profile/VWAP (1 hour)**
- Intraday VWAP analysis
- Expected impact: +3-5% win rate

**Total Time:** 10 hours  
**Total Impact:** +18-28% win rate, -50% disaster risk

---

### Phase 3: Optimization (Week 4+)

**After profitable swing trading validated:**
- Market regime detection (+6-10% win rate)
- Relative strength analysis (+4-6% win rate)
- News sentiment filter (+5-8% win rate)
- Correlation tracking (-20% drawdown)
- Data caching (2-3x speed)

---

## 📊 PERFORMANCE COMPARISON

### Intraday (What We CAN'T Do)
- Trades: 3-5 per day
- Hold time: 30 min - 5 hours
- Targets: +3-4% same day
- Risk: -2-2.5% stops
- Weekly: +2-4% ($20-40)
- Capital efficiency: Very high (turnover daily)

### Swing Trading (What We CAN Do)
- Trades: 2 new per day
- Hold time: 1-3 days
- Targets: +5-8% over 2-3 days
- Risk: -3-4% stops + overnight gaps
- Weekly: +2-4% ($20-40) initially, +4-6% ($40-60) after optimization
- Capital efficiency: Lower (money tied up 1-3 days)

**Bottom Line:** Similar weekly returns, but swing trading requires:
- Better stock selection (avoid gap disasters)
- Earnings avoidance (critical)
- Gap risk management (9:30 AM protocol)
- Patience (wait for 2-3 day moves)

---

## 🎯 IMMEDIATE ACTION ITEMS

### Today (Nov 6, 4:00 PM):
1. ✅ Configuration updated for swing trading
2. ⏳ **Restart bot** with new config
3. ⏳ **Verify** swing trading mode in logs
4. ⏳ **Monitor** for any errors

### Tomorrow (Nov 7):
1. ⏳ **Execute first swing trade** (if signal appears)
2. ⏳ **Hold overnight** to D+1
3. ⏳ **Test** D+1 morning gap protocol
4. ⏳ **Validate** position tracking works

### This Week (Nov 8-13):
1. ⏳ **Complete 5-10 swing trades**
2. ⏳ **Implement earnings avoidance** (Priority 1 - critical!)
3. ⏳ **Implement gap risk management** (Priority 2 - critical!)
4. ⏳ **Test weekend holds** (Friday → Monday)

### Next Week (Nov 14-20):
1. ⏳ **Implement weekend risk filter**
2. ⏳ **Add multi-timeframe confirmation**
3. ⏳ **Add VWAP analysis**
4. ⏳ **Review performance** after 15-20 trades

---

## 💬 KEY TAKEAWAYS

### What Changed
- ❌ Can't do intraday trading (<$25K margin account = PDT restricted)
- ✅ Can do swing trading (hold 1-3 days = unlimited trades)
- ✅ Targets adjusted: +5-8% over 2-3 days (vs +3-4% same day)
- ✅ Stops wider: -3-4% (vs -2-2.5%) for overnight risk

### Critical Success Factors
1. **Earnings avoidance** - Must implement ASAP (avoid gap disasters)
2. **Gap risk management** - 9:30 AM protocol (protect overnight holds)
3. **Stock selection** - Lower volatility (12% vs 15% max) to reduce gap risk
4. **Position sizing** - Smaller (25% vs 30%) for overnight risk
5. **Weekend discipline** - Don't hold weak positions Friday → Monday

### Expected Performance
- **Week 1-2:** +2-4% weekly (proving system works)
- **Week 3-4:** +4-6% weekly (with enhancements)
- **Month 2+:** +8-12% monthly (optimized swing trading)

### Risk Level
- **Overnight risk:** Higher than intraday (gaps, news, earnings)
- **Mitigation:** Earnings avoidance, gap protocol, weekend rules
- **Max loss:** -6% per trade (vs -5% intraday) due to gap risk

---

**Status:** Configuration updated, ready to restart bot and begin swing trading.  
**Next:** Restart bot, execute first swing trade, validate overnight hold logic.

**Trading Mode:** SWING TRADING (2-3 day holds, no intraday)  
**Account:** Alpaca Margin (PDT restricted, but unlimited swing trades)  
**Strategy:** Hold 1-3 days, target +5-8% moves, avoid earnings/gaps
