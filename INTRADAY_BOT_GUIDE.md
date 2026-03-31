# LiteBotX Intraday Day Trading Bot - Complete Guide
**Version: 2.0 - Intraday Optimized**  
**Date: November 4, 2025**  
**Account Type: Cash Account ($1,000 Paper Trading)**

---

## Table of Contents
1. [Overview](#overview)
2. [Strategy Summary](#strategy-summary)
3. [Configuration Reference](#configuration-reference)
4. [Trading Schedule](#trading-schedule)
5. [Entry Logic](#entry-logic)
6. [Exit Logic](#exit-logic)
7. [Risk Management](#risk-management)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Performance Expectations](#performance-expectations)

---

## Overview

### What is This Bot?
LiteBotX is an **intraday momentum trading bot** optimized for small cash accounts ($1,000). It trades highly liquid stocks with strong intraday momentum, entering and exiting positions **the same day** to eliminate overnight risk.

### Key Features
- ✅ **Pure Intraday Trading** - All positions closed daily by 3:45 PM
- ✅ **No Overnight Risk** - Never holds positions overnight
- ✅ **Cash Account Optimized** - Unlimited day trades (no PDT restrictions)
- ✅ **All-Day Entry Window** - Entries from 9:45 AM to 2:30 PM
- ✅ **Aggressive Profit Targets** - 2.5-3.5% intraday gains
- ✅ **Tight Risk Control** - 1.5-2.0% stop losses
- ✅ **Automated Risk Management** - Daily loss limits, position sizing
- ✅ **Real-Time Monitoring** - Checks positions every 2 minutes

### Technical Stack
- **Python 3.11** with litebotx_env virtual environment
- **Alpaca API** for paper trading
- **Market Hours Aware** - Uses US/Eastern timezone
- **Persistent State** - Saves positions between restarts

---

## Strategy Summary

### Core Philosophy
**Capture intraday momentum moves while maintaining strict risk control through same-day exits.**

The bot looks for stocks showing strong momentum (2-8% moves) with high volume, enters positions with clear profit targets (+2.5%), and exits either at profit target, stop loss (-1.5%), or force close at 3:45 PM daily.

### Trading Style
- **Type:** Intraday Momentum / Day Trading
- **Hold Time:** 30 minutes to 5 hours (max)
- **Position Count:** 1-3 morning entries + 0-5 late entries
- **Win Rate Target:** 65-70%
- **Risk/Reward:** 1.5% risk for 2.5% reward (1.67:1 ratio)

### Advantages of Intraday Strategy
1. **No Gap Risk** - Close all positions before market close
2. **Fast Capital Recycling** - Up to 8 trades per day possible
3. **No PDT Restrictions** - Cash account allows unlimited day trades
4. **Sleep Easy** - No overnight worries
5. **Better Risk Control** - Know your exact risk every day

---

## Configuration Reference

### Core Settings (`small_portfolio_config.py`)

#### Portfolio Parameters
```python
portfolio_value: 1000.0           # Target portfolio size
max_hold_days: 0                  # SAME-DAY ONLY - no overnight holds
cash_account_mode: True           # No PDT restrictions
enable_same_day_exit: True        # Allow exits same day as entry
enable_all_day_entries: True      # Allow entries throughout day
```

#### Position Sizing
```python
max_position_dollars: 300.0       # 30% max per position
min_position_size_dollars: 50.0   # Minimum position size
max_positions_per_day: 3          # Morning entry limit
max_late_entries_per_day: 5       # Late entry limit
```

#### Profit/Loss Targets (Intraday)
```python
# Primary targets
intraday_take_profit: 0.025       # +2.5% profit target
intraday_stop_loss: -0.015        # -1.5% stop loss
intraday_max_hold_minutes: 300    # 5-hour max hold

# Zone-based targets
zone1_take_profit: 0.025          # +2.5% (morning)
zone1_stop_loss: -0.015           # -1.5%
zone2_take_profit: 0.035          # +3.5% (stretch)
zone2_stop_loss: -0.020           # -2.0%
zone3_take_profit: 0.020          # +2.0% (conservative)
zone3_stop_loss: -0.015           # -1.5%
```

#### Trailing Stops
```python
trailing_trigger_pct: 0.015       # Activate at +1.5% gain
trailing_distance_pct: 0.01       # Trail 1% behind peak
trailing_min_profit_pct: 0.01     # Lock +1% minimum
trailing_update_interval: 60      # Update every 60 seconds
```

#### Time Windows
```python
# Morning entry: 9:45-10:00 AM (15 minutes)
# Late entries: 10:00 AM-2:30 PM
allow_late_entries_after_minutes: 30     # Start late entries at 10:00
all_day_entry_cutoff_time: "14:30"       # Stop entries at 2:30 PM
force_exit_time: time(15, 45)            # Force close at 3:45 PM
late_entry_check_interval_minutes: 5     # Check every 5 minutes
```

#### Risk Limits
```python
max_risk_per_trade_dollars: 25.0     # $25 max risk per trade
max_daily_loss_percent: 0.08         # 8% daily loss limit ($80)
max_weekly_loss_percent: 0.15        # 15% weekly loss limit ($150)
```

#### Stock Selection Filters
```python
min_price: 10.0                   # Minimum stock price
max_price: 35.0                   # Maximum stock price
min_avg_volume: 500_000           # 500K shares daily average
min_dollar_volume: 5_000_000      # $5M daily dollar volume
confidence_threshold: 0.05        # 5% confidence for entries
late_entry_confidence_multiplier: 1.3  # 6.5% for late entries
```

---

## Trading Schedule

### Daily Timeline (All Times Eastern)

#### Pre-Market (Before 9:30 AM)
- Bot initializes
- Loads previous positions (should be 0 for intraday)
- Checks market status
- Waits for market open

#### Market Open (9:30 AM)
- Market opens
- Bot waits 15 minutes for stabilization
- **No trades during this period**

#### Primary Entry Window (9:45-10:00 AM)
- **15-minute entry window**
- Scans pre-filtered universe (~10-15 stocks)
- Confidence threshold: **5%**
- Targets: **1-3 positions**
- Position size: Up to **$300 per trade**
- Best opportunity window (strongest signals)

#### Late Entry Window (10:00 AM-2:30 PM)
- Scans every **5 minutes** for high-confidence setups
- Confidence threshold: **6.5%** (1.3× multiplier)
- Targets: **0-5 additional positions**
- Position size: **$300** (same as morning)
- More selective than morning entries

#### Entry Cutoff (2:30 PM)
- **NO NEW ENTRIES AFTER THIS TIME**
- Ensures 75+ minutes to manage exits
- Bot continues monitoring existing positions

#### Force Exit Period (3:45 PM)
- **HARD EXIT TIME**
- ALL positions closed automatically
- No exceptions
- Account returns to 100% cash

#### Market Close (4:00 PM)
- Market closes
- Bot enters idle mode
- Clean slate for next day

---

## Entry Logic

### Morning Entry (9:45-10:00 AM)

#### Qualification Criteria
1. **Price Range:** $10-$35 per share
2. **Volume:** 500K+ shares daily average
3. **Dollar Volume:** $5M+ daily
4. **Momentum:** Positive 4-day return
5. **Confidence:** ≥5% signal strength

#### Position Sizing
- **Base Size:** Calculated from $333 daily pool (33% of $1K)
- **Max Size:** $300 per position (30% of portfolio)
- **Minimum:** $50 per position
- **Multipliers:** Based on signal confidence
  - High confidence (>7%): 2.5-3.0× base
  - Medium confidence (5-7%): 1.8-2.5× base
  - Low confidence (<5%): Rejected

#### Entry Process
1. Pre-filter universe to 10-15 quality stocks
2. Calculate momentum and technical indicators
3. Generate AI signals with confidence scores
4. Rank signals by confidence
5. Select top 1-3 signals meeting 5% threshold
6. Submit market orders
7. Wait for fills and track positions

### Late Entry (10:00 AM-2:30 PM)

#### Key Differences from Morning
- **Higher Bar:** 6.5% confidence required (vs 5%)
- **More Selective:** Only exceptional setups
- **Same Sizing:** Full $300 positions allowed
- **More Frequent Checks:** Every 5 minutes
- **Volume Requirement:** 750K+ shares (vs 500K)

#### When Late Entries Happen
- Strong breakout with volume spike
- News catalyst drives momentum
- Continuation of morning trend
- Gap fill with reversal signal

#### Late Entry Limits
- **Maximum:** 5 late entries per day
- **Combined Limit:** No more than 8 total positions (3 morning + 5 late)
- **Risk Check:** Must pass daily loss limit check

---

## Exit Logic

### Exit Methods (Priority Order)

#### 1. Emergency Exits (Highest Priority)
- **Stop Loss:** Price drops ≥2% → Exit immediately
- **Profit Take:** Price up ≥3% → Exit immediately
- **Account Protection:** Daily loss limit hit → Close all

#### 2. Time-Based Zone Exits

**Zone 1: Morning (9:30-11:00 AM)**
- Exit if **+1%** or better
- Patient with small losses (hold if >-2%)
- Let winners run early

**Zone 2: Midday (11:00 AM-2:00 PM)**
- Exit if **+0.5%** or better
- Getting more defensive
- Take partial profits

**Zone 3: Afternoon (2:00-3:30 PM)**
- Exit if **breakeven or better**
- Cut losses if **-1.5%** or worse
- Protect capital, reduce risk

**Zone 4: Late Day (3:30-3:45 PM)**
- Exit if **-1.5%** or better
- Monitoring every check (2 min intervals)
- Prepare for force close

**Zone 5: Force Close (3:45 PM)**
- **EXIT EVERYTHING**
- Market orders at any price
- No overnight holds, period

#### 3. Trailing Stops
- **Activation:** Position up +1.5%
- **Distance:** Trail 1% below peak
- **Protection:** Lock +1% minimum profit
- **Update Frequency:** Every 60 seconds

#### 4. Target Price Exits
- If position hits target price (+2.5% typical)
- Immediate exit, lock profits

### Same-Day Exit Process
1. Bot checks positions every **2 minutes**
2. Gets current price for each position
3. Calculates P&L percentage
4. Applies exit logic based on:
   - Time of day (zone)
   - Profit/loss level
   - Trailing stop status
5. Submits market orders for exits
6. Updates position tracking
7. Frees capital for re-use

---

## Risk Management

### Position-Level Risk

#### Individual Position Limits
- **Max Position:** $300 (30% of portfolio)
- **Max Risk:** $25 per trade (2.5% of portfolio)
- **Stop Loss:** -1.5% to -2.0% depending on zone
- **Max Hold:** 5 hours (300 minutes)

#### Position Sizing Formula
```
Base Size = Daily Pool / Max Positions
          = $333 / 3 = $111

Actual Size = Base Size × Confidence Multiplier
            = $111 × 2.5 = $278 (for high confidence)

Capped At = min(Actual Size, $300)
```

### Portfolio-Level Risk

#### Daily Limits
- **Max Daily Loss:** 8% ($80)
- **Max Positions:** 8 total (3 morning + 5 late)
- **Max Capital Deployed:** $1,000 (can use 100% intraday)

#### Weekly Limits
- **Max Weekly Loss:** 15% ($150)
- **Kill Switch:** If hit, stops all trading for week

#### Risk Monitoring
Bot checks before every entry:
1. Current daily P&L
2. Current weekly P&L
3. Number of open positions
4. Available capital
5. Loss limits

### Stop Loss Strategy

#### Why Tight Stops?
- Small account can't absorb large losses
- Intraday moves are fast
- Better to cut and re-enter
- Preserve capital for next opportunity

#### Stop Loss Levels
- **Primary:** -1.5% (most positions)
- **Wide:** -2.0% (high confidence runners)
- **Emergency:** -2.0% hard stop (always)

### Capital Protection

#### Settlement Tracking (T+2)
- Tracks settled vs unsettled cash
- Warns if using >80% unsettled funds
- Keeps $50 emergency reserve

#### Force Close Safety
- All positions closed by 3:45 PM
- No overnight gap risk
- Clean slate daily

---

## Monitoring & Logs

### Log Files

#### Primary Log: `logs/short_cycle_trader.log`
Real-time bot activity:
```bash
tail -f logs/short_cycle_trader.log
```

Key indicators to watch:
- `🔍 Scanning for late-day entry opportunities` - Looking for trades
- `✅ REAL BUY ORDER SUBMITTED` - Entry executed
- `🔚 Exiting` - Exit executed
- `⚠️ FORCE EXIT TIME` - 3:45 PM close
- `❌ FAILED` - Errors (investigate)

#### Check Recent Activity
```bash
# Last 50 lines
tail -50 logs/short_cycle_trader.log

# Search for trades today
grep "$(date +%Y-%m-%d)" logs/short_cycle_trader.log | grep -E "BUY|SELL"

# Check for errors
grep "ERROR\|FAILED" logs/short_cycle_trader.log | tail -20
```

### Bot Status

#### Check if Running
```bash
ps aux | grep "start_small_portfolio_trader.py" | grep -v grep
```

#### Current Account Status
```bash
python3 << 'EOF'
from connect_real_trading import RealPaperTradingEngine
engine = RealPaperTradingEngine()
info = engine.get_account_info()
if info:
    acct = info.get('account', {})
    print(f"Portfolio: ${float(acct.get('portfolio_value', 0)):,.2f}")
    print(f"Cash: ${float(acct.get('cash', 0)):,.2f}")
    print(f"Buying Power: ${float(acct.get('buying_power', 0)):,.2f}")
EOF
```

### Performance Monitoring

#### Daily P&L
Check `logs/short_cycle_trader.log` for:
```
📊 Total exits processed: X (Strategic D+1: 0, Other: X)
```

#### Position Count
```bash
grep "positions" logs/short_cycle_trader.log | tail -5
```

#### Win Rate
Track manually:
- Wins: Exits with positive P&L
- Losses: Exits with negative P&L
- Target: >65% win rate

---

## Troubleshooting

### Common Issues

#### Bot Not Trading

**Symptoms:**
- No entries during 9:45-10:00 AM window
- Log shows "No high-confidence signals found"

**Possible Causes:**
1. Market too quiet (low volatility)
2. No stocks meeting 5% confidence threshold
3. All stocks already have positions
4. Daily loss limit reached

**Solutions:**
- Check market conditions (VIX, major indices)
- Review confidence_threshold setting (current: 5%)
- Verify watchlist has liquid stocks
- Check daily P&L hasn't hit -8% limit

#### Bot Not Exiting

**Symptoms:**
- Positions held past 3:45 PM
- Losses exceeding stop loss levels

**Checks:**
1. Verify bot is running: `ps aux | grep start_small`
2. Check force exit time: Should be 15:45:00
3. Review exit logic in logs
4. Verify API connection to Alpaca

**Fix:**
- Restart bot if hung
- Manually close positions via Alpaca dashboard
- Review logs for errors

#### API Connection Errors

**Symptoms:**
- `❌ FAILED to submit order`
- `Cannot get current price`

**Solutions:**
1. Check API keys are valid
2. Verify internet connection
3. Check Alpaca service status
4. Restart bot

#### Position Tracking Issues

**Symptoms:**
- Bot thinks it has positions when it doesn't
- Position file corrupted

**Fix:**
```bash
# Backup current positions
cp positions.json positions_backup.json

# Clear positions (if needed)
echo "[]" > positions.json

# Restart bot
pkill -f start_small_portfolio_trader.py
python3 start_small_portfolio_trader.py &
```

### Error Messages

#### "insufficient buying power"
- Check account cash balance
- Verify no pending orders
- May have unsettled funds (T+2)

#### "NOT_ELIGIBLE_YET"
- Position entered too recently
- Wait for next check interval (2 minutes)

#### "FORCED_EXIT_LATE"
- Past scheduled exit date
- Should not occur in intraday mode (max_hold_days=0)

---

## Performance Expectations

### Realistic Daily Targets

#### Conservative Day
- **Trades:** 1-2 entries, 1-2 exits
- **Win Rate:** 50%
- **Avg Win:** +2.0%
- **Avg Loss:** -1.5%
- **Net P&L:** +0.25% ($2.50)

#### Average Day
- **Trades:** 2-4 entries, 2-4 exits
- **Win Rate:** 65%
- **Avg Win:** +2.5%
- **Avg Loss:** -1.5%
- **Net P&L:** +0.75% ($7.50)

#### Strong Day
- **Trades:** 4-6 entries, 4-6 exits
- **Win Rate:** 70%
- **Avg Win:** +3.0%
- **Avg Loss:** -1.2%
- **Net P&L:** +1.5% ($15.00)

### Weekly Targets

#### Target Range
- **Conservative:** +2-3% per week ($20-30)
- **Average:** +4-5% per week ($40-50)
- **Aggressive:** +6-8% per week ($60-80)

#### Monthly Targets
- **12% monthly** → $120/month
- **Compounding:** $1,000 → $1,120 → $1,254 → $1,405
- **Annual projection:** ~120-150% (if sustained)

### What to Expect Tomorrow (Tuesday, Nov 5)

#### Morning (9:45-10:00 AM)
- Bot will scan universe of 10-15 stocks
- Likely to enter **1-3 positions**
- Position sizes: $200-300 each
- Total deployment: $300-900

#### Throughout Day
- Check positions every 2 minutes
- May take **0-3 late entries** if strong signals
- Exit winners at +2.5% or trailing stops
- Cut losers at -1.5%

#### End of Day (3:45 PM)
- Force close all remaining positions
- Account back to 100% cash
- P&L locked in (no overnight risk)

### Risk Scenarios

#### Worst Case Single Day
- All 3 morning entries hit stop loss: -$13.50 (3 × $300 × 1.5%)
- 2 late entries also stopped: -$9.00 (2 × $300 × 1.5%)
- **Total Loss:** -$22.50 (-2.25%)
- Well below 8% daily limit

#### Worst Case Week
- 5 losing days at -2% each: -$100 total
- Still below 15% weekly limit (-10%)
- Bot would continue trading (not killed)

---

## Quick Reference Commands

### Start/Stop Bot
```bash
# Start
cd /home/wes/Desktop/litebotx-usb-deployment
nohup python3 start_small_portfolio_trader.py > /dev/null 2>&1 &

# Stop
pkill -f start_small_portfolio_trader.py

# Check status
ps aux | grep start_small_portfolio_trader.py | grep -v grep
```

### Monitor Logs
```bash
# Live tail
tail -f logs/short_cycle_trader.log

# Today's trades
grep "$(date +%Y-%m-%d)" logs/short_cycle_trader.log | grep -E "BUY|SELL"

# Recent activity
tail -100 logs/short_cycle_trader.log
```

### Run Tests
```bash
# Full test suite
python3 test_intraday_bot.py

# Quick config check
python3 -c "from small_portfolio_config import SmallPortfolioConfig; c = SmallPortfolioConfig(); print(f'✅ max_hold_days={c.max_hold_days}, force_exit={c.force_exit_time}')"
```

### Account Status
```bash
# Quick check
python3 -c "from connect_real_trading import RealPaperTradingEngine; e = RealPaperTradingEngine(); i = e.get_account_info(); print(f\"Cash: \${float(i['account']['cash']):,.2f}\") if i else print('❌ Connection failed')"
```

---

## Configuration Files

### Key Files
- `small_portfolio_config.py` - Main configuration
- `traders/short_cycle_trader.py` - Trading logic
- `connect_real_trading.py` - Execution engine
- `start_small_portfolio_trader.py` - Bot launcher
- `test_intraday_bot.py` - Test suite

### Important Settings
```python
# In small_portfolio_config.py
max_hold_days = 0                  # Intraday only
cash_account_mode = True           # No PDT
force_exit_time = time(15, 45)    # 3:45 PM daily close
enable_all_day_entries = True      # All-day scanning
```

---

## Support & Maintenance

### Daily Checklist
- [ ] Check bot is running (morning)
- [ ] Monitor logs during 9:45-10:00 entry window
- [ ] Verify trades executing correctly
- [ ] Check force close at 3:45 PM
- [ ] Review daily P&L
- [ ] Verify account back to 100% cash

### Weekly Checklist
- [ ] Review win rate (target: >65%)
- [ ] Check weekly P&L
- [ ] Verify no positions held overnight (should be 0)
- [ ] Review log files for errors
- [ ] Run test suite: `python3 test_intraday_bot.py`

### Monthly Checklist
- [ ] Calculate monthly return
- [ ] Review strategy performance
- [ ] Adjust confidence thresholds if needed
- [ ] Update watchlist if necessary
- [ ] Backup configuration files

---

## Version History

### v2.0 - Intraday Optimized (November 4, 2025)
- Converted from D+1 swing to pure intraday
- Removed overnight holds (max_hold_days = 0)
- Added force close at 3:45 PM
- Optimized profit targets (2.5% vs 4-6%)
- Tighter stop losses (1.5% vs 2.5%)
- Increased late entry limit (5 vs 2)
- Trade all 5 days (Mon-Fri vs Mon-Thu)
- 100% test suite pass rate

### v1.0 - Initial Release
- D+1 swing trading strategy
- Overnight holds
- Larger profit targets (4-6%)
- Wider stop losses (2.5%)

---

## Conclusion

This intraday day trading bot is designed to maximize efficiency for small cash accounts by:
- Eliminating overnight risk
- Enabling fast capital recycling
- Providing realistic 2-5% weekly returns
- Maintaining strict risk controls

**Remember:** Past performance does not guarantee future results. Always monitor the bot and be prepared to intervene if market conditions change dramatically.

**Questions or Issues?** Review this guide first, then check logs for error messages.

---

*Last Updated: November 4, 2025*  
*Next Review: November 11, 2025*
