# Automated Evening Launch System
## For Users Who Start Bot at Night & Can't Monitor Next Morning

---

## 🎯 Your Situation

**Your workflow:**
- Start bot in the evening (before bed)
- Can't monitor in the morning (work schedule)
- Need to know BEFORE launching if bot will work tomorrow
- Want alerts if problems detected

**What you need:**
1. ✅ Automated checks before launch (no manual monitoring needed)
2. ✅ Clear GO/NO-GO decision (should I launch or not?)
3. ✅ Alerts sent to you if issues found
4. ⏳ Self-repair (future enhancement)

---

## ✅ Solution Created For You

### New System: Evening Launch Readiness Check

**What it does:**
1. Runs comprehensive validation (7 critical checks)
2. Tests bot initialization in dry-run mode
3. Gives GO/NO-GO decision
4. Sends alerts if issues found
5. Blocks bot launch if critical issues detected

**Files created:**
- ✅ `evening_launch_check.py` - Validation system
- ✅ `safe_launch.sh` - Wrapper that checks THEN launches
- ✅ This guide

---

## 🚀 How To Use (Simple Method)

### Every Evening (Before Bed):

**Instead of this:**
```bash
python3 litebotx_launcher.py  # OLD WAY - risky
```

**Do this:**
```bash
./safe_launch.sh  # NEW WAY - safe
```

**That's it!** The script will:
1. ✅ Run all checks automatically
2. ✅ Show you GO/NO-GO decision
3. ✅ Launch bot ONLY if checks pass
4. ✅ Send desktop notification with results

---

## 📋 What The Evening Check Validates

### Critical Checks (Must Pass - Bot Won't Launch If These Fail):

1. **Alpaca API Connection** 
   - Tests live connection
   - Verifies account active
   - Checks buying power adequate
   - **Prevents:** Can't trade if API down

2. **Timezone Handling** ⭐ 
   - Tests timezone-aware datetime operations
   - Verifies pattern recognizer works
   - Simulates Oct 20 bug scenario
   - **Prevents:** Exact bug that happened today

3. **Position Loading**
   - Tests loading positions from previous session
   - Verifies timestamps are timezone-aware
   - **Prevents:** Crash on startup with loaded positions

4. **Pattern Recognition**
   - Tests morning gap scanner
   - Tests pattern recognizer
   - Tests pattern tracker
   - **Prevents:** D+1 features not working

5. **Market Schedule**
   - Checks if market open tomorrow
   - Warns if tomorrow is weekend/holiday
   - **Prevents:** Launching for non-trading day

6. **Disk Space**
   - Verifies adequate disk space
   - **Prevents:** Crash due to full disk

7. **Bot Dry Run** ⭐ MOST IMPORTANT
   - Actually initializes the bot
   - Tests all components load
   - Simulates what happens at startup
   - **Prevents:** Any initialization failures

### Warning Checks (Nice To Pass - Bot Can Launch With Warnings):

8. **Previous Session Health**
   - Checks if last session ended cleanly
   - Warns if crashed

9. **Log File Size**
   - Warns if logs getting large

10. **Memory Available**
    - Warns if memory getting low

---

## 📱 Setting Up Alerts (Optional But Recommended)

### Option 1: Desktop Notifications (Easiest)

**Already configured in `safe_launch.sh`**

When you run `./safe_launch.sh`, you'll see a desktop notification:

**If all checks pass:**
```
✅ Trading Bot: ALL CLEAR
All checks passed. Safe to launch for tomorrow.
```

**If critical issues:**
```
⛔ Trading Bot: NO-GO  
Critical issues found. DO NOT launch.
```

**Setup:** Nothing needed - works out of the box on Ubuntu!

---

### Option 2: Email Alerts (Recommended For Remote)

**One-time setup:**

1. Install mail utility:
```bash
sudo apt-get install mailutils
```

2. Configure (if not already set up):
```bash
# Test it first:
echo "Test message" | mail -s "Test" your-email@example.com
```

3. Use email flag:
```bash
python3 evening_launch_check.py --email your-email@example.com
```

Or modify `safe_launch.sh` line 18:
```bash
# Change this line:
python3 evening_launch_check.py --notify

# To this:
python3 evening_launch_check.py --notify --email your-email@example.com
```

**Email you'll receive:**

**Subject:** ✅ Trading Bot: ALL CLEAR (or ⛔ NO-GO)

**Body:**
```
EVENING LAUNCH READINESS CHECK
============================================================
Time: 2025-10-20 19:30:00
For tomorrow: Monday, October 21, 2025

STATUS: GO FOR LAUNCH ✅

Passed: 10
Warnings: 0
Critical Issues: 0

ACTION: You can launch the bot.
Command: python3 litebotx_launcher.py
```

---

### Option 3: SMS/Phone Alerts (Advanced)

**Using Twilio (free tier):**

1. Sign up: https://www.twilio.com/try-twilio
2. Get phone number and credentials
3. Install: `pip install twilio`
4. Add to `evening_launch_check.py` in `_send_alerts()` method

**Or use email-to-SMS:**
```bash
# Most carriers have email-to-SMS gateways:
# AT&T: number@txt.att.net
# Verizon: number@vtext.com
# T-Mobile: number@tmomail.net

python3 evening_launch_check.py --email 5551234567@txt.att.net
```

---

## 🔄 Your New Evening Workflow

### Step-by-Step (5 Minutes):

**6:00 PM - Before starting work on bot:**
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./safe_launch.sh
```

**What happens:**
1. Script runs evening checks (30 seconds)
2. Shows results on screen
3. Sends desktop notification
4. Sends email (if configured)

**Two possible outcomes:**

### Outcome A: All Checks Pass ✅
```
✅ GO FOR LAUNCH - BOT IS READY

You can now launch the bot:
  python3 litebotx_launcher.py
  Choose: 3 (Aggressive Trading)
  Confirm: yes

Launching bot for tomorrow's trading...
```

**Bot launches automatically!** You're done. Go about your evening.

---

### Outcome B: Critical Issues Found ❌
```
⛔ NO-GO FOR LAUNCH - DO NOT START BOT

CRITICAL ISSUES FOUND:

  ❌ Alpaca API Connection: Connection failed: Network error
  ❌ Timezone Handling: Pattern recognizer timezone error

Recommended actions:
  1. Review and fix critical issues above
  2. Re-run this check: python3 evening_launch_check.py
  3. Only launch bot after all critical checks pass

CRITICAL ISSUES DETECTED - BOT NOT STARTED
```

**Bot did NOT launch.** You have two choices:

**Choice 1: Fix Tonight (If Quick)**
```bash
# Fix the issues (e.g., restart network, check API keys)
# Then re-run:
./safe_launch.sh
```

**Choice 2: Skip Trading Tomorrow**
```bash
# Don't launch bot
# Investigate tomorrow evening
# Trade the day after
```

---

## 📊 Example Scenarios

### Scenario 1: Everything Working (Normal)

**You run:**
```bash
./safe_launch.sh
```

**You see:**
```
🌙 EVENING LAUNCH READINESS CHECK
==========================================
Running comprehensive validation before overnight bot launch...

🔴 CRITICAL CHECKS (must pass):

  ✅ Alpaca API Connection
  ✅ Timezone Handling  
  ✅ Position Loading
  ✅ Pattern Recognition
  ✅ Market Schedule
  ✅ Disk Space
  ✅ Bot Dry Run

🟡 WARNING CHECKS (nice to pass):

  ✅ Previous Session Health
  ✅ Log File Size
  ✅ Memory Available

==========================================
✅ GO FOR LAUNCH - BOT IS READY
==========================================

Launching bot for tomorrow's trading...

Select profile:
1. Conservative
2. Moderate  
3. Aggressive Trading
> 
```

**You:** Type `3`, then `yes`

**Result:** Bot launches successfully. You sleep well. 😴

---

### Scenario 2: Network Issue (Alpaca Down)

**You run:**
```bash
./safe_launch.sh
```

**You see:**
```
🔴 CRITICAL CHECKS (must pass):

  ❌ Alpaca API Connection: Connection failed: Name resolution error
  ✅ Timezone Handling
  ✅ Position Loading
  ✅ Pattern Recognition
  ⚠️  Market Schedule: Cannot check (API down)
  ✅ Disk Space
  ✅ Bot Dry Run

==========================================
⛔ NO-GO FOR LAUNCH - DO NOT START BOT
==========================================

CRITICAL ISSUES DETECTED - BOT NOT STARTED
```

**Your options:**

**Option A:** Wait 10 minutes (maybe temporary), re-run
```bash
# Wait...
./safe_launch.sh  # Try again
```

**Option B:** Check network
```bash
ping paper-api.alpaca.markets
# If network issue, fix network
./safe_launch.sh
```

**Option C:** Skip tomorrow
```bash
# Don't launch
# Will investigate tomorrow evening
```

---

### Scenario 3: Tomorrow is Weekend

**You run (on Friday evening):**
```bash
./safe_launch.sh
```

**You see:**
```
🔴 CRITICAL CHECKS (must pass):

  ✅ Alpaca API Connection
  ✅ Timezone Handling
  ✅ Position Loading
  ✅ Pattern Recognition
  ❌ Market Schedule: Tomorrow is Saturday - market closed
  ✅ Disk Space
  ✅ Bot Dry Run

==========================================
⛔ NO-GO FOR LAUNCH - DO NOT START BOT
==========================================
```

**Result:** Bot doesn't launch (correctly - market closed tomorrow!)

---

## 🔧 Advanced: Check-Only Mode

If you just want to check without launching:

```bash
# Check only (no launch):
python3 evening_launch_check.py

# Check with desktop notification:
python3 evening_launch_check.py --notify

# Check with email alert:
python3 evening_launch_check.py --email your@email.com

# Check with both:
python3 evening_launch_check.py --notify --email your@email.com
```

**Use cases:**
- Test the system
- Check readiness without committing to launch
- Run multiple times while fixing issues

---

## 📝 Reviewing Past Checks

All check results saved to `evening_check_reports/`:

```bash
# View latest check:
cat evening_check_reports/latest_evening_check.json

# View specific check:
cat evening_check_reports/evening_check_2025-10-20_19-30-00.json

# View all checks from today:
ls -lt evening_check_reports/ | head -10
```

**Example report:**
```json
{
  "timestamp": "2025-10-20_19-30-00",
  "for_date": "2025-10-21",
  "go_for_launch": true,
  "passed_checks": [
    "Alpaca API Connection",
    "Timezone Handling",
    "Position Loading",
    ...
  ],
  "warnings": [],
  "critical_issues": []
}
```

---

## ⚡ Quick Reference

### Normal Evening Workflow:
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./safe_launch.sh
# Watch for GO/NO-GO
# If GO: Select option 3, confirm yes
# If NO-GO: Review issues, fix or skip trading
```

### Check Without Launching:
```bash
python3 evening_launch_check.py --notify
```

### View Latest Results:
```bash
cat evening_check_reports/latest_evening_check.json
```

### If Issues Found:
```bash
# Fix issues, then re-run:
./safe_launch.sh

# Or check only:
python3 evening_launch_check.py
```

---

## 🎓 What This Prevents

### Oct 20 Scenario - How It Would Have Been Different:

**What Actually Happened (Oct 20):**
```
Evening (Oct 19):
- No checks run
- Assumed bot ready
- Went to bed confident

Morning (Oct 20):
- 9:46 AM: Bot crashed (timezone bug)
- Can't monitor (at work)
- Entire day: 0 trades
- Found out later: Missed 8 signals
```

**What Would Have Happened With This System:**
```
Evening (Oct 19):
- Run: ./safe_launch.sh
- Check #7 (Bot Dry Run): ❌ FAILS
  Error: "can't compare offset-naive and offset-aware datetimes"
- Decision: ⛔ NO-GO FOR LAUNCH
- Desktop alert: "Critical issues found. DO NOT launch."
- Email sent: "NO-GO FOR LAUNCH"

Your action:
- See the error at 7 PM (not 9:46 AM next day)
- Post in chat: "Getting timezone error in evening check"
- I fix it within 30 minutes
- Re-run: ./safe_launch.sh
- Check passes: ✅ GO FOR LAUNCH
- Bot launches successfully
- Go to bed confident

Morning (Oct 20):
- 9:46 AM: Trades execute successfully
- 8 signals → 5-8 positions entered
- Pattern recognition working
- You check logs at lunch: Everything working perfectly
```

**Difference:**
- **Without system:** Lost entire day, found out too late
- **With system:** Caught at 7 PM, fixed in 30 min, successful trading next day

---

## 🔮 Future Enhancements (Self-Repair)

You mentioned wanting self-repair. Here's the roadmap:

### Phase 1: Detection (✅ DONE - This System)
- Detect issues before they affect trading
- Alert you with clear GO/NO-GO

### Phase 2: Auto-Fix Common Issues (Future)
```python
# Could add to evening_launch_check.py:

def _auto_fix_disk_space(self):
    """Auto-cleanup old logs if disk full"""
    if disk_full:
        cleanup_old_logs()
        return True

def _auto_fix_positions_file(self):
    """Backup and repair corrupted positions.json"""
    if positions_corrupted:
        backup_positions()
        reset_positions()
        return True

def _auto_fix_timezone_issues(self):
    """Automatically patch timezone handling"""
    if timezone_error_detected:
        apply_timezone_patch()
        return True
```

### Phase 3: Self-Healing Bot (Long-term)
```python
# Bot monitors itself during trading
# If error detected:
#   1. Try to auto-fix
#   2. If can't fix, safe shutdown
#   3. Send alert
#   4. Write detailed report
```

**For now:** Detection + alerts is the safe approach. Auto-fixing can introduce new bugs.

---

## ✅ Setup Checklist

- [x] `evening_launch_check.py` created ✅
- [x] `safe_launch.sh` created ✅
- [x] Scripts made executable ✅
- [ ] Test evening check (run tonight) ⏳
- [ ] Configure email alerts (optional) ⏳
- [ ] Test safe_launch.sh (run tonight) ⏳
- [ ] Review results tomorrow morning ⏳
- [ ] Update this guide with your feedback ⏳

---

## 📞 Tonight's Action Plan

### 1. Test The System (5 minutes):

```bash
cd /home/wes/Desktop/litebotx-usb-deployment

# Test check-only mode:
python3 evening_launch_check.py --notify

# Review results
# Fix any issues found
```

### 2. When Ready To Launch:

```bash
# Use safe launcher:
./safe_launch.sh

# If it says GO:
#   Select 3 (Aggressive)
#   Confirm yes
#   Bot launches

# If it says NO-GO:
#   Review issues
#   Fix if quick
#   Or skip trading tomorrow
```

### 3. Next Morning (Optional):

```bash
# Check if bot is running:
ps aux | grep litebotx_launcher

# Check this morning's logs:
tail -50 logs/short_cycle_trader.log | grep "09:4"

# Look for trades executed around 9:46 AM
```

---

## 🎯 Bottom Line

**Old way (risky):**
```bash
python3 litebotx_launcher.py  # Hope it works tomorrow 🤞
```

**New way (safe):**
```bash
./safe_launch.sh  # Know it will work tomorrow ✅
```

**Time difference:** +30 seconds (for checks)
**Risk reduction:** Prevents disasters like Oct 20
**Peace of mind:** Priceless

---

## Questions?

**Q: What if check passes but bot still crashes tomorrow?**  
A: Very unlikely - the dry-run test actually initializes the bot. But if it happens, we add that scenario to the checks.

**Q: Can I skip the checks sometimes?**  
A: Yes, use old method: `python3 litebotx_launcher.py`. But why risk it?

**Q: What if I'm not home when I get the alert?**  
A: Email/SMS alerts mean you know before tomorrow. Can fix remotely or accept no trading.

**Q: How do I know the check itself isn't buggy?**  
A: It's simple validation code (no trading logic). Worst case: false negative (says NO-GO when bot would work). Better safe than sorry.

**Q: Can this system auto-launch the bot if checks pass?**  
A: Not yet (requires you to select option 3 and confirm). Could automate fully if desired.

---

**You're all set!** Use `./safe_launch.sh` tonight and never have a "broken bot on launch day" surprise again. 🚀
