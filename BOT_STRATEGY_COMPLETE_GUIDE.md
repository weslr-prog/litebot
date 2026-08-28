# Bot Strategy Complete Guide

Last updated: April 7, 2026

## 1) Beginner Overview: What This Bot Actually Does

This bot is a **short-hold swing trading bot**. It is trying to buy stocks that are:

- liquid enough to enter and exit safely,
- moving enough to produce a meaningful swing,
- in a tradable trend/pullback structure,
- and likely to bounce with confirmation.

In simple terms: it does **not** try to trade every stock. It looks for a specific "shape" of setup, then only takes the better-quality ones.

## 2) Which Strategy Is Active Right Now

Current behavior is dominated by **momentum + swing-pullback logic** with gate-based filtering and confidence scoring.

- Active style: momentum/swing continuation and pullback confirmation
- Scan windows are time-gated (it avoids random times of day)
- Entries require multiple confirmations, not just one indicator

Some older strategy components exist in code/history, but your live candidate flow is mainly controlled by:

1. Pre-filter (universe reduction)
2. Momentum/swing gates (entry validation)
3. Confidence threshold (final decision)

## 3) What the Bot Is Looking For (Easy Version)

A "good" stock for this bot usually has:

- **Enough daily volume** (easy to trade without heavy slippage)
- **Enough daily movement** (not too flat)
- **Not crazy volatility** (not pure chaos)
- **A valid pullback + bounce pattern**
- **Indicator alignment** (trend + RSI + support behavior)

If any of those are missing, it often gets rejected.

## 4) Technical Version: Selection Pipeline

### Stage A: Pre-filter (broad universe pruning)

The pre-filter removes names before strategy logic even starts.

Current conservative expansion (applied April 7, 2026):

| Parameter           |        Old |        New | Why                                            |
| ------------------- | ---------: | ---------: | ---------------------------------------------- |
| `min_volume`        |  3,000,000 |  1,500,000 | Add more tradable mid-liquidity names          |
| `min_dollar_volume` | 30,000,000 | 15,000,000 | Keep liquidity floor but admit more candidates |
| `min_atr_pct`       |      0.035 |      0.028 | Admit lower-volatility movers                  |
| `max_atr_pct`       |      0.060 |      0.068 | Admit slightly higher-volatility setups        |

Intent: increase final candidates from roughly **32 toward ~50** without opening the floodgates.

### Stage B: Strategy gates

After pre-filter, momentum/swing checks validate:

- trend structure,
- RSI band,
- pullback depth,
- support proximity,
- reversal/bounce behavior,
- and time window validity.

### Stage C: Confidence threshold

Even if a symbol passes gates, confidence must be high enough to execute.

## 5) What Is a Perfect-Fit Stock for This Bot

A near-perfect fit usually looks like this:

- Price in your configured trade range
- Strong average volume and dollar liquidity
- ATR in a tradable middle zone (not dead, not wild)
- In an uptrend, currently in a controlled pullback
- Near support or EMA/SMA structure
- Volume behavior suggests sellers are fading and buyers are reappearing

Example profile:

- Mid-cap stock, liquid, ADR/ATR moderate-high
- Pulled back 2-5% inside a larger trend
- RSI cooled from hot levels to a neutral band
- Early bounce candle appears near support with improving volume

## 6) Why Your Manually Chosen Stocks Often Fall Out of Range

Most manual picks fail for one of these reasons:

1. **Liquidity mismatch**: too thin for safe fills
2. **Volatility mismatch**: either too flat (no opportunity) or too explosive (poor risk control)
3. **Structure mismatch**: no valid trend + pullback pattern
4. **Timing mismatch**: setup not valid during active scan window
5. **Confirmation mismatch**: no bounce/reversal confirmation yet

This is why a stock can look "good" visually but still be rejected by the system.

## 7) How to Move From 32 Candidates to ~50 Safely

Use a staged approach (already started with conservative config expansion):

### Step 1: Conservative expansion (done)

- Lowered volume and dollar-volume floors
- Slightly widened ATR band

### Step 2: Observe for several sessions

Track:

- pre-filter pass count,
- gate rejection mix,
- confidence distribution,
- fill quality/slippage,
- win rate and drawdown shift.

### Step 3: Only if still too low (<45)

Use a small stretch adjustment (one knob at a time), then re-measure.

## 8) Practical Daily Workflow to Find Better-Fit Trades

Use this checklist before trusting a candidate:

1. Is liquidity clearly above your minimums?
2. Is ATR in the bot's valid zone?
3. Is the stock in a real trend, not random chop?
4. Is current action a pullback (not a breakdown)?
5. Is price near meaningful support/EMA/SMA context?
6. Do you see bounce/reversal confirmation?
7. Is it within scan window and confidence threshold likely to pass?

If you answer "no" to multiple items, it probably does not fit this bot.

## 9) Beginner Translation: Why This Discipline Matters

The bot is trying to avoid two expensive mistakes:

- buying stocks that are hard to exit,
- buying setups that look exciting but statistically underperform.

So the filter is strict on purpose. Broadening from 32 to ~50 is reasonable, but broadening too far can reduce trade quality fast.

## 10) Recommended Next Checkpoints

After this tuning pass, review 3-5 sessions and compare against prior baseline:

- Candidate count trend
- Percent of candidates dying at strategy gates
- Trade quality (win rate, drawdown, average R)
- Slippage/exit behavior in lower-liquidity names

If candidate count improved but quality collapsed, tighten one parameter back.
If quality stayed stable, keep the new range and continue monitoring.
