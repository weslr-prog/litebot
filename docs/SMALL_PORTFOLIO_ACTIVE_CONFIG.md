# Small Portfolio Configuration - ACTIVE

**Last Updated:** November 6, 2025  
**Status:** ✅ OPTIMIZED FOR $1K PORTFOLIO

---

## 🎯 Current Configuration Summary

### Stock Selection Filters (Mid-Cap Volatile Focus)
- **Price Range:** $10-30 (optimized for small positions)
- **Volatility:** 3-15% ATR (need bigger daily swings, avoid chaos)
- **Momentum:** 3-40% (mid-caps can run harder)
- **Volume:** 100K shares/day minimum ($500K dollar volume)
- **Breakout:** 0.7x volume spike, 0.2% price breakout (relaxed for opportunities)

### Exit Zones (Wider for Mid-Cap Swings)
- **Zone 1 (9:30-10:00):** TP: +3% | SL: -2%
- **Zone 2 (10:00-2:00):** TP: +4% | SL: -3%
- **Zone 3 (2:00-3:45):** TP: +2.5% | SL: -2%
- **Intraday Targets:** +4% take profit, -2.5% stop loss
- **Trailing Stops:** Activate at +3%, trail 2% behind

### Stock Universe (Mid-Cap Volatile)
**Growth Tech:** PLTR, SOFI, HOOD, FSLY, NET, DDOG, CRWD, ZS, RBLX, U, PATH  
**Crypto-Related:** MARA, RIOT, COIN  
**EV/Clean Energy:** RIVN, NIO, LCID, XPEV, PLUG, FCEL, BE, QS, CHPT, BLNK  
**Cannabis:** TLRY, CGC, MSOS, SNDL, ACB, CRON, OGI, GRWG  
**Meme/Retail:** AMC, GME, SPCE  
**Other Volatile:** SNAP, DKNG, PENN, AFRM, UPST, BYND, SFIX, ETSY, W  

### Current Watchlist (Nov 6, 2025)
Top 15 candidates with momentum:
1. FSLY ($11) - Score: 126.68 | +32.1% momentum ⭐
2. VCYT ($42) - Score: 56.88 | +14.5% momentum
3. RIVN ($15) - Score: 46.60 | +16.5% momentum ⭐
4. BE ($141) - Score: 44.46 | +39.4% momentum
5. XPEV ($24) - Score: 28.97 | +11.1% momentum ⭐
6. U ($40) - Score: 23.30 | +7.9% momentum
7. ILMN ($121) - Score: 18.63 | +20.8% momentum
8. W ($99) - Score: 9.55 | +18.7% momentum
9. PLTR ($188) - Score: 8.41 | +4.1% momentum
10. EXAS ($67) - Score: 7.48 | +4.3% momentum

⭐ = Perfect price range for small portfolio ($10-30)

---

## 📋 Changes Made Today (Nov 6, 2025)

### Configuration Updates (`small_portfolio_config.py`)
✅ **Price filter:** $10-30 (was $10-35)  
✅ **Volatility filter:** 3-15% ATR (was 3-60%)  
✅ **Volume requirements:** 100K shares, $500K dollar volume (was 500K shares, $5M)  
✅ **Breakout thresholds:** 0.7x volume, 0.2% price (was 0.8x, 0.3%)  
✅ **Momentum range:** 3-40% (was 5-50%)  

### Exit Strategy Updates
✅ **Intraday TP/SL:** +4% / -2.5% (was +2.5% / -1.5%)  
✅ **Zone 1:** +3% / -2% (was +2.5% / -1.5%)  
✅ **Zone 2:** +4% / -3% (was +3.5% / -2%)  
✅ **Zone 3:** +2.5% / -2% (was +2% / -1.5%)  
✅ **Trailing stops:** +3% trigger, 2% trail (was +1.5%, 1%)  

### Universe Updates (`config/short_cycle_universe.json`)
✅ **Replaced:** S&P 500 blue chips with 70 mid-cap volatile stocks  
✅ **Focus:** Growth tech, crypto, cannabis, EV, meme stocks  
✅ **Target:** Stocks that move 3-10% daily for profit opportunities  

### Documentation Cleanup
✅ **Archived:** Old ROADMAP.md and completed sprint docs to `docs/archive_old/`  
✅ **Active Plan:** `SMALL_PORTFOLIO_OPTIMIZATION_PLAN.md` is the current roadmap  

---

## 🚀 Next Steps

### Immediate (Today)
1. ✅ Config optimized for mid-cap volatility
2. ✅ Universe updated with 70 volatile stocks
3. ✅ Watchlist refreshed (15 candidates with momentum)
4. ⏳ **Restart bot** with new configuration
5. ⏳ **Monitor paper trading** with optimized settings

### Short-term (This Week)
1. ⏳ **Wait for Alpaca cash account approval** (1-2 days)
2. ⏳ **Validate 5-10 trades** in paper mode with new universe
3. ⏳ **Restore production thresholds** (5% confidence after testing)
4. ⏳ **Switch to live trading** once cash account active

### Phase 2 (Next 1-2 Weeks)
1. 📋 Fund with $500 initially (not full $1K)
2. 📋 Trade 2-3 positions max
3. 📋 Run 2 weeks to validate mechanics
4. 📋 Target +2-4% weekly return

### Phase 3 (After Validation)
1. 📋 Scale to full $1K
2. 📋 Trade 4-5 positions daily
3. 📋 Monitor weekly performance vs targets

---

## ⚠️ Test Mode Settings (Restore After First Profitable Week)

**Current (TEMP):**
- `confidence_threshold = 0.025` (2.5% - very relaxed)
- `late_entry_confidence_multiplier = 1.05` (1.05x - easy late entries)

**Production (RESTORE AFTER TESTING):**
- `confidence_threshold = 0.05` (5% - stricter quality)
- `late_entry_confidence_multiplier = 1.3` (1.3x - higher bar for late entries)

---

## 📊 Expected Performance

**With Mid-Cap Volatile Stocks:**
- Win Rate: 50% (same as before)
- Avg Win: +4% ($8 on $200 position)
- Avg Loss: -3% ($6 on $200 position)
- Profit Factor: 1.33 (profitable!)

**Weekly Target:**
- 5 trades/day × 4 days = 20 trades/week
- 10 wins @ +$8 = +$80
- 10 losses @ -$6 = -$60
- **Net: +$20/week (+2% weekly return)**

**Realistic Range:** +$20-40/week (+2-4% weekly)

---

## 🎯 Key Success Factors

1. **Stock Selection:** Mid-cap volatility is CRITICAL (3-8% daily ATR)
2. **Price Range:** $10-30 sweet spot for $100-200 positions
3. **Risk Management:** 2% risk per trade ($20) is sacred
4. **Exit Discipline:** Take profits at +3-4%, cut losses at -2-3%
5. **Position Sizing:** Never exceed $200 per position

---

**Status:** Ready to trade with optimized small portfolio configuration!
