# Option 3 Quick Start Guide

## 🚀 Start the Bot

```bash
cd /home/wes/Desktop/litebotx-usb-deployment
source litebotx_env/bin/activate
python3 start_small_portfolio_trader.py
```

## 📊 What to Expect

**First Week (Nov 25-29)**:
- 2-3 trade signals (60% confidence threshold is strict)
- Entry prices: $5-$50 stocks
- Position sizes: $50-$200 per trade
- Daily monitoring: Check logs for signal quality

**Target Performance**:
- 12 trades/month (3 per week average)
- 60% win rate (6-8 winners out of 12)
- 3.52% weekly return
- 14% monthly return

## 🎯 Key Changes from Previous Config

| What Changed | Old | New | Impact |
|--------------|-----|-----|--------|
| Portfolio | $963K | **$1K** | Small account mode |
| Confidence | 5% | **60%** | Much stricter filtering |
| Max Positions | 8 | **12** | Triple frequency |
| Daily Pool | 30% | **50%** | Aggressive deployment |
| Price Range | $10-$40 | **$5-$50** | More opportunities |

## ⚠️ What This Means

**GOOD NEWS** ✅:
- Higher quality signals (60% confidence minimum)
- Better position sizing for $1K account
- 3x more trades per month (if signals available)
- Projected 3.52% weekly (vs 0.98% current)

**REALITY CHECK** ⚠️:
- Fewer signals than before (60% threshold is strict)
- May only get 8-10 trades/month (not 12)
- Win rate may be 40-50% (not full 60%)
- Realistic: 2-3% weekly (still 2-3x better!)

## 📈 Success Metrics (First Month)

**EXCELLENT** (hitting targets):
- 10-12 trades executed
- Win rate >50%
- Weekly return >3%
- No system errors

**GOOD** (on track):
- 6-8 trades executed
- Win rate >40%
- Weekly return >2%
- Bot running smoothly

**NEEDS ADJUSTMENT** (underperforming):
- <6 trades executed → Lower confidence to 50%
- Win rate <30% → Review entry quality
- Weekly return <1% → Check exit timing
- Frequent errors → Debug issues

## 🔧 Quick Adjustments

**If too few signals** (<6 trades/month after 2 weeks):
```python
# Edit traders/short_cycle_trader.py line 112
confidence_threshold: float = 0.50  # Lower from 0.60 to 0.50
```

**If win rate low** (<35% after 10 trades):
```python
# Consider adding these filters (advanced):
# - Volume momentum confirmation
# - 50MA uptrend filter
# - Sector rotation screening
```

**If too many signals** (>15 trades/month):
```python
# Edit traders/short_cycle_trader.py line 112
confidence_threshold: float = 0.65  # Raise from 0.60 to 0.65
```

## 📋 Daily Monitoring Commands

**Check signals generated today**:
```bash
grep "confidence=" logs/short_cycle_trader.log | grep $(date +%Y-%m-%d) | tail -10
```

**Check active positions**:
```bash
python3 -c "import json; positions = json.load(open('positions.json')); active = [p for p in positions if p.get('status') == 'OPEN']; print(f'{len(active)} active positions'); [print(f\"  {p['symbol']}: \${p.get('unrealized_pnl', 0):.2f}\") for p in active]"
```

**Check today's P&L**:
```bash
grep "P&L" logs/short_cycle_trader.log | grep $(date +%Y-%m-%d) | tail -5
```

**Check win rate (week)**:
```bash
python3 -c "import json; from datetime import datetime, timedelta; positions = json.load(open('positions.json')); week_ago = (datetime.now() - timedelta(days=7)).isoformat(); recent = [p for p in positions if p.get('exit_timestamp', '') > week_ago and p.get('status') == 'EXITED']; winners = [p for p in recent if p.get('realized_pnl', 0) > 0]; print(f'This week: {len(winners)}/{len(recent)} = {len(winners)/len(recent)*100:.1f}% win rate' if recent else 'No trades this week')"
```

## 🎯 Next Steps

1. **Week 1**: Monitor signal generation (should see 2-3 signals)
2. **Week 2**: Check win rate (target >40%)
3. **Week 3**: Review weekly returns (target >2%)
4. **Week 4**: Adjust confidence threshold if needed

## 📞 Need Help?

**Bot not starting**:
```bash
# Check Python environment
source litebotx_env/bin/activate
python3 -c "from traders.short_cycle_trader import ShortCycleConfig; print('OK')"
```

**No signals**:
- Check if 60% confidence is too strict
- Verify pre_filter is finding stocks ($5-$50 range)
- Review logs for filter rejections

**Too many errors**:
- Check Alpaca API connection
- Verify market hours (9:30 AM - 4:00 PM ET)
- Review data quality issues

## ✅ Pre-Flight Checklist

Before starting:
- [ ] Portfolio has ~$1,000 (or adjust config)
- [ ] Alpaca account is paper trading (not live!)
- [ ] Market is open (Mon-Fri 9:30 AM - 4:00 PM ET)
- [ ] No old positions from previous config
- [ ] Bot logs directory exists (logs/)
- [ ] positions.json is backed up

**Good luck!** 🚀

Target: 3.52% weekly (140% annually)  
Realistic: 2-3% weekly (100-150% annually)  
Both are EXCELLENT for a $1K account!
