# Quick Parameter Reference Guide

**Last Updated:** November 6, 2025  
**For:** Small Portfolio Trading Bot ($1K accounts)

---

## 🎯 MOST COMMONLY ADJUSTED PARAMETERS

### File: `small_portfolio_config.py`
**Location:** `/home/wes/Desktop/litebotx-usb-deployment/small_portfolio_config.py`

---

### 1️⃣ PORTFOLIO SIZE (Adjust as account grows)

```python
portfolio_value: float = 1000.0          # YOUR ACCOUNT SIZE
```

**When to change:**
- Start: $1,000
- After doubling: $2,000
- After 5x: $5,000
- After 10x: $10,000

---

### 2️⃣ POSITION SIZING (Risk per trade)

```python
max_position_dollars: float = 300.0      # Max $300 per position (30%)
min_position_size_dollars: float = 50.0  # Min $50 per position (5%)
max_positions_per_day: int = 3           # Max 3 positions daily
```

**Recommendations by account size:**
- **$1K:** max=$300 (30%), min=$50 (5%), max_positions=3
- **$2K:** max=$500 (25%), min=$100 (5%), max_positions=4
- **$5K:** max=$1000 (20%), min=$200 (4%), max_positions=5
- **$10K:** max=$1500 (15%), min=$300 (3%), max_positions=8

---

### 3️⃣ RISK LIMITS (How much you can lose)

```python
max_risk_per_trade_dollars: float = 25.0       # $25 risk per trade (2.5%)
max_loss_per_trade_dollars: float = 50.0       # $50 hard stop (5%)
max_daily_loss_percent: float = 0.08           # 8% daily loss limit ($80)
max_weekly_loss_percent: float = 0.15          # 15% weekly loss limit ($150)
```

**Conservative (lower risk):**
```python
max_risk_per_trade_dollars: float = 15.0       # 1.5% risk
max_daily_loss_percent: float = 0.05           # 5% daily limit
```

**Aggressive (higher risk):**
```python
max_risk_per_trade_dollars: float = 40.0       # 4% risk
max_daily_loss_percent: float = 0.10           # 10% daily limit
```

---

### 4️⃣ STOCK PRICE RANGE (What stocks to trade)

```python
min_price: float = 10.0                  # $10 minimum
max_price: float = 30.0                  # $30 maximum
```

**Why $10-30?**
- Affordable for $100-200 positions
- Volatile enough for 3-8% daily moves
- Liquid enough to exit quickly

**Adjust for larger accounts:**
- **$5K account:** min=$15, max=$50
- **$10K account:** min=$20, max=$100

---

### 5️⃣ VOLATILITY FILTER (How much stocks move)

```python
min_volatility: float = 0.03             # 3% ATR minimum
max_volatility: float = 0.15             # 15% ATR maximum
```

**What this means:**
- 3% = Stock moves at least $0.30 per day on $10 stock
- 15% = Stock moves at most $1.50 per day on $10 stock

**Conservative (less volatility):**
```python
min_volatility: float = 0.02             # 2% ATR
max_volatility: float = 0.10             # 10% ATR
```

**Aggressive (more volatility):**
```python
min_volatility: float = 0.04             # 4% ATR
max_volatility: float = 0.20             # 20% ATR
```

---

### 6️⃣ MOMENTUM FILTER (How fast stocks are moving)

```python
min_momentum: float = 0.03               # 3% minimum 4-day return
max_momentum: float = 0.40               # 40% maximum 4-day return
```

**What this means:**
- 3% = Stock up at least 3% over last 4 days
- 40% = Stock up at most 40% over last 4 days (avoid overextended)

---

### 7️⃣ VOLUME REQUIREMENTS (Liquidity)

```python
min_avg_volume: int = 100_000            # 100K shares/day minimum
min_dollar_volume: int = 500_000         # $500K/day minimum
```

**Don't change unless:**
- Trading larger accounts (increase both)
- Can't find enough stocks (decrease both)

---

### 8️⃣ SIGNAL QUALITY (How confident to be)

```python
# ⚠️ CURRENTLY IN TEST MODE ⚠️
confidence_threshold: float = 0.025            # 2.5% (TEMP)
late_entry_confidence_multiplier: float = 1.05 # 1.05x (TEMP)

# RESTORE TO PRODUCTION AFTER 10 SUCCESSFUL TRADES:
# confidence_threshold: float = 0.05           # 5% minimum
# late_entry_confidence_multiplier: float = 1.3 # 1.3x late entries
```

**Higher threshold = fewer but better trades:**
```python
confidence_threshold: float = 0.07             # 7% (very selective)
```

**Lower threshold = more trades but lower quality:**
```python
confidence_threshold: float = 0.03             # 3% (easier entry)
```

---

### 9️⃣ PROFIT TARGETS (When to take profits)

```python
# Intraday Targets (D+0 same-day exit)
intraday_take_profit: float = 0.04       # +4% target
intraday_stop_loss: float = -0.025       # -2.5% stop

# Zone 1: Morning (9:30-10:00 AM)
zone1_take_profit: float = 0.03          # +3% target
zone1_stop_loss: float = -0.02           # -2% stop

# Zone 2: Midday (10:00 AM - 2:00 PM)
zone2_take_profit: float = 0.04          # +4% target
zone2_stop_loss: float = -0.03           # -3% stop

# Zone 3: Afternoon (2:00 PM - 3:45 PM)
zone3_take_profit: float = 0.025         # +2.5% target
zone3_stop_loss: float = -0.02           # -2% stop
```

**Conservative (take profits faster):**
```python
zone1_take_profit: float = 0.02          # +2% target
zone2_take_profit: float = 0.03          # +3% target
```

**Aggressive (let winners run):**
```python
zone1_take_profit: float = 0.05          # +5% target
zone2_take_profit: float = 0.06          # +6% target
```

---

### 🔟 TRAILING STOPS (Protect profits)

```python
trailing_trigger_pct: float = 0.03       # Activate at +3% profit
trailing_distance_pct: float = 0.02      # Trail 2% behind peak
trailing_min_profit_pct: float = 0.015   # Lock in +1.5% minimum
```

**Example:**
- Stock reaches +3% → trailing stop activates
- Stock continues to +5% → stop is now at +3% (2% behind)
- Stock drops back to +3% → exit with +3% profit
- Minimum profit locked: +1.5%

**Tighter trailing (take profits faster):**
```python
trailing_trigger_pct: float = 0.02       # Activate at +2%
trailing_distance_pct: float = 0.015     # Trail 1.5% behind
```

**Looser trailing (let winners run):**
```python
trailing_trigger_pct: float = 0.04       # Activate at +4%
trailing_distance_pct: float = 0.025     # Trail 2.5% behind
```

---

## 🗂️ STOCK UNIVERSE

### File: `config/short_cycle_universe.json`
**Location:** `/home/wes/Desktop/litebotx-usb-deployment/config/short_cycle_universe.json`

**Current stocks (70 total):**

```json
{
  "base_universe": [
    "PLTR", "SOFI", "RIVN", "HOOD", "SNAP",
    "PLUG", "FCEL", "BE", "TLRY", "CGC",
    "MARA", "RIOT", "COIN", "AMC", "GME",
    // ... 55 more stocks
  ]
}
```

**To add stocks:** Just add ticker symbols to the array  
**To remove stocks:** Delete ticker symbols from the array  
**To focus on sector:** Remove other sectors, keep your favorites

**Popular categories:**
- **Tech:** PLTR, SOFI, HOOD, DDOG, CRWD, ZS, NET
- **EV:** RIVN, NIO, LCID, XPEV
- **Crypto:** MARA, RIOT, COIN
- **Cannabis:** TLRY, CGC, SNDL
- **Meme:** AMC, GME, SPCE

---

## ⏰ TRADING SCHEDULE

### File: `small_portfolio_config.py`

```python
trading_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
exit_time: str = "15:45"                 # Exit by 3:45 PM
max_hold_days: int = 0                   # Same-day only (no overnight)
```

**To trade only certain days:**
```python
trading_days: List[str] = ["monday", "tuesday", "wednesday"]  # Mon-Wed only
```

**To allow overnight holds:**
```python
max_hold_days: int = 1                   # Can hold to next day (D+1)
exit_time: str = "15:50"                 # Exit near close
```

---

## 🔧 LATE ENTRY SETTINGS

### File: `small_portfolio_config.py`

```python
enable_all_day_entries: bool = True      # Allow entries after open
allow_late_entries_after_minutes: int = 30  # 10:00 AM earliest
all_day_entry_cutoff_time: str = "14:30"    # 2:30 PM latest
late_entry_check_interval_minutes: int = 5  # Check every 5 min
max_late_entries_per_day: int = 5           # Max 5 late entries
```

**To disable late entries:**
```python
enable_all_day_entries: bool = False
```

**To be more aggressive with late entries:**
```python
all_day_entry_cutoff_time: str = "15:00"    # Trade until 3 PM
max_late_entries_per_day: int = 10          # Allow more trades
```

---

## 📊 QUICK REFERENCE: PARAMETER LOCATIONS

| What You Want to Change | File | Lines |
|------------------------|------|-------|
| Portfolio size | `small_portfolio_config.py` | 25 |
| Position sizing | `small_portfolio_config.py` | 33-36 |
| Risk limits | `small_portfolio_config.py` | 39-43 |
| Stock price range | `small_portfolio_config.py` | 67-68 |
| Volatility filter | `small_portfolio_config.py` | 69-70 |
| Momentum filter | `small_portfolio_config.py` | 71-72 |
| Volume requirements | `small_portfolio_config.py` | 83-84 |
| Signal threshold | `small_portfolio_config.py` | 77 |
| Profit targets | `small_portfolio_config.py` | 100-120 |
| Trailing stops | `small_portfolio_config.py` | 123-125 |
| Trading days | `small_portfolio_config.py` | 129 |
| Stock universe | `config/short_cycle_universe.json` | 2-70 |

---

## 🚀 COMMON SCENARIOS

### Scenario 1: "I want fewer, higher-quality trades"
```python
confidence_threshold: float = 0.07       # Raise from 0.05 to 0.07
min_momentum: float = 0.05               # Raise from 0.03 to 0.05
max_positions_per_day: int = 2           # Lower from 3 to 2
```

### Scenario 2: "I want to be more aggressive"
```python
max_position_dollars: float = 400.0      # Raise from 300 to 400
max_risk_per_trade_dollars: float = 40.0 # Raise from 25 to 40
zone2_take_profit: float = 0.06          # Raise from 0.04 to 0.06
```

### Scenario 3: "I'm losing money, need to be safer"
```python
max_position_dollars: float = 200.0      # Lower from 300 to 200
max_risk_per_trade_dollars: float = 15.0 # Lower from 25 to 15
confidence_threshold: float = 0.08       # Raise from 0.05 to 0.08
zone1_take_profit: float = 0.02          # Lower from 0.03 to 0.02
```

### Scenario 4: "Can't find enough stocks to trade"
```python
min_price: float = 5.0                   # Lower from 10 to 5
max_price: float = 50.0                  # Raise from 30 to 50
min_avg_volume: int = 50_000             # Lower from 100K to 50K
confidence_threshold: float = 0.03       # Lower from 0.05 to 0.03
```

### Scenario 5: "Account grew to $5,000"
```python
portfolio_value: float = 5000.0          # Update from 1000
max_position_dollars: float = 1000.0     # Update from 300 (20%)
min_position_size_dollars: float = 200.0 # Update from 50 (4%)
max_positions_per_day: int = 5           # Update from 3
max_risk_per_trade_dollars: float = 125.0 # Update from 25 (2.5%)
max_price: float = 50.0                  # Can afford higher-priced stocks
```

---

## ⚠️ PARAMETERS TO NEVER CHANGE (Advanced Only)

**Don't touch these unless you really know what you're doing:**

```python
# Position multipliers (confidence-based sizing)
high_confidence_multiplier_min: float = 2.5
high_confidence_multiplier_max: float = 3.0
medium_confidence_multiplier_min: float = 1.8
medium_confidence_multiplier_max: float = 2.5

# Breakout detection (pattern recognition)
vol_spike_min: float = 0.7
breakout_min: float = 0.002
breakout_window: int = 10

# Settlement tracking (T+2 compliance)
enable_settlement_tracking: bool = True
settlement_days: int = 2
settlement_buffer_dollars: float = 50.0

# Monitoring intervals
intraday_monitor_interval_seconds: int = 120
late_entry_check_interval_minutes: int = 5
trailing_update_interval: int = 60
```

---

## 💾 HOW TO APPLY CHANGES

### Step 1: Stop the bot
```bash
pkill -f start_small_portfolio_trader.py
```

### Step 2: Edit the config file
```bash
nano small_portfolio_config.py
# OR
code small_portfolio_config.py  # If using VS Code
```

### Step 3: Save changes (Ctrl+O, then Ctrl+X in nano)

### Step 4: Restart the bot
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
nohup /home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python start_small_portfolio_trader.py > logs/bot_startup.log 2>&1 &
```

### Step 5: Verify it's running
```bash
ps aux | grep start_small_portfolio_trader.py | grep -v grep
tail -f logs/short_cycle_trader.log
```

---

## 🎯 SUGGESTED STARTING VALUES

**For beginners (conservative):**
```python
portfolio_value = 1000.0
max_position_dollars = 200.0        # 20% max
max_risk_per_trade_dollars = 15.0   # 1.5% risk
confidence_threshold = 0.07         # 7% (selective)
zone1_take_profit = 0.02            # +2% target
zone1_stop_loss = -0.015            # -1.5% stop
max_positions_per_day = 2           # Conservative
```

**For experienced traders (balanced):**
```python
portfolio_value = 1000.0
max_position_dollars = 300.0        # 30% max
max_risk_per_trade_dollars = 25.0   # 2.5% risk
confidence_threshold = 0.05         # 5% (balanced)
zone1_take_profit = 0.03            # +3% target
zone1_stop_loss = -0.02             # -2% stop
max_positions_per_day = 3           # Current settings
```

**For aggressive traders (higher risk):**
```python
portfolio_value = 1000.0
max_position_dollars = 400.0        # 40% max
max_risk_per_trade_dollars = 40.0   # 4% risk
confidence_threshold = 0.03         # 3% (permissive)
zone1_take_profit = 0.05            # +5% target
zone1_stop_loss = -0.03             # -3% stop
max_positions_per_day = 5           # More active
```

---

**Need help?** Check `docs/CURRENT_STATUS_AND_ROADMAP.md` for full context and explanations.
