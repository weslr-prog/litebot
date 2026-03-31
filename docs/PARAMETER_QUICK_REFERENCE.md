# LiteBotX Parameter Quick Reference

## Current Bot Configuration (October 30, 2025)

## 🎯 Small Portfolio Config (NEW) vs Large Portfolio

### Portfolio & Position Sizing Comparison
| Parameter | Small Portfolio | Large Portfolio | Ratio |
|-----------|----------------|----------------|--------|
| Portfolio Value | $1,000 | $963,000 | 1:963 |
| Daily Pool % | 33% (Mon-Wed) | 60% | Lower daily |
| Thursday Pool % | 100% (All-in) | 60% | Higher risk |
| Daily Pool $ | $330 | $577,800 | 1:1,751 |
| Max Position $ | $300 | $6,000 | 1:20 |
| Min Position $ | $50 | $25 | 2x higher |
| Max Positions/Day | 3 | 8 | Quality focus |
| Position % of Portfolio | 30% | 0.6% | 50x higher |

### Risk Management Comparison  
| Parameter | Small Portfolio | Large Portfolio | Risk Level |
|-----------|----------------|----------------|------------|
| Risk/Trade $ | $25 | $100+ | 2.5% vs 0.01% |
| Max Loss/Trade $ | $50 | $400 | 5% vs 0.04% |
| Daily Loss Limit | 8% ($80) | 0.2% ($1,926) | 40x % higher |
| Weekly Loss Limit | 15% ($150) | 0.6% ($5,778) | 25x % higher |
| Risk Tolerance | Aggressive | Conservative | Higher % swings |

### Stock Selection Comparison
| Parameter | Small Portfolio | Large Portfolio | Focus |
|-----------|----------------|----------------|--------|
| Price Range | $10 - $35 | $15 - $300 | Mid-cap vs all |
| Min Volatility | 3% | 1.5% | Higher ATR |
| Max Volatility | 60% | 35% | Embrace swings |
| Min Momentum | 5% | 3% | Stronger moves |
| Max Momentum | 50% | 20% | Bigger breakouts |
| Min Volume | 500K | 30K | Better liquidity |

### Exit Strategy Comparison
| Time Zone | Small Take/Stop | Large Take/Stop | Aggression |
|-----------|----------------|----------------|------------|
| Zone 1 (9:30-10:30) | +4%/-2.5% | +1.5%/-1% | 2.7x more |
| Zone 2 (10:30-1:00) | +6%/-3% | +2%/-1.5% | 3x more |
| Zone 3 (1:00-3:30) | +3%/-2.5% | +1%/-1% | 3x more |
| Zone 4 (3:30-4:00) | Force exit | Force exit | Same |

---

## 📊 Large Portfolio Configuration (Main System)

### Portfolio & Position Sizing
| Parameter | Value | What It Controls |
|-----------|-------|------------------|
| Portfolio Value | $963,000 | Total account equity |
| Daily Pool % | 60% | % of portfolio available daily |
| Daily Pool $ | $577,800 | Dollar amount available daily |
| Max Position $ | $6,000 | Hard cap per position |
| Min Position $ | $25 | Minimum viable position |
| Max Positions/Day | 8 | New positions per day |
| Max Position % | 12% | Theoretical max (overridden by $6K cap) |

### Risk Management
| Parameter | Value | What It Controls |
|-----------|-------|------------------|
| Base Risk/Trade | $100 | Foundation for position sizing |
| Max Loss/Trade | $400 | Hard stop per trade |
| Daily Loss Limit | 0.2% ($1,926) | Max loss per day |
| Weekly Loss Limit | 0.6% ($5,778) | Max loss per week |
| Confidence Threshold | 7% (0.07) | Minimum signal quality |

### Dynamic Position Sizing (NEW)
| Confidence Tier | Range | Multiplier | Example Risk |
|----------------|-------|------------|--------------|
| HIGH | ≥0.75 | 1.6x - 2.0x | $160-$200 |
| MEDIUM | 0.55-0.75 | 1.2x - 1.6x | $120-$160 |
| LOW | <0.55 | 1.0x - 1.2x | $100-$120 |

### Trailing Stops (NEW)
| Parameter | Value | What It Does |
|-----------|-------|--------------|
| Enabled | True | Activates profit protection |
| Trigger | +1.5% | Profit to activate stop |
| Trail Distance | 1.0% | Distance below highest price |
| Min Profit Lock | +0.5% | Minimum profit guaranteed |
| Update Interval | 60 sec | Recalculation frequency |

### Time & Holding
| Parameter | Value | What It Controls |
|-----------|-------|------------------|
| Max Hold Days | 2 (D+1) | Maximum hold period |
| Trading Days | Mon-Thu | Days to enter positions |
| Exit Time | 3:45 PM ET | Default forced exit time |

### PreFilter - Data Quality
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min Data Rows | 15 days | Minimum price history |
| Min Volume | 30,000/day | Average daily volume |
| Min $ Volume | $300,000/day | Daily dollar volume |

### PreFilter - Price & Volatility
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min Price | $15 | Avoid penny stocks |
| Max Price | $350 | Keep positions meaningful |
| Min Volatility | 1.5% | Minimum ATR% for momentum |
| Max Volatility | 35% | Avoid excessive risk |

### PreFilter - Momentum
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Lookback | 4 days | Momentum measurement period |
| Min Momentum | +2% | Minimum 4-day return |
| Max Momentum | +30% | Avoid parabolic moves |

### PreFilter - Breakout (RELAXED Oct 29)
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Vol Spike Min | 0.7 (70%) | Volume vs average |
| Breakout Min | 0.0015 (0.15%) | Price breakout magnitude |
| Breakout Window | 8 days | Lookback period |
| Vol Avg Window | 8 days | Volume average period |
| Min Data Fraction | 0.3 (30%) | Valid data points required |

### Watchlist Targets
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Target Min | 8 stocks | Minimum watchlist size |
| Target Max | 15 stocks | Maximum watchlist size |
| Current Result | 15 stocks | After Oct 29 relaxation |

### D+1 Exit Zones
| Zone | Time | Take Profit | Stop Loss |
|------|------|-------------|-----------|
| Zone 1 (Morning) | 9:30-10:00 AM | ≥+1.5% | ≤-1.0% |
| Zone 2 (Mid-Day) | 10:00 AM-2:00 PM | ≥+2.0% | ≤-1.5% |
| Zone 3 (Afternoon) | 2:00-3:45 PM | ≥+1.0% | ≤-1.0% |
| Zone 4 (Power Hour) | 3:45-4:00 PM | Force exit ALL | Force exit ALL |

### VIX Regime Adjustments
| VIX Range | Condition | Position Size Multiplier |
|-----------|-----------|-------------------------|
| >30 | Extreme Fear | 0.5x (cut in half) |
| 25-30 | High Volatility | 0.75x (reduce 25%) |
| 20-25 | Elevated | 1.0x (normal) |
| <20 | Low Volatility | 1.0x (normal) |

### Diversification
| Parameter | Small Portfolio (<$100K) | Large Portfolio (>$100K) | Your Status |
|-----------|-------------------------|-------------------------|-------------|
| Max Positions/Symbol | 2 | 3 | Using Large rules |
| Max Concentration % | 35% | 40% | Using Large rules |

### Transaction Costs
| Parameter | Value | Notes |
|-----------|-------|-------|
| Commission | $0 | Alpaca is commission-free |
| Spread Cost | 5 basis points | Bid-ask spread estimate |
| Model Costs | True | Include in P&L |

---

## Recent Changes Log

### October 29, 2025
**Breakout Filter Relaxation:**
- vol_spike_min: 0.8 → 0.7 (12.5% easier)
- breakout_min: 0.002 → 0.0015 (25% easier)  
- minp_frac: 0.4 → 0.3 (25% easier)
- **Result:** Watchlist 6 → 15 stocks (+150%)

**Dynamic Position Sizing Added:**
- HIGH confidence: 1.6-2.0x position size
- MEDIUM confidence: 1.2-1.6x position size
- LOW confidence: 1.0-1.2x position size

**Trailing Stops Added:**
- Activation: +1.5% profit
- Trail distance: 1.0% below highest
- Minimum profit lock: +0.5%

---

## Configuration File Location
`/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py`

**Lines 74-130:** ShortCycleConfig dataclass

---

## Quick Health Check Commands

```bash
# Check current watchlist
cat logs/current_watchlist.json | jq '.symbols | length'

# Monitor dynamic sizing
grep "Dynamic Sizing" logs/trading_bot.log | tail -5

# Watch trailing stops
grep "Trailing stop" logs/trading_bot.log | tail -5

# Check daily P&L
grep "Daily P&L" logs/trading_bot.log | tail -1
```

---

**Version:** 1.0  
**Date:** October 30, 2025  
**Status:** ✅ Production - All parameters validated
