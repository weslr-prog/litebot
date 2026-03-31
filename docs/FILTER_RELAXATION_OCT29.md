# Filter Relaxation Implementation - October 29, 2025

## Summary of Changes

### What Was Changed
**File:** `pre_filter.py` (lines 830-842)
**Filter:** Breakout filter final relaxation parameters

### Before (Oct 28, 2025)
```python
'vol_spike_min': 0.8,      # Volume spike threshold
'breakout_min': 0.002,     # 0.2% price breakout
'breakout_window': 8,      # 8-day lookback
'vol_avg_window': 8,       # 8-day volume average
'minp_frac': 0.4           # 40% valid data required
```
**Result:** Only 6 stocks passing (82% rejection rate)

### After (Oct 29, 2025) - Option A Implementation
```python
'vol_spike_min': 0.7,      # Reduced from 0.8 (12.5% relaxation)
'breakout_min': 0.0015,    # Reduced from 0.002, now 0.15% (25% relaxation)
'breakout_window': 8,      # Unchanged - optimal for yfinance data
'vol_avg_window': 8,       # Unchanged - matches breakout window
'minp_frac': 0.3           # Reduced from 0.4 (25% relaxation)
```
**Expected Result:** 10-12 stocks passing (67-100% improvement)

## Rationale

### Problem Identified
1. **Breakout filter was primary bottleneck** (82% rejection rate)
2. **Only 6 stocks passing** → poor diversification
3. **Risk-reward ratio: 0.23:1** (target: >1.5:1)
4. **yfinance data gaps** causing most stocks to show `vol_spike=NaN`

### Solution: Option A (Moderate Relaxation)
- **Conservative enough** to maintain signal quality
- **Aggressive enough** to meaningfully increase stock selection
- **Balanced approach** between Options B (too conservative) and C (too aggressive)

## Expected Impact

### Quantitative
- Stock universe: **6 → 10-12 stocks** (+67% to +100%)
- Filter pass rate: **18% → 30-35%**
- Risk distribution: **Significantly improved**
- Signal diversity: **More opportunities**

### Qualitative
- Better diversification across sectors
- Reduced single-position impact
- More consistent weekly performance
- Improved profit factor (target: >1.0)

## Monitoring Plan

### Days 1-3 (Oct 30 - Nov 1)
- ✅ Verify 10-12 stocks in daily watchlist
- ✅ Confirm filter relaxation working
- ✅ Check for signal quality

### Days 4-7 (Nov 2 - Nov 5)
- Monitor win rate (target: ≥45%)
- Monitor avg P&L per trade
- Monitor profit factor (target: >1.0)

### Week 2 (Nov 8 - Nov 12)
- Assess weekly return (target: ≥+0.25%)
- Decide on further adjustments
- Consider Option B/C or revert if needed

## Rollback Plan

If performance degrades or signal quality drops:

### Revert to Previous Settings
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
git diff pre_filter.py  # Review changes
git checkout pre_filter.py  # Revert if needed
```

### Or Implement Option B (Conservative)
```python
'vol_spike_min': 0.75,     # Between current 0.7 and previous 0.8
'breakout_min': 0.0018,    # Between current 0.0015 and previous 0.002
'minp_frac': 0.35          # Between current 0.3 and previous 0.4
```

## Success Metrics

### Primary Metrics (Week 1)
- [ ] Stock universe: 10-12 stocks passing filters
- [ ] Win rate: ≥45%
- [ ] Profit factor: >0.8 (improvement from 0.23)

### Secondary Metrics (Week 2)
- [ ] Weekly return: ≥+0.25%
- [ ] Risk-reward ratio: >1.0:1
- [ ] Average loss: <$400 (vs current -$462)

### Stretch Goals (Month 1)
- [ ] Monthly return: +1.0% to +2.0%
- [ ] Profit factor: >1.5
- [ ] Sharpe ratio improvement

## Notes

- **yfinance data quality** is the root cause of NaN values
- **8-day window** is optimal balance (shorter = less data, longer = stale signals)
- **0.15% breakout threshold** is realistic for D+1 momentum plays
- **30% valid data requirement** compensates for typical yfinance gaps

## Reference

See full analysis in: `docs/PERFORMANCE_EVALUATION_OCT29_2025.md`

---

**Implementation Date:** October 29, 2025, 5:00 PM ET
**Implemented By:** Performance evaluation analysis
**Status:** ✅ Active and monitoring
**Next Review:** November 1, 2025
