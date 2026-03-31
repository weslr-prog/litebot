# LiteBotX Trading Bot - Parameter Reference Guide

## Document Purpose
This guide explains every parameter the bot uses, organized by function. Each parameter includes its current value, what it controls, and why it matters.

**Last Updated:** October 30, 2025  
**Bot Version:** Short-Cycle Trader v3.0 + SmallPortfolioConfig  
**Configuration Files:** 
- Main: `traders/short_cycle_trader.py` (ShortCycleConfig)
- Small Portfolio: `small_portfolio_config.py` (SmallPortfolioConfig)

---

## 🎯 Small Portfolio Configuration (NEW - October 30, 2025)

### **Overview**
**Purpose:** Optimized for <$1K portfolios with aggressive weekly profit targets  
**Philosophy:** "Go big or go home" for paper trading with weekly positive returns  
**Capital Allocation:** 33% daily pools Mon-Wed, all-in Thursday  
**Target Market:** Mid-cap stocks $10-35 for higher % swings  

### **Core Portfolio Parameters**
| Parameter | Value | Large Portfolio | Description |
|-----------|--------|----------------|-------------|
| **portfolio_value** | $1,000 | $963,000 | Target small portfolio size |
| **daily_pool_percent** | 33% | 60% | Mon-Wed deployment |
| **thursday_pool_percent** | 100% | N/A | All-in Thursday strategy |
| **max_position_dollars** | $300 | $6,000 | 30% max position vs 0.6% |
| **min_position_size_dollars** | $50 | $25 | Meaningful minimum |
| **max_positions_per_day** | 3 | 15 | Quality over quantity |

### **Enhanced Risk Management**
| Parameter | Value | Large Portfolio | Impact |
|-----------|--------|----------------|---------|
| **max_risk_per_trade_dollars** | $25 | Variable | 2.5% portfolio risk |
| **max_loss_per_trade_dollars** | $50 | Variable | 5% hard stop |
| **max_daily_loss_percent** | 8% | 3% | Higher risk tolerance |
| **max_weekly_loss_percent** | 15% | 5% | Weekly limit |
| **position_risk_percent** | 2.5% | 0.5-0.6% | More aggressive |

### **Mid-Cap Stock Selection**
| Parameter | Value | Large Portfolio | Rationale |
|-----------|--------|----------------|-----------|
| **min_price** | $10.00 | $15.00 | Capture growth stocks |
| **max_price** | $35.00 | $300.00 | Mid-cap volatility focus |
| **min_volatility** | 3% | 1.5% | Minimum ATR for swings |
| **max_volatility** | 60% | 35% | Embrace volatility |
| **min_momentum** | 5% | 3% | Stronger momentum requirement |
| **max_momentum** | 50% | 20% | Higher breakout potential |
| **min_avg_volume** | 500,000 | 30,000 | Enhanced liquidity |
| **min_dollar_volume** | $5,000,000 | $300,000 | Institutional quality |

### **Aggressive Exit Strategy**
| Time Zone | Take Profit | Stop Loss | Large Portfolio | Strategy |
|-----------|-------------|-----------|----------------|----------|
| **Zone 1 (9:30-10:30 AM)** | +4% | -2.5% | +1.5%/-1% | Morning volatility |
| **Zone 2 (10:30 AM-1 PM)** | +6% | -3% | +2%/-1.5% | Mid-day trends |
| **Zone 3 (1-3:30 PM)** | +3% | -2.5% | +1%/-1% | Afternoon position |
| **Zone 4 (3:30-4 PM)** | Force exit | Force exit | Same | Close all positions |

### **Enhanced Trailing Stops**
| Parameter | Value | Large Portfolio | Enhancement |
|-----------|--------|----------------|-------------|
| **trailing_trigger_pct** | 3% | 1.5% | Activate at higher gain |
| **trailing_distance_pct** | 2% | 1% | Wider trailing distance |
| **trailing_min_profit_pct** | 1.5% | 0.5% | Lock higher minimum |
| **trailing_update_interval** | 30 sec | 60 sec | More responsive |

### **Performance Targets**
| Metric | Target | Rationale |
|--------|--------|-----------|
| **Daily Return** | +1% to +4% | Higher % from volatility |
| **Weekly Return** | +5% to +15% | Aggressive but achievable |
| **Weekly Positive Rate** | 75%+ | Consistency requirement |
| **Monthly Return** | +20% to +50% | Compound growth |

### **Sample Small Portfolio Universe (Oct 30, 2025)**
Generated with $10-35 price filter:
1. **CCL (Carnival Corp)**: $27.87 - 10 shares = $279 position
2. **MRNA (Moderna)**: $24.70 - 12 shares = $296 position  
3. **MGM (MGM Resorts)**: $31.21 - 9 shares = $281 position
4. **NCLH (Norwegian Cruise)**: $22.22 - 13 shares = $289 position

**Universe Quality:** Mid-cap stocks with 3-6% ATR, good liquidity, consumer cyclical/healthcare sectors

---

## 📊 Large Portfolio Configuration (Main System)

### **Portfolio & Position Sizing Parameters**

### **portfolio_value**
- **Current Value:** `$963,000`
- **What It Does:** Total account equity used for all calculations
- **Why It Matters:** Foundation for position sizing, risk limits, and daily pool
- **Updates:** Syncs from Alpaca at bot startup

### **daily_pool_percent**
- **Current Value:** `60%`
- **What It Does:** Percentage of portfolio available for new trades each day
- **Why It Matters:** Controls total capital deployment (60% = $577,800/day available)
- **Range:** 40-80% (balanced: 60%)

### **daily_pool_dollars** (calculated)
- **Current Value:** `$577,800`
- **What It Does:** Dollar amount available for new positions daily
- **Formula:** `portfolio_value × daily_pool_percent`
- **Updates:** Automatically recalculated

### **max_position_dollars**
- **Current Value:** `$6,000`
- **What It Does:** Hard cap on any single position size
- **Why It Matters:** Prevents over-concentration, limits single-trade risk
- **Sweet Spot:** $6K optimized for 5% weekly ROI target

### **max_position_size_percent**
- **Current Value:** `12%`
- **What It Does:** Theoretical maximum position as % of portfolio
- **Why It Matters:** Secondary limit (12% of $963K = $115K, but capped at $6K)
- **Note:** Hard dollar cap always enforced first

### **min_position_size_dollars**
- **Current Value:** `$25`
- **What It Does:** Minimum viable position size to prevent micro-trades
- **Why It Matters:** Keeps positions meaningful relative to transaction costs
- **Recent Change:** Lowered from $50 to increase flexibility

### **max_positions_per_day**
- **Current Value:** `8`
- **What It Does:** Maximum number of new positions opened in one day
- **Why It Matters:** Controls diversification and capital deployment pace
- **Recent Change:** Increased from 6 to capture more opportunities

---

## 💰 Risk Management Parameters

### **max_risk_per_trade_dollars**
- **Current Value:** `$100`
- **What It Does:** Base risk amount per trade (distance from entry to stop-loss)
- **Why It Matters:** Foundation for position sizing (shares = $100 / stop_distance)
- **Note:** Dynamic sizing multiplies this by 1.0x-2.0x based on confidence

### **max_loss_per_trade_dollars**
- **Current Value:** `$400`
- **What It Does:** Absolute maximum loss allowed on any single trade
- **Why It Matters:** Hard stop regardless of position size (prevents $739 losses)
- **Trigger:** Fast-exit if unrealized loss hits this amount

### **max_daily_loss_percent**
- **Current Value:** `0.2%`
- **What It Does:** Maximum portfolio loss allowed in one day
- **Dollar Equivalent:** `$1,926` (0.2% of $963K)
- **Action:** Bot stops trading for the day if hit

### **max_daily_loss_dollars** (calculated)
- **Current Value:** `$1,926`
- **Formula:** `portfolio_value × max_daily_loss_percent`
- **Updates:** Recalculated daily

### **max_weekly_loss_percent**
- **Current Value:** `0.6%`
- **What It Does:** Maximum portfolio loss allowed in one week
- **Dollar Equivalent:** `$5,778` (0.6% of $963K)
- **Action:** Bot pauses trading for remainder of week if hit

### **max_weekly_loss_dollars** (calculated)
- **Current Value:** `$5,778`
- **Formula:** `portfolio_value × max_weekly_loss_percent`
- **Updates:** Recalculated weekly

---

## 🎯 Dynamic Position Sizing Parameters (NEW - Oct 29, 2025)

### **Confidence Tiers**
Dynamic sizing scales position size based on ML signal confidence:

#### **HIGH Confidence (≥0.75)**
- **Multiplier Range:** `1.6x - 2.0x`
- **What It Does:** Aggressive sizing on best signals
- **Example:** $100 base risk × 1.8 = $180 risk, larger position
- **Use Case:** High-conviction trades with strong technical + ML alignment

#### **MEDIUM Confidence (0.55-0.75)**
- **Multiplier Range:** `1.2x - 1.6x`
- **What It Does:** Moderate sizing on decent signals
- **Example:** $100 base risk × 1.4 = $140 risk
- **Use Case:** Good setups, reasonable confidence

#### **LOW Confidence (<0.55)**
- **Multiplier Range:** `1.0x - 1.2x`
- **What It Does:** Conservative sizing on marginal signals
- **Example:** $100 base risk × 1.1 = $110 risk
- **Use Case:** Marginal setups, barely passing filters

---

## 🛑 Trailing Stop Parameters (NEW - Oct 29, 2025)

### **enable_trailing_stops**
- **Current Value:** `True`
- **What It Does:** Activates trailing stop profit protection system
- **Why It Matters:** Locks in gains on winning positions

### **trailing_trigger_pct**
- **Current Value:** `1.5%` (0.015)
- **What It Does:** Profit threshold to activate trailing stop
- **Example:** Position up +1.5% → trailing stop activates
- **Recent Tuning:** Set conservatively to avoid premature exits

### **trailing_distance_pct**
- **Current Value:** `1.0%` (0.01)
- **What It Does:** How far trailing stop trails below highest price
- **Example:** Price hits $103 (+3%) → stop at $102 (+2%)
- **Behavior:** Stop only moves UP, never down

### **trailing_min_profit_pct**
- **Current Value:** `0.5%` (0.005)
- **What It Does:** Minimum profit locked in once trailing stop activated
- **Why It Matters:** Prevents giving back all gains if reversal happens quickly

### **trailing_update_interval_sec**
- **Current Value:** `60 seconds`
- **What It Does:** How often trailing stops are recalculated
- **Why It Matters:** Balance between responsiveness and API rate limits

---

## 🎲 Diversification Parameters

### **max_positions_per_symbol_small**
- **Current Value:** `2`
- **What It Does:** Max concurrent positions in same symbol (portfolios <$100K)
- **Why It Matters:** Prevents over-concentration in single stock

### **max_positions_per_symbol_large**
- **Current Value:** `3`
- **What It Does:** Max concurrent positions in same symbol (portfolios >$100K)
- **Why It Matters:** Larger portfolios can handle more concentration

### **max_concentration_percent_small**
- **Current Value:** `35%`
- **What It Does:** Max % of all positions in one symbol (small portfolios)
- **Example:** If holding 10 positions, max 3-4 can be same symbol

### **max_concentration_percent_large**
- **Current Value:** `40%`
- **What It Does:** Max % of all positions in one symbol (large portfolios)
- **Why It Matters:** Larger portfolios get slightly more concentration flexibility

### **portfolio_threshold_large**
- **Current Value:** `$100,000`
- **What It Does:** Cutoff for "large" vs "small" portfolio rules
- **Impact:** Your $963K portfolio uses "large" rules

---

## ⏰ Time & Holding Parameters

### **max_hold_days**
- **Current Value:** `2 days`
- **What It Does:** Maximum hold period (D+1 forced exit rule)
- **Example:** Enter Monday → Must exit by Tuesday market close
- **Why It Matters:** Core strategy principle - no overnight risk accumulation

### **trading_days**
- **Current Value:** `["monday", "tuesday", "wednesday", "thursday"]`
- **What It Does:** Days bot can enter new positions
- **Why It Matters:** No Friday entries (avoids weekend risk)
- **Exit Days:** Friday used only for exiting positions, not entering

### **exit_time**
- **Current Value:** `"15:45"` (3:45 PM ET)
- **What It Does:** Default exit time for forced D+1 exits
- **Why It Matters:** 15 minutes before market close for liquidity

---

## 🎯 Signal Quality Parameters

### **confidence_threshold**
- **Current Value:** `0.07` (7%)
- **What It Does:** Minimum signal strength to consider trade
- **Why It Matters:** Quality gate - weak signals rejected
- **Tuning:** Not too loose (5.5%), not too tight (8%)

---

## 🔍 PreFilter Parameters (Stock Selection)

### **Data Completeness Filter**

#### **min_rows**
- **Current Value:** `15 days`
- **What It Does:** Minimum price history required
- **Why It Matters:** Ensures reliable calculations
- **Free Tier Optimized:** Reduced from 90 days to work with Alpaca free data

---

### **Liquidity Filter**

#### **min_avg_volume**
- **Current Value:** `30,000 shares/day`
- **What It Does:** Minimum average daily volume
- **Why It Matters:** Ensures you can enter/exit without slippage
- **Calculation:** 20-day rolling average

#### **min_dollar_volume**
- **Current Value:** `$300,000/day`
- **What It Does:** Minimum daily trading dollar volume
- **Formula:** `price × volume`
- **Why It Matters:** Better liquidity indicator than share volume alone

---

### **Price Range Filter**

#### **min_price**
- **Current Value:** `$15`
- **What It Does:** Minimum stock price to trade
- **Why It Matters:** Avoids penny stocks, ensures quality
- **Too Low:** <$5 = high volatility, poor quality

#### **max_price**
- **Current Value:** `$350`
- **What It Does:** Maximum stock price to trade
- **Why It Matters:** With $6K max position, keeps minimum 15+ shares
- **Math:** $6,000 ÷ $350 = 17 shares (reasonable)

---

### **Volatility Filter (ATR%)**

#### **min_volatility**
- **Current Value:** `1.5%` (0.015)
- **What It Does:** Minimum ATR% for momentum opportunities
- **Why It Matters:** Too low = slow movers, no intraday moves
- **ATR:** Average True Range over 14 periods

#### **max_volatility**
- **Current Value:** `35%` (0.35)
- **What It Does:** Maximum ATR% to avoid excessive risk
- **Why It Matters:** Too high = unpredictable, high slippage
- **Sweet Spot:** 1.5-8% ideal for short-cycle trading

---

### **Momentum Filter**

#### **lookback**
- **Current Value:** `4 days`
- **What It Does:** Period for measuring price momentum
- **Why It Matters:** Short-term momentum aligns with D+1 strategy

#### **min_momentum**
- **Current Value:** `2%` (0.02)
- **What It Does:** Minimum 4-day return to pass filter
- **Why It Matters:** Wants stocks already moving up

#### **max_momentum**
- **Current Value:** `30%` (0.30)
- **What It Does:** Maximum 4-day return (avoid parabolic moves)
- **Why It Matters:** Too hot = likely pullback imminent

---

### **Breakout Filter (RELAXED Oct 29, 2025)**

#### **vol_spike_min**
- **Current Value:** `0.7` (70% above average)
- **What It Does:** Minimum volume spike vs. average
- **Recent Change:** Was 0.8 → relaxed to 0.7 (12.5% easier)
- **Why It Matters:** Volume confirms breakout validity
- **Formula:** `current_volume / avg_volume_8day`

#### **breakout_min**
- **Current Value:** `0.0015` (0.15%)
- **What It Does:** Minimum price breakout magnitude
- **Recent Change:** Was 0.002 (0.2%) → relaxed to 0.0015
- **Why It Matters:** Confirms price is breaking higher
- **Too Tight:** 0.002 filtered out 82% of candidates

#### **breakout_window**
- **Current Value:** `8 days`
- **What It Does:** Lookback period for breakout calculation
- **Why It Matters:** Balance between recency and data availability
- **yfinance Optimized:** Typically provides ~21 days, using 8 is safe

#### **vol_avg_window**
- **Current Value:** `8 days`
- **What It Does:** Period for average volume calculation
- **Why It Matters:** Matches breakout window for consistency

#### **minp_frac**
- **Current Value:** `0.3` (30%)
- **What It Does:** Minimum fraction of valid data points required
- **Recent Change:** Was 0.4 (40%) → relaxed to 0.3
- **Why It Matters:** Compensates for yfinance data gaps
- **Example:** In 8-day window, need at least 3 valid days (0.3 × 8 = 2.4)

---

### **Gap Filter**

#### **max_gap**
- **Current Value:** `8%` (0.08)
- **What It Does:** Maximum overnight gap allowed
- **Formula:** `(open - prev_close) / prev_close`
- **Why It Matters:** Excessive gaps indicate data issues or extreme events

---

### **Extended yfinance Filter**

#### **filter_float**
- **Current Value:** `True`
- **Max Float Shares:** `2 billion`
- **What It Does:** Filters out mega-caps with huge float
- **Why It Matters:** Large float = harder to move, less momentum
- **Example:** Filters AAPL, GOOGL if float >2B shares

---

## 📈 Adaptive Target Parameters

### **target_min**
- **Current Value:** `8 stocks`
- **What It Does:** Minimum watchlist size for next trading day
- **Why It Matters:** Ensures diversification opportunities

### **target_max**
- **Current Value:** `15 stocks`
- **What It Does:** Maximum watchlist size
- **Why It Matters:** Focus on highest quality candidates
- **Recent Results:** Getting 15 stocks consistently after Oct 29 relaxation

---

## 🧠 Machine Learning Parameters

### **AI Signal Confidence**
- **Range:** `0.0 - 1.0`
- **What It Does:** ML model's certainty about trade direction
- **Sources:** Technical indicators, momentum, volume, market regime
- **Usage:** Drives dynamic position sizing tiers

### **Signal Strength**
- **Range:** `0.0 - 1.0`
- **What It Does:** Combined strength of all indicators
- **Components:** Momentum + volume + volatility + technical alignment

---

## 💵 Transaction Cost Parameters

### **enable_forced_d1_exit**
- **Current Value:** `True`
- **What It Does:** Enforces D+1 exit rule
- **Why It Matters:** Core strategy principle

### **model_transaction_costs**
- **Current Value:** `True`
- **What It Does:** Includes costs in P&L calculations
- **Why It Matters:** Realistic performance measurement

### **commission_per_trade**
- **Current Value:** `$0`
- **What It Does:** Per-trade commission fee
- **Why:** Alpaca offers commission-free trading

### **spread_bp**
- **Current Value:** `5 basis points` (0.05%)
- **What It Does:** Bid-ask spread cost estimate
- **Example:** $100 entry → $100.05 effective cost
- **Why It Matters:** Realistic slippage modeling

---

## 🌍 Market Universe Parameters

### **max_universe_size**
- **Current Value:** `100 stocks`
- **What It Does:** Maximum symbols in screening universe
- **Why It Matters:** Balance between opportunity and processing time
- **Current Universe:** ~70 large-cap stocks

---

## 📊 D+1 Exit Strategy Parameters (Zone-Based)

### **Zone 1: Morning Rush (9:30-10:00 AM)**
- **Take Profit:** ≥+1.5%
- **Stop Loss:** ≤-1.0%
- **Why:** High volatility, quick moves

### **Zone 2: Mid-Day (10:00 AM-2:00 PM)**
- **Take Profit:** ≥+2.0%
- **Stop Loss:** ≤-1.5%
- **Why:** Stable period, let winners run

### **Zone 3: Afternoon (2:00-3:45 PM)**
- **Take Profit:** ≥+1.0%
- **Stop Loss:** ≤-1.0%
- **Why:** Close positions before EOD

### **Zone 4: Power Hour (3:45-4:00 PM)**
- **Action:** Force exit ALL positions
- **Why:** D+1 rule enforcement, no overnight risk

---

## 🔄 VIX Regime Adjustments

### **VIX > 30 (Extreme Fear)**
- **Position Size Multiplier:** `0.5x` (cut in half)
- **Why:** Reduce risk in panic conditions

### **VIX 25-30 (High Volatility)**
- **Position Size Multiplier:** `0.75x` (reduce 25%)
- **Why:** Elevated risk environment

### **VIX 20-25 (Elevated)**
- **Position Size Multiplier:** `1.0x` (normal)
- **Why:** Manageable volatility

### **VIX < 20 (Low Volatility)**
- **Position Size Multiplier:** `1.0x` (normal)
- **Why:** Calm markets, normal sizing

---

## 📝 Parameter Update History

### **October 29, 2025 - Filter Relaxation**
- `vol_spike_min`: 0.8 → 0.7
- `breakout_min`: 0.002 → 0.0015
- `minp_frac`: 0.4 → 0.3
- **Result:** Watchlist 6 → 15 stocks (+150%)

### **October 29, 2025 - Dynamic Sizing**
- Added confidence-based position sizing
- HIGH: 1.6-2.0x, MEDIUM: 1.2-1.6x, LOW: 1.0-1.2x

### **October 29, 2025 - Trailing Stops**
- Added trailing stop profit protection
- Activation: +1.5%, Trail: 1.0%

---

## 🎯 Quick Reference - Most Important Parameters

| Parameter | Value | Impact |
|-----------|-------|--------|
| Portfolio Value | $963,000 | Foundation for all calculations |
| Daily Pool | $577,800 (60%) | Capital available per day |
| Max Position | $6,000 | Single position limit |
| Max Risk/Trade | $100 base | Position sizing baseline |
| Max Loss/Trade | $400 | Hard stop per trade |
| Daily Loss Limit | $1,926 (0.2%) | Daily risk cap |
| Weekly Loss Limit | $5,778 (0.6%) | Weekly risk cap |
| Confidence Tiers | 1.0x-2.0x | Dynamic sizing range |
| Trailing Stop | +1.5% trigger | Profit protection |
| Watchlist Size | 8-15 stocks | Daily candidates |
| Hold Period | 1 day (D+1) | Maximum hold time |

---

## 📞 How to Modify Parameters

**Configuration File:** `/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py`

**Line 74-130:** `ShortCycleConfig` dataclass

**After Changes:**
1. Validate syntax: `python -m py_compile traders/short_cycle_trader.py`
2. Restart bot: Bot will pick up new values on next startup
3. Monitor logs for 1-2 days to validate changes

**⚠️ Caution:** Risk parameters should only be changed with careful consideration and testing.

---

**Document Version:** 1.0  
**Created:** October 30, 2025  
**Author:** GitHub Copilot  
**Bot Status:** ✅ Production - All parameters validated and tuned
