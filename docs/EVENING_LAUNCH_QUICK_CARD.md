# 🌙 EVENING BOT LAUNCH - QUICK CARD

## Every Evening Before Launching Bot:

### ONE COMMAND:
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./safe_launch.sh
```

---

## What Happens:

### ✅ If All Checks Pass (GO):
```
✅ GO FOR LAUNCH - BOT IS READY

Launching bot...
Select profile: 3 (Aggressive)
Confirm: yes
```
**→ Bot launches. You're done! 😴**

---

### ❌ If Issues Found (NO-GO):
```
⛔ NO-GO FOR LAUNCH - DO NOT START BOT

CRITICAL ISSUES:
  ❌ Alpaca API Connection: Network error
  ❌ Bot Dry Run: Initialization failed
```

**→ Bot does NOT launch. You must decide:**

**Option A:** Quick fix possible
```bash
# Fix the issue
./safe_launch.sh  # Try again
```

**Option B:** Complex issue
```
Don't launch bot tonight
Skip trading tomorrow
Fix tomorrow evening
```

---

## Desktop Notification You'll See:

**All good:**
```
✅ Trading Bot: ALL CLEAR
All checks passed. Safe to launch.
```

**Problems:**
```
⛔ Trading Bot: NO-GO
Critical issues found. DO NOT launch.
[Details of issues]
```

---

## Emergency: Check Failed But Bot Already Running?

```bash
# Stop the bot immediately:
pkill -f litebotx_launcher

# Review what went wrong:
tail -100 logs/short_cycle_trader.log

# Fix issues before trying again
```

---

## Optional: Email Alerts

**Add to command:**
```bash
# Edit safe_launch.sh line 18:
python3 evening_launch_check.py --notify --email your@email.com
```

---

## What Gets Checked (7 Critical Tests):

1. ✅ **Alpaca API** - Can connect to broker
2. ✅ **Timezone Handling** - Oct 20 bug check
3. ✅ **Position Loading** - Previous session data
4. ✅ **Pattern Recognition** - D+1 features work
5. ✅ **Market Schedule** - Tomorrow is trading day
6. ✅ **Disk Space** - Not full
7. ✅ **Bot Dry Run** - Initialization test ⭐

---

## Files Created:

- `safe_launch.sh` - Use this to launch
- `evening_launch_check.py` - The validation system  
- `AUTOMATED_EVENING_LAUNCH_GUIDE.md` - Full documentation

---

## Key Rule:

**ALWAYS use `./safe_launch.sh` instead of `python3 litebotx_launcher.py`**

30 seconds of checks → Prevents hours of debugging

---

## Tomorrow Morning (Can't Monitor):

**Don't worry!** The evening check simulated everything.

**Optional quick check at lunch:**
```bash
# Check if trades happened:
ssh your-computer  # If remote
tail -20 logs/short_cycle_trader.log | grep "Trade executed"
```

---

## Troubleshooting:

**"Permission denied" error:**
```bash
chmod +x safe_launch.sh evening_launch_check.py
```

**"No such file" error:**
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
pwd  # Confirm you're in right directory
```

**Check keeps failing:**
```bash
# Run check-only to see details:
python3 evening_launch_check.py

# View report:
cat evening_check_reports/latest_evening_check.json
```

---

## Contact/Help:

**Check reports saved here:**
```
evening_check_reports/latest_evening_check.json
```

**Full guide:**
```
AUTOMATED_EVENING_LAUNCH_GUIDE.md
```

---

**Print This Card | Keep It Handy | Never Launch Without Checking**

---

Last updated: Oct 20, 2025  
System prevents: Broken bot launches (like Oct 20 timezone bug)  
Time cost: +30 seconds  
Peace of mind: Priceless ✅
