# Bot v2 Improvement Checklist

Ordered by expected impact on productivity and reliability.

## �� 🚀 Highest Impact

### 1. Switch Primary Market Data to Polygon.io

- **Why:** yfinance suffers from rate limits, data gaps, and latency during market hours.
- **Expected Benefit:** More reliable, faster data leading to better signal timing and fewer missed opportunities.
- **Implementation:** Modify data loader to use Polygon as primary source with yfinance fallback.
- **Status:** [ ] Not Started

### 2. Refine Entry Quality and Signal Filtering

- **Why:** Current win/loss ratio is balanced; improving signal quality can increase average profit per trade.
- **Expected Benefit:** Higher win rate and/or larger average winners.
- **Actions:**
  - Increase confidence threshold (test 0.24–0.26)
  - Test volatility-adjusted stop loss (e.g., 1.5×ATR) instead of fixed percent
  - Consider entry timing delay (wait for bar close)
  - Evaluate profit target increase (e.g., 8–10%) while keeping stop loss at 5–5.5%
- **Status:** [ ] Not Started

### 3. Enhance Prefilter for Better Candidate Quality

- **Why:** Current prefilter yields ~80 candidates; improving quality can reduce noise.
- **Expected Benefit:** Higher signal-to-noise ratio, fewer false signals.
- **Actions:**
  - Test moving volatility check before volume (if high volume but noisy)
  - Add minimum 20-day average dollar volume filter
  - Consider relative strength vs. SPY filter (only take longs in strong sectors)
- **Status:** [ ] Not Started

### 4. Improve Trade Strategy Tuning

- **Why:** Current strategy allocation (Gap & Go 65%, Momentum 35%) is reasonable but can be optimized.
- **Expected Benefit:** Better alignment with market regimes.
- **Actions:**
  - Test dynamic strategy allocation based on volatility regime (e.g., more Gap & Go in high volatility)
  - Evaluate sector strength filter (only long in sectors with positive relative strength)
  - Consider adjusting hold times based on volatility (e.g., longer holds in low volatility)
- **Status:** [ ] Not Started

### 5. Operational Monitoring and Alerting

- **Why:** Ensures system health and provides data for analysis.
- **Expected Benefit:** Reduced downtime, better performance tracking.
- **Actions:**
  - Verify liveness heartbeat is working and alert on stagnation
  - Implement daily equity curve snapshot to CSV/SQLite for analysis
  - Soft-enable entry quality screener (block only REJECT quality)
  - Add more detailed trade logging (entry/exit reasons, MFE/MAE)
- **Status:** [ ] Not Started

## �� 📋 How to Use This Checklist

- Start with the top item and move down only when the previous item is complete and validated.
- For each item, implement, test in paper trading for at least 3-5 trading days, then evaluate.
- Keep a log of changes and their observed impact.

## � ✅ Completed Items

- [ ]
