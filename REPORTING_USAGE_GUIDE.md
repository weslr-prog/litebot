# Reporting System Usage Guide

## Overview

Your bot now has **automated daily reporting** with morning briefs and end-of-day summaries.

---

## 📅 Automated Reports

### Morning Market Brief (9:00 AM ET)
**Runs automatically** when bot starts premarket phase.

**Shows**:
- Market conditions (SPY, VIX)
- Setup quality (1-5 stars)
- Oversold stock count  
- Expected trade count for the day
- Top 5 premarket gaps with RSI

**Purpose**: Know if today is a "hunting day" or "patience day"

---

### Daily Summary (4:30 PM ET)
**Runs automatically** during postmarket phase.

**Shows**:
- Today's trading activity (scans, candidates, signals, entries)
- P&L (realized + unrealized)
- Rejection breakdown (why stocks were skipped)
- Week-to-date stats (trades, win rate, portfolio value)
- Next session info

**Purpose**: Track daily progress and confirm bot discipline

---

## 🖥️ Manual Reports

### View Morning Brief Anytime
```bash
python3 view_reports.py morning
```

### View Daily Summary (Overview)
```bash
python3 view_reports.py daily
```

### View Daily Summary (With Full Details)
```bash
python3 view_reports.py daily -d
```

**Details include**:
- All entries today (with entry prices, RSI, gaps)
- All exits today (with P&L, hold times, exit reasons)
- All open positions (with unrealized P&L, hold days)

---

## 📊 Report Examples

### Morning Brief Example
```
🌅 MORNING MARKET BRIEF - Friday, Jan 3, 2026

MARKET CONDITIONS:
  • VIX: 18.2 (↑ from 16.5 yesterday) ✅ Good volatility
  • SPY: -0.8% (morning gap down) ✅ Dip-buy opportunity
  • Oversold stocks (RSI<35): 14/280 (5%) ⚠️ Below average

MEAN REVERSION SETUP:
  • Quality: ⭐⭐⭐☆☆ (3/5 stars)
  • Reason: Moderate oversold, good volatility
  • Expected trades: 1-3 positions today
  • Confidence: Moderate

PREMARKET GAPS (Top 5):
  1. RIVN: -4.2% (weekend news) 📊 RSI: 28 ✅
  2. COIN: -3.8% (sector weakness) 📊 RSI: 31 ✅
  3. UPST: -3.1% (sympathy move) 📊 RSI: 38 ⚠️
  4. LYFT: -2.9% (gap reversal setup) 📊 RSI: 33 ✅
  5. SOFI: -2.7% (tech rotation) 📊 RSI: 29 ✅

BOT STATUS: 🟢 Active | Next scan: 9:45 AM
```

### Daily Summary Example
```
📊 DAILY SUMMARY - Friday, Jan 3, 2026

MARKET PERFORMANCE:
  • SPY: +0.2% 📈
  • VIX: -1.1 ↓
  • Mean reversion setup: ⭐⭐⭐⭐☆ (4/5)

TRADING ACTIVITY:
  • Scans run: 8
  • Candidates reviewed: 28 unique stocks
  • Signals generated: 4
  • Entries executed: 2 (RIVN, COIN)
  • Positions held overnight: 2 (D+1 exit tomorrow)

TODAY'S P&L:
  • Realized: $0.00 (no exits today)
  • Unrealized: +$21.00 (open positions)
  • Total: +$21.00 (+2.1% of deployed capital) ✅

REJECTION BREAKDOWN:
  • Total rejected: 26 stocks
  • RSI too high (>35): 18 (69%)
  • Momentum falling knife: 4 (15%)
  • Earnings blackout: 2 (8%)
  • Strategy discipline: ✅ Avoided 26 marginal setups

WEEK-TO-DATE (Mon-Fri):
  • Trades: 7 (5W, 2L)
  • Win rate: 71%
  • Total P&L: +$142.50 (+14.3% weekly) 📈
  • Portfolio: $1,142.50

💡 Type 'show details' to see entries, exits, and open positions

NEXT SESSION: Monday, Jan 6, 2026
  • Weekend gap scanner will run 9:30-9:45 AM
```

---

## 🎯 What This Solves

### Before Reports
- ❌ "Why no trades today?"
- ❌ "Is the bot working?"
- ❌ "Am I making progress?"
- ❌ Anxiety → over-tweaking

### After Reports  
- ✅ "Market not oversold (RSI>35), bot correctly patient"
- ✅ "Bot scanned 28 stocks, rejected 26 for good reasons"
- ✅ "Up +14.3% this week, 71% win rate"
- ✅ Confidence → let it run

---

## 📁 Data Storage

Reports are saved automatically:
- **Daily stats**: `bot_v2/data/daily_stats.json` (last 90 days)
- **Position history**: Managed by position tracker
- **Logs**: `logs/sprint1_alpaca.log`

---

## 🔄 Integration with Bot

Reports are **fully integrated**:
1. Bot tracks session data automatically
2. Reports generate from live data
3. No manual input needed
4. Just run bot normally

**Session data tracked**:
- Scans run
- Candidates reviewed
- Signals generated
- Entries executed
- Rejection reasons

---

## 💡 Best Practices

### Daily Routine
1. **9:00 AM**: Check morning brief
   - Know if today is good for trading
   - See which stocks gapped down
2. **During day**: Let bot run (don't micro-manage)
3. **4:30 PM**: Check daily summary
   - See what happened and why
   - Track weekly progress

### When to Check Details
- **After first trade**: See why that stock was chosen
- **After 0-signal day**: Understand rejection reasons
- **End of week**: Review all trades for patterns

### Red Flags
- ⚠️ Win rate dropping below 55% → Check if filters need adjustment
- ⚠️ No trades for 3+ days → Market might be grinding (normal)
- ⚠️ Rejecting >90% of candidates → Filters might be too tight

---

## 🚀 Next Steps

1. **Let bot run for 2 weeks** with reports
2. **Review daily summaries** to build confidence
3. **After 2 weeks**: Decide if Monday gap scanner needed
4. **Stay disciplined**: Trust the reports, don't over-optimize

The reports will give you the visibility you need without the temptation to constantly tweak.
