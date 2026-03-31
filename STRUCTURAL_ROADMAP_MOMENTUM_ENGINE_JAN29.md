# Structural Roadmap: Momentum Engine (Weekly ROI‑Optimized, Solid Build)
**Date:** January 29, 2026  
**Goal:** Build a stable, modular momentum system optimized for **efficient short-swing weekly returns** with minimal patching and low rework.

**Primary KPI:** Weekly ROI % (P&L / Average Capital Deployed)  
**Secondary KPIs:** Trade frequency, capital utilization, win rate  
**Philosophy:** Productivity over perfection — every phase must improve weekly ROI or be rolled back.

---

## 1) Design Principles (Non‑Negotiable)
- **Weekly ROI first:** Every change must show measurable weekly ROI improvement vs baseline.
- **Trade frequency floor:** System must generate minimum 8-12 trades/week to maintain productivity.
- **Capital efficiency:** Target 70-90% capital utilization (not letting cash sit idle).
- **Single source of truth** for each feature (no duplicate logic in multiple layers).
- **Data‑flow clarity:** Feature computation → Screening → Signal scoring → Execution.
- **Fail fast, degrade gracefully:** If data is missing, log and skip without breaking pipeline.
- **Only compute expensive features after the candidate list is small.**
- **No hidden coupling:** Each module accepts input data and returns explicit outputs.
- **Fast rollback:** If weekly ROI drops >15%, auto-revert to previous phase.

---

## 2) Target Architecture (Stable & Modular)

### A. Data Layer (Existing / Minimal Change)
- **Input:** OHLCV + market proxy (SPY/QQQ) + sentiment + earnings/events
- **Output:** Cleaned per‑symbol dataframes + market regime snapshot

### B. Feature Layer (Ground‑Up, Deterministic)
Compute features once, store in a normalized structure, then consume everywhere.

**Feature Groups:**
1. **Volume & Momentum Core**
   - rvol_5m, rvol_15m
   - vol_roc, vol_zscore
   - volume_accel
   - climax_flag
   - price_breakout, momentum
2. **Trend & Regime**
   - adx_14
   - ma_slope_20 (and slope angle)
   - atr_pct_change
   - trend_state
   - vol_regime
3. **Structure & Alignment**
   - htf_trend_bias (15m/1h/4h)
   - ltf_break_flag (1m/5m)
   - range_compress_score
   - expansion_flag
4. **Setup Quality**
   - breakout_quality_score
   - flag_pullback_flag
   - gap_continuation_score
   - fakeout_probability

**Rule:** No direct signal decisions happen here—only feature computation.

### C. Screening Layer (Fast Filters)
Use **cheap features first** to reduce universe before heavier computations.

**Order:**
1) Liquidity + Price + Basic Volatility (ATR%)
2) Volume spike + breakout + momentum
3) Regime gating (market proxy)

Output: **Candidate set (10–20 symbols)**

### D. Scoring Layer (Quality + Confluence)
Run only on small candidate set.

- Multi‑timeframe alignment score
- Volume quality score
- Momentum consistency score
- Statistical quality score
- Setup classifier score
- Confluence + expected R

Output: **Trade quality score 0–100** + tier.

### E. Execution Layer (Existing)
- VWAP/TWAP/Order routing
- Risk controls, position sizing, cooldowns

---

## 3) Build Order (Solid Ground‑Up)

### Phase 0 — Foundation (Stability + Baseline Measurement)
**Deliverables:**
- Feature schema defined (names, types, ranges)
- Unified feature registry (single computation path)
- Unit tests for each feature calculation
- **Baseline weekly ROI measurement** (current system)

**Exit Criteria:**
- Feature registry produces deterministic outputs
- 100% unit tests passing
- **Baseline metrics captured:**
  - Weekly ROI: X%

### Phase 1b — RS & Sector Rotation (CRITICAL BUG FIX, Jan 30)
**Status**: ✅ **IMPLEMENTED & TESTED (21/21 tests passing)**
**Priority**: CRITICAL - Fixes root cause of Jan 26-30 underperformance

**Problem Addressed:**
- Bot was entering trades with false momentum (market-driven, not alpha-driven)
- Missing validation that stock was actually outperforming vs SPY/sector
- This week: 5 losses (-15.83 bps) that could have been filtered
- Example: MRNA -2.9%, CLF -5.97%, TAL -2.68% all had no relative strength

**Deliverables:**
- ✅ `rs_sector_enhancement.py` (296 lines, core module)
  - RelativeStrengthAnalyzer: Stock vs SPY comparison
  - SectorRotationAnalyzer: Sector momentum and alignment
  - Full feature set: RS score, decoupling score, sector momentum
- ✅ `test_phase1b_rs_sector_rotation.py` (524 lines, 21 tests)
  - All 21 tests passing (100%)
  - Real scenario validation (Jan 26-30 actual trades)
  - Impact quantification: 20.42 bps swing (5-8% weekly ROI improvement)
- ✅ `PHASE1B_RS_SECTOR_ROTATION_DESIGN.md` (615 lines)
  - Complete design specification
  - Integration points identified
  - Rollback plan documented
- ✅ `INVESTIGATION_REPORT_JAN30.md` (486 lines)
  - Evidence-based root cause analysis
  - 95% accuracy confirmation of chatbot diagnosis
  - Specific trade-by-trade analysis

**Features Implemented:**
1. **Relative Strength (RS) Calculation**
   - Stock 5-day return vs SPY 5-day return
   - RS score: 0-1 (higher = better)
   - Detects "green in red market" = highest conviction signals

2. **Decoupling Score**
   - Measures alpha (independent movement) vs beta (market-driven)
   - 0-1 scale: 0.8+ = high alpha, <0.3 = low alpha
   - Identifies real moves vs false breakouts

3. **Sector Identification & Momentum**
   - Maps stocks to sector ETFs (XLE, XLV, XLK, etc.)
   - Classifies sector as STRONG/NEUTRAL/WEAK
   - Validates stock isn't just following sector

4. **Hard Gates (Rejection Criteria)**
   - Market down >2% + stock not green in red → REJECT
   - Sector weak + stock not decoupled → REJECT
   - RS negative + low alpha → REJECT

5. **Confidence Multipliers**
   - Green in red: +30% boost
   - Beating sector: +15% boost
   - High alpha (>0.7): +25% boost

**Weekly ROI Target**: +5-8% improvement
**Expected Win Rate**: 40% → 50-60%
**Expected Trade Reduction**: 8-10/day → 5-8/day (quality over quantity)
**Implementation Effort**: 1 hour (signal_generator.py + pre_filter.py integration)
**Testing Effort**: 1 hour (run test suite + integration tests)
**Validation Period**: 1 week paper trading

**Exit Criteria:**
- ✅ All 21 unit tests passing
- Integration tests pass (no regressions to Phase 1)
- Paper trading: Win rate ≥ 48%+
- Paper trading: Weekly ROI ≥ +5%
- Log analysis shows RS gates working
- Ready for production deployment
  - Trades/week: Y
  - Capital utilization: Z%
  - Win rate: W%
  - Avg winner: $A, Avg loser: $B

---

### Phase 1 — Volume & Momentum Core (Highest ROI)
**Build:**
- rvol_5m / rvol_15m
- vol_roc / vol_zscore / volume_accel
- climax_flag
- price_breakout / momentum

**Integration:** PreFilter candidate generation

**Exit Criteria:**
- All features available for 95%+ symbols
- PreFilter yields stable candidate count (10–20 typical)
- **Weekly ROI improvement: +5% minimum vs baseline**
- **Trade frequency: ≥8 trades/week maintained**
- **Capital utilization: ≥60%**
- If ROI drops or trade count falls below 8/week → rollback + tune thresholds

---

### Phase 2 — Trend & Regime Filter (Win‑Rate Booster)
**Build:**
- adx_14, atr_pct_change, ma_slope_20
- trend_state, vol_regime (market proxy)

**Integration:** Regime‑adjusted thresholds in screening

**Exit Criteria:**
- Regime gating doesn’t reduce candidates below 5 unless market is extreme
- Backtest shows reduced drawdowns vs baseline- **Weekly ROI improvement: +3% minimum vs Phase 1**
- **Trade frequency: ≥8 trades/week maintained** (regime filter can't be too restrictive)
- **Win rate improvement: +2-5%** (quality over quantity, but not at expense of ROI)
- **Rollback trigger:** If weekly ROI drops OR trade count falls below 6/week
---

### Phase 3 — Multi‑Timeframe Structure (Precision Layer)
**Build:**
- htf_trend_bias (15m/1h/4h)
- ltf_break_flag (1m/5m)
- range_compress_score, expansion_flag

**Integration:** Quality scoring layer only

**Exit Criteria:**
- Quality scores differentiate trades (strong/medium/weak)
- **Trade count acceptable reduction: ≤20% vs Phase 2** (not 30% — too aggressive)
- **Weekly ROI improvement: +5% minimum vs Phase 2** (must offset lower trade count)
- **Capital utilization: ≥65%** (fewer trades but larger/better positions)
- **Strong tier outperforms by 2x:** Strong-tier trades should have 2x win rate vs weak tier
- **Rollback trigger:** If weekly ROI drops OR trade count falls below 6/week OR capital utilization <50%

---

### Phase 4 — Setup Classifiers (A+ Filter)
**Build:**
- breakout_quality_score
- flag_pullback_flag
- gap_continuation_score
- fakeout_probability

**Integration:** Confluence / quality score (not hard blocking)

**Exit Criteria:**
- False breakout rate drops measurably
- Net expectancy improves on backtest
- **Weekly ROI improvement: +3% minimum vs Phase 3**
- **Trade frequency: ≥7 trades/week maintained**
- **Avg winner increases by ≥10%** (better setup quality should increase profit per trade)
- **Max drawdown reduction: ≥15%** (fewer fakeouts = smoother equity curve)
- **Rollback trigger:** If weekly ROI flat or negative vs Phase 3

---

### Phase 5 — Trade Quality Scoring (Final Gate)
**Build:**
- confluence_score
- trade_quality_score
- expected_r
- probability_edge

**Integration:** Final decision gate before execution

**Exit Criteria:**
- Decision score aligns with P&L on backtest
- Strong tier outperforms medium/weak tiers
- **Weekly ROI improvement: +5% minimum vs Phase 4**
- **Trade frequency: ≥6 trades/week** (acceptable to be more selective at this stage)
- **Capital utilization: ≥70%** (deploy capital efficiently even with fewer trades)
- **Profit factor: ≥1.5** (gross profit / gross loss ratio)
- **Expected R per trade: ≥1.5:1** (average winner / average loser)
- **Rollback trigger:** If weekly ROI doesn't improve OR profit factor drops below 1.3

---

### Phase 6 — Lightweight ML (Optional, Only If ROI Justifies)
**Build:**
- XGBoost / LightGBM classifier for p_continuation and p_fakeout
- Walk‑forward validation

**Exit Criteria:**
- Model improves out‑of‑sample performance by ≥10% vs rule‑based
- **Weekly ROI improvement: +7% minimum vs Phase 5** (ML must justify complexity)
- **Trade frequency: ≥6 trades/week maintained**
- **No performance degradation:** Must maintain consistency across different market regimes
- **Rollback trigger:** If weekly ROI doesn't improve by ≥5% OR model shows overfitting signs

**Note:** This phase is truly optional. If Phases 1-5 achieve target weekly ROI (20-30%+), ML may not be necessary.

---

## 4) Testing Strategy (ROI‑Focused, No Patch‑Heavy Rework)

### Unit Tests (per feature)
- Deterministic outputs on fixed fixtures
- Edge cases: missing volume, zero volume, low liquidity

### Integration Tests
- End‑to‑end: data → features → screening → scoring → signal
- Verify the feature registry outputs are consistent across runs

### Backtesting Gates
- Phase advancement only after positive impact vs baseline
- **Minimum 4 weeks of backtest data** (capture weekly variance)
- **Weekly ROI must improve in ≥75% of weeks** (not just avg improvement)

### Paper Trading Gates (Critical for Weekly ROI Validation)
- **Every phase must paper trade for 1 full week before live deployment**
- **Weekly ROI target: Match or exceed backtest projections**
- **Trade frequency verification: Actual trades ≥ 80% of backtest expectations**
- **Capital utilization check: Deployed capital ≥ target threshold**
- If paper trading fails any metric → tune and retest for another week

### Live Trading Rollback Rules
- **Monitor weekly ROI in live trading continuously**
- **Automatic rollback if:**
  - Weekly ROI drops >15% vs previous phase for 2 consecutive weeks
  - Trade frequency drops >30% vs paper trading average
  - Capital utilization drops below 50% for 1 week
  - Max drawdown exceeds 20% in any week
- **Manual review if:**
  - Weekly ROI flat (±3%) for 3 consecutive weeks
  - Win rate drops >10% vs paper trading

---

## 5) Performance Budget (Protect Speed)

- **Feature Layer:** batch compute once per symbol
- **Screening:** O(n) on full universe
- **Scoring:** O(k) where k << n (candidate set only)

Guideline: **never run multi‑timeframe scoring on the full universe.**

---

## 6) “No‑Patching” Rules
- No logic duplicated across modules.
- No production deployment without passing integration tests.
- Every new feature must have a test + benchmark impact report.
- Strictly limit experimental logic to a flagged branch until validated.

---

## 7) Implementation Checklist (Per Phase — ROI‑Gated)
- ✅ Feature spec defined
- ✅ Unit tests added (100% passing)
- ✅ Integration tests updated (100% passing)
- ✅ Performance benchmark recorded
- ✅ **Backtest completed (4+ weeks):**
  - Weekly ROI improvement: ___% vs previous phase
  - Trade frequency: ___ trades/week (≥minimum threshold)
  - Capital utilization: ___%
  - Win rate: ___%
  - Avg winner / Avg loser: $ ___ / $ ___
  - Profit factor: ___
- ✅ **Paper trading completed (1 week minimum):**
  - Weekly ROI achieved: ___%
  - Trades executed: ___
  - Capital deployed: ___%
  - Any deviations from backtest documented
- ✅ **Phase gate approval:**
  - All ROI metrics meet or exceed targets ✓
  - No regression in secondary metrics ✓
  - Risk controls validated ✓
  - Rollback plan documented ✓
- ✅ Deployment checklist followed
- ✅ **Live monitoring active:**
  - Daily ROI tracking
  - Weekly ROI comparison vs target
  - Rollback trigger monitoring

---

## 8) Why This Build Order Optimizes Weekly ROI
- **Early layers** are cheap, deterministic, and reduce data volume → faster execution, more trades.
- **Later layers** are expensive but only run on a small set → precision without killing productivity.
- **Each phase** has explicit ROI gates → only keep changes that improve weekly returns.
- **Trade frequency floors** prevent over-filtering → maintain productivity.
- **Capital utilization targets** ensure cash isn't sitting idle → maximize weekly returns.
- **Fast rollback rules** protect against ROI regression → preserve gains from previous phases.

---

## 9) Weekly ROI Targets (Cumulative)

| Phase | Target Weekly ROI | Min Trades/Week | Min Capital Util | Expected Timeline |
|-------|------------------|-----------------|------------------|-------------------|
| Baseline (Phase 0) | Measure current | Current | Current | Week 0 |
| Phase 1 | Baseline + 5% | 8 | 60% | Week 1-2 |
| Phase 2 | Phase 1 + 3% | 8 | 65% | Week 3-4 |
| Phase 3 | Phase 2 + 5% | 7 | 65% | Week 5-7 |
| Phase 4 | Phase 3 + 3% | 7 | 70% | Week 8-10 |
| Phase 5 | Phase 4 + 5% | 6 | 70% | Week 11-13 |
| Phase 6 (optional) | Phase 5 + 7% | 6 | 70% | Week 14-17 |

**Cumulative Target:** If baseline is 3% weekly ROI, end state should be 10-15% weekly ROI (Phase 5) or 15-20% weekly ROI (Phase 6).

**Critical Rule:** If any phase fails to meet ROI target after 2 weeks of tuning → skip it and move forward. Don't let perfect be the enemy of profitable.

---

## 10) Next Action (Zero‑Risk)
- **Week 0:** Capture baseline metrics (current system, 1 week of live/paper trading)
  - Weekly ROI: ___%
  - Trades/week: ___
  - Capital utilization: ___%
  - Win rate: ___%
- **Week 1:** Confirm Phase 0 feature schema and registry naming
- **Week 2:** Begin Phase 1 implementation with ROI tracking

---

**Status:** Ready to execute as a **weekly ROI-optimized** structural roadmap.  
**Philosophy:** Productivity over perfection. Every phase must earn its place by improving weekly returns.
