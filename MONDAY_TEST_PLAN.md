# Monday Test Plan - November 10, 2025
## Weekend Development Validation Checklist

**Session Goal:** Validate all weekend fixes and enhancements in live paper trading

---

## 🌅 Pre-Market Checklist (9:00-9:30 AM)

### 1. System Startup Verification
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
source litebotx_env/bin/activate
python3 start_small_portfolio_trader.py
```

**Expected Output:**
- ✅ Configuration loaded: small_portfolio_config.py
- ✅ Earnings calendar initialized (3-day blackout, 1-day buffer)
- ✅ Gap detection ready (9:30-9:45 AM window)
- ✅ Position sizing uses fractional shares
- ✅ Loaded 40 positions from previous session

### 2. Log Monitoring Setup
```bash
# Terminal 1: Main trading logs
tail -f trading_bot.log | grep -E "(EARNINGS|GAP|Position sizing|shares @)"

# Terminal 2: Error monitoring
tail -f trading_bot.log | grep -E "(ERROR|CRITICAL|FAILED)"

# Terminal 3: Signal tracking
tail -f trading_bot.log | grep -E "(signal|confidence|BLOCKING|FORCE EXIT)"
```

### 3. Pre-Flight Checks
- [ ] Check bot loaded all 40 positions correctly
- [ ] Verify current watchlist is fresh (<6 hours old)
- [ ] Confirm portfolio value is correct (~$1,000)
- [ ] Review any Friday positions that need D+1 exit today

---

## 🔔 Market Open Window (9:30-9:45 AM)

### Gap Risk Management Validation

**What to Watch:**
- Bot should run `_check_morning_gaps()` automatically
- Check logs for gap detection messages

**Log Patterns to Monitor:**
```bash
# Gap down exits
grep "GAP DOWN" trading_bot.log

# Gap up profit-taking
grep "GAP UP" trading_bot.log

# Timing window confirmation
grep "Morning gap" trading_bot.log
```

**Expected Behavior:**
1. **Gap Down >= -3%:** Auto-exit with reason "GAP_DOWN_X.X%"
   - Example: RIVN gaps down -4% → Exit immediately
   
2. **Gap Up >= +5%:** Take profit with reason "GAP_UP_X.X%"
   - Example: PLTR gaps up +7% → Exit immediately
   
3. **Normal Gaps:** No action, position continues
   - Example: SOFI gaps up +1.5% → Hold as normal

**Validation Commands:**
```bash
# Check if any gaps were detected
grep -E "GAP (DOWN|UP)" trading_bot.log | tail -20

# Verify timing (should only be 9:30-9:45 AM)
grep "gap" trading_bot.log | grep -E "09:3[0-4]|09:4[0-5]"
```

---

## 📊 Full Trading Day (9:30 AM - 4:00 PM)

### Feature Validation Matrix

#### 1. Position Sizing Fix (CRITICAL)
**Test Case:** Bot finds a signal with entry price > $200

**What to Watch:**
```bash
grep "Position sizing" trading_bot.log | tail -10
```

**Expected:**
- ✅ Returns fractional shares (e.g., "0.8 shares @ $250")
- ❌ NOT "0 shares" or "$0 position too small"

**Validation:**
```bash
# Should see fractional shares
grep "shares @" trading_bot.log | grep -E "0\.[0-9]+ shares"

# Should NOT see rejections due to $0
grep "REJECTED - Position size too small (0 shares)" trading_bot.log
```

#### 2. Earnings Protection
**Test Cases:**

**A. Entry Blocking (3-day blackout)**
```bash
# Check for earnings blocks
grep "BLOCKING ENTRY - Earnings" trading_bot.log
```

**Expected:**
- If NVDA (Nov 19) appears: Should trade normally (12 days out)
- If any stock has earnings Nov 10-13: Should block with message
  - Example: "❌ TSLA: BLOCKED - 🚫 BLOCK ENTRIES - Earnings in 2 day(s)"

**B. Forced Exits (1-day buffer)**
```bash
# Check for earnings exits
grep "FORCE EXIT - Earnings" trading_bot.log
```

**Expected:**
- Any position with earnings Nov 11 → Force exit today
- Log: "⚠️ SYMBOL: EARNINGS EXIT - ⚠️ FORCE EXIT - Earnings in 1 day(s)"

**Validation:**
```bash
# Test with real stocks
python3 -c "
from earnings_calendar import EarningsCalendar
cal = EarningsCalendar()
for sym in ['NVDA', 'TSLA', 'AAPL', 'PLTR', 'SOFI']:
    info = cal.get_earnings_info(sym)
    print(f'{sym}: {info[\"status\"]}')
"
```

#### 3. D+1 Exit Sequencing
**What to Watch:**
```bash
grep "Strategic exit sequence" trading_bot.log
```

**Expected Priority Order:**
1. **EARNINGS_URGENT** exits first (if any)
2. Then oldest positions (most days held)
3. 30-60 second delays between exits

**Validation:**
- [ ] Earnings exits happen before regular D+1 exits
- [ ] Exits are spaced out (not all at once)
- [ ] Each exit has clear reason logged

---

## 🔍 Hourly Monitoring Checklist

### Every Hour (10:00 AM, 11:00 AM, 12:00 PM, 1:00 PM, 2:00 PM, 3:00 PM)

```bash
# Quick status check
python3 -c "
import json
with open('positions.json', 'r') as f:
    positions = json.load(f)
print(f'Open positions: {len([p for p in positions if p[\"status\"] == \"entered\"])}')
print(f'Exited today: {len([p for p in positions if \"2025-11-10\" in str(p.get(\"exit_date\", \"\"))])}')
"
```

**Check for:**
- [ ] No stuck positions (status should update)
- [ ] No ERROR messages piling up
- [ ] Signal generation working (should see attempts)
- [ ] Position sizing returning valid shares

---

## 📈 End-of-Day Review (4:00-5:00 PM)

### Performance Summary
```bash
# Generate daily report
grep "Daily Report" trading_bot.log | tail -1

# Check all exits
grep "exit" trading_bot.log | grep "2025-11-10"

# Count signal attempts
grep "confidence:" trading_bot.log | wc -l

# Count rejections
grep "REJECTED\|BLOCKED" trading_bot.log | wc -l
```

### Feature Effectiveness

#### Position Sizing
```bash
# Count fractional share entries
grep "shares @" trading_bot.log | grep -E "0\.[0-9]+ shares" | wc -l

# Expected: At least 1 if expensive stock signaled
```

#### Earnings Protection
```bash
# Count earnings blocks
grep "BLOCKING ENTRY - Earnings" trading_bot.log | wc -l

# Count earnings exits
grep "EARNINGS EXIT" trading_bot.log | wc -l
```

#### Gap Management
```bash
# Count gap exits
grep -E "GAP (DOWN|UP)" trading_bot.log | wc -l

# Should be 0 if no large gaps today
```

### Success Criteria
- ✅ Bot ran full day without crashes
- ✅ Position sizing returned non-zero for all signals
- ✅ Earnings blocks logged correctly (if applicable)
- ✅ Gap detection ran only 9:30-9:45 AM
- ✅ D+1 exits executed in proper sequence
- ✅ No ERROR messages in critical paths

---

## 🚨 Rollback Procedure (If Needed)

If critical issues appear:

### 1. Immediate Stop
```bash
# Stop the bot
python3 stop_litebotx.py
```

### 2. Restore Previous Version
```bash
# The pre-weekend bot is in backups
cd /home/wes/Desktop/litebotx-usb-deployment

# Check backup date
ls -lh backups/ | tail -5

# If needed, restore traders/short_cycle_trader.py from backup
# (Manual step - only if absolutely necessary)
```

### 3. Restart with Previous Code
```bash
# Undo earnings calendar integration
# Undo gap detection integration
# Keep position sizing fix (it's critical)
```

---

## 📊 Metrics to Track

### Baseline (Pre-Weekend)
- **Friday Nov 7:** 0 entries, 0 exits
- **Reason:** Position sizing bug + Friday freeze

### Monday Goals
- **Entries:** 1-2 (if good signals appear)
- **Position Sizing:** ALL entries should have valid shares (>0)
- **Earnings Blocks:** Log any earnings-related decisions
- **Gap Exits:** Should trigger if any large gaps

### Win Criteria
1. ✅ At least 1 position entered with fractional shares
2. ✅ No "0 shares @ $0" rejections
3. ✅ Earnings calendar checks logged
4. ✅ Gap detection runs 9:30-9:45 AM only
5. ✅ D+1 exits execute smoothly

---

## 🔧 Debug Commands

### Check Current State
```bash
# Portfolio value
python3 -c "
from connect_real_trading import RealPaperTradingEngine
engine = RealPaperTradingEngine()
account = engine.get_account_status()
print(f'Portfolio: \${account[\"portfolio_value\"]:.2f}')
print(f'Cash: \${account[\"cash\"]:.2f}')
"
```

### Test Earnings Calendar Manually
```bash
python3 earnings_calendar.py
```

### Test Position Sizing Manually
```bash
python3 test_position_sizing.py
```

### Check Gap Detection
```bash
# During 9:30-9:45 AM
python3 -c "
from traders.short_cycle_trader import ShortCycleTrader
from small_portfolio_config import SmallPortfolioConfig
trader = ShortCycleTrader(SmallPortfolioConfig())
gaps = trader._check_morning_gaps()
print(f'Gap exits: {gaps}')
"
```

---

## 📝 Notes Section

### Issues Found
(Document any issues discovered during testing)

### Observations
(Note any interesting behaviors or patterns)

### Next Steps
(Action items for future improvement)

---

**Remember:** This is paper trading. We can afford to let it run and observe. The goal is to validate all 6 weekend enhancements work correctly in the live environment.

**Key Focus Areas:**
1. Position sizing returns valid shares
2. Earnings protection blocks/exits as expected
3. Gap detection only runs during market open window
4. All systems integrate smoothly without conflicts

**End of Test Plan**
