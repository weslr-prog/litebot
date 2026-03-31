# Quick Start Guide: Cash Account Day Trading

**Ready to trade?** Here's your step-by-step guide to start using the new cash account features.

---

## ✅ Pre-Flight Checklist

Before you start trading, verify:

1. **API Keys Updated** ✅
   - New Alpaca API keys in `.env` file
   - Account verified as paper trading
   - $1,000 starting balance confirmed

2. **Tests Passing** ✅
   - Run: `python scripts/test_cash_account_features.py`
   - Should see: "🎉 ALL TESTS PASSED!"

3. **Bot Status Check** ✅
   - Run: `python scripts/bot_status.py`
   - Verify: Account shows $1,000.00

---

## 🚀 How to Start Trading

### Option 1: Use SmallPortfolioConfig (Recommended)

```python
from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCycleTrader

# This automatically enables cash account mode
config = SmallPortfolioConfig()

# Create trader
trader = ShortCycleTrader(config=config)

# Start trading
trader.run()
```

### Option 2: Start from Command Line

```bash
# Navigate to project directory
cd /home/wes/Desktop/litebotx-usb-deployment

# Activate environment
source litebotx_env/bin/activate

# Run the bot (TODO: Create launcher script)
python start_small_portfolio_trader.py
```

---

## 📊 What to Expect First Week

### Day 1-2: Light Trading
- **Trades:** 2-3 per day
- **Hold Time:** Mix of same-day + overnight
- **Target:** 1-2% daily return
- **Goal:** Verify same-day exits work

### Day 3-4: Increase Activity
- **Trades:** 3-5 per day
- **Hold Time:** More same-day exits
- **Target:** 2-3% daily return
- **Goal:** Test re-entry capability

### Day 5: Week Review
- **Total Trades:** 15-20
- **Win Rate:** Target >55%
- **Weekly Return:** Target 10%+
- **Goal:** Confirm no violations

---

## 🔍 What to Monitor

### Every Day:
```bash
# Check bot status
python scripts/bot_status.py

# Should show:
# - Today's P&L
# - Open positions
# - Cash available
```

### Every Trade:
Look in logs for:
- ✅ "Cash account can exit same day" (no PDT blocks)
- ✅ Position entries/exits
- ⚠️ "VIOLATION RISK" warnings (should be rare)

### End of Week:
```bash
# Review performance
python scripts/analyze_current_performance.py

# Should show:
# - Win rate >55%
# - Weekly return 10%+
# - 15+ closed trades
```

---

## ⚠️ Important Rules

### DO:
✅ Exit winners same day (take profits fast)  
✅ Re-enter after losses (second chances)  
✅ Trade 2-5 times per day  
✅ Monitor unsettled cash  
✅ Keep $50 buffer untouched  

### DON'T:
❌ Trade with 100% of capital  
❌ Ignore violation warnings  
❌ Sell before settlement (T+2)  
❌ Overtrade (>10 trades/day)  
❌ Hold losers too long  

---

## 🆘 Troubleshooting

### "PDT BLOCK" messages in logs
**Problem:** Old PDT logic still activating  
**Solution:** Verify `cash_account_mode=True` in config  
**Check:** `python scripts/test_cash_account_features.py`

### "VIOLATION RISK" warnings
**Problem:** Using too much unsettled cash  
**Solution:** Wait for T+2 settlement or use less capital  
**Check:** Review `settlement_tracker` output

### No same-day exits
**Problem:** `enable_same_day_exit=False`  
**Solution:** Use `SmallPortfolioConfig()` which sets it True  
**Check:** Print `config.enable_same_day_exit`

### Too few trades
**Problem:** Universe too restrictive  
**Solution:** Check pre-filter settings in config  
**Check:** Look for "candidates pass" in logs

---

## 📈 Performance Targets

### Week 1 (Learning Phase):
- **Trades:** 15-20
- **Win Rate:** 50-55%
- **Weekly ROI:** 5-10%
- **Focus:** Verify features work

### Week 2 (Optimization):
- **Trades:** 20-25
- **Win Rate:** 55-60%
- **Weekly ROI:** 10-15%
- **Focus:** Fine-tune exits

### Week 3 (Scaling):
- **Trades:** 25-30
- **Win Rate:** 60%+
- **Weekly ROI:** 15-20%
- **Focus:** Add scalping

### Month 1 Goal:
- **Monthly ROI:** 30-40%
- **Portfolio:** $1,000 → $1,300-$1,400
- **Win Rate:** 55-60%
- **Confidence:** High

---

## 🎯 Quick Commands Reference

```bash
# Test features
python scripts/test_cash_account_features.py

# Check bot status (operational + financial)
python scripts/bot_status.py

# Detailed performance analysis
python scripts/analyze_current_performance.py

# View comprehensive evaluation
python scripts/comprehensive_performance_evaluation.py

# Check settlement tracker demo
python settlement_tracker.py

# Run bot (TODO: create launcher)
python start_small_portfolio_trader.py
```

---

## 💡 Pro Tips

1. **Start Small:** First week, aim for 2-3 trades/day max
2. **Track Everything:** Note why you entered and exited each trade
3. **Review Daily:** End of day, check what worked and what didn't
4. **Adjust Weekly:** Based on results, tweak profit targets
5. **Preserve Capital:** Never risk >5% on any single trade

---

## 📞 Need Help?

### Check These First:
1. `docs/CASH_ACCOUNT_DAY_TRADING_PLAN.md` - Full strategy
2. `docs/PHASE1_IMPLEMENTATION_COMPLETE.md` - What was built
3. Test script output - Automated diagnostics
4. Bot logs - `logs/short_cycle_trader.log`

### Common Issues Solved:
- **No trades executing:** Check market hours, verify API keys
- **PDT blocks:** Confirm cash_account_mode=True
- **Violation warnings:** Wait for T+2 or reduce position size
- **Low returns:** Increase trade frequency or profit targets

---

**🎉 You're Ready! Let's Make Some Money!** 🚀

Start with small positions, monitor closely, and scale up as you gain confidence. The bot is now optimized for cash account day trading with unlimited potential!

Good luck! 📈
