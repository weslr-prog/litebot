# Free Upgrades Implementation Plan

**Date:** 2026-09-26  
**Bot Version:** bot_v2 (commit ccaf839)  
**Hardware:** i5-10500T, 16GB RAM, Ubuntu 24.04  
**Goal:** Implement free high-ROI upgrades for better data freshness and signal quality

---

## 📋 Implementation Checklist

### Phase 1: WebSocket Upgrades (Highest ROI - Free)

| #   | Task                                                    | Status  | Est. Time | Dependencies                     |
| --- | ------------------------------------------------------- | ------- | --------- | -------------------------------- |
| 1.1 | Add Polygon.io WebSocket client                         | ✅ DONE | 30 min    | Polygon API key (exists in .env) |
| 1.2 | Replace `_get_realtime_price()` polling with Polygon WS | ✅ DONE | 45 min    | 1.1                              |
| 1.3 | Test Polygon WS in shadow mode (log only)               | ✅ DONE | 15 min    | 1.2                              |
| 1.4 | Validate Polygon WS data quality vs REST                | ✅ DONE | 30 min    | 1.3                              |
| 1.5 | Switch `_get_realtime_price()` to Polygon WS primary    | ✅ DONE | 15 min    | 1.4                              |
| 1.6 | Add Alpaca WebSocket client                             | ✅ DONE | 30 min    | Alpaca credentials (exist)       |
| 1.7 | Add Alpaca WS as secondary fallback                     | ✅ DONE | 30 min    | 1.6                              |
| 1.8 | Test both WS in parallel (shadow)                       | ✅ DONE | 15 min    | 1.7                              |
| 1.9 | Switch fallback chain: Polygon WS → Alpaca WS → REST    | ✅ DONE | 15 min    | 1.8                              |

### Phase 1 Test Results — 2026-09-26

Code is complete and compiles. Real bugs found and fixed during testing:

1. **`WebSocketClient.run()` signature** — was called as `run(handle_message=...)`; the
   library requires positional `handle_msg`. Fixed.
2. **`WebSocketClient.close()` is a coroutine** — was called synchronously, producing
   `RuntimeWarning: coroutine ... was never awaited`. Fixed via a guarded event loop.
3. **Feed must be a full hostname** — passing `feed="delayed"` built
   `wss://delayed/stocks`, which failed DNS resolution (`socket.gaierror`).
   Added a `FEED_HOSTNAMES` map so `delayed` → `delayed.polygon.io`.
4. **Optimistic `_connected` flag** — both clients set "connected" *before* the server
   confirmed. Now `start()` waits for a real `status: connected` (Polygon) or the
   first inbound message (Alpaca), and returns the truthful result.
5. **alpaca-py requires coroutine handlers** — `_handle_quote` / `_handle_trade` were
   sync, failing with `handler must be a coroutine function`. Made both `async`.

**Polygon outcome: blocked by plan, not by code.** The endpoint and auth succeed
(`status: connected`), but subscribing returns:
`"Your plan doesn't include websocket access. Visit https://massive.com/pricing"`.
The same key is also `403 NOT_AUTHORIZED` on REST `/v2/last/trade`.
Polygon stays **off by default** until the plan is upgraded.

**Alpaca outcome: working.** Connects to `wss://stream.data.alpaca.markets/v2/iex` and
subscribes successfully. Handlers, price extraction (trade → quote mid), and
`get_data_age()` staleness were verified with synthetic messages because the test ran
**Saturday 20:28 ET, market closed**, so no live trades were flowing.

**Launcher routing verified:** WebSocket path returned the cached price `123.45`; with
the cache aged 999s the call correctly fell through to REST and returned a live quote.
REST fallbacks are intact, so behavior is unchanged while both providers are off.

### Phase 1 Activation (both default to `false`)

| Variable                   | Default  | Purpose                          |
| -------------------------- | -------- | -------------------------------- |
| `ENABLE_POLYGON_WEBSOCKET` | `false`  | Polygon WS primary               |
| `ENABLE_ALPACA_WEBSOCKET`  | `false`  | Alpaca WS secondary fallback     |
| `WS_MAX_SYMBOLS`           | `100`    | Cap subscriptions (free tier)    |
| `WS_MAX_AGE_SECONDS`       | `60`     | Reject stale quotes, use REST    |
| `POLYGON_FEED`             | `delayed`| `delayed` or `real-time`         |

To enable Alpaca only (Polygon is blocked by plan):

```bash
echo "ENABLE_ALPACA_WEBSOCKET=true" >> .env
```

Full chain when enabled: **Polygon WS → Alpaca WS → Alpaca REST → DataLoader/yfinance.**

### Phase 2: Free Data Source Integration (Medium ROI - Free)

| #   | Task                                                 | Status  | Est. Time | Dependencies         |
| --- | ---------------------------------------------------- | ------- | --------- | -------------------- |
| 2.1 | Add Finnhub insider transactions to signal generator | ⬜ TODO | 45 min    | Finnhub key (exists) |
| 2.2 | Add Finnhub short interest / borrow rates            | ⬜ TODO | 30 min    | Finnhub key          |
| 2.3 | Add Finnhub analyst ratings/estimates                | ⬜ TODO | 30 min    | Finnhub key          |
| 2.4 | Integrate as confidence boosters in signal generator | ⬜ TODO | 45 min    | 2.1-2.3              |
| 2.4 | Add short interest filter (>20% = avoid/short bias)  | ⬜ TODO | 30 min    | 2.2                  |

### Phase 3: Validation & Monitoring

| #   | Task                                                    | Status  | Est. Time |
| --- | ------------------------------------------------------- | ------- | --------- |
| 3.1 | Shadow mode: run new data sources in parallel, log only | ⬜ TODO | 1 week    |
| 3.2 | Compare WS vs REST latency/accuracy metrics             | ⬜ TODO | 2 days    |
| 3.3 | A/B test: old params vs new params (paper)              | ⬜ TODO | 1 week    |
| 3.4 | Document latency improvements                           | ⬜ TODO | 30 min    |

---

## 🎯 Quick Wins Priority Order

### Quick Win 1: Polygon WebSocket (30 min) ⭐ HIGHEST ROI

- **File to create:** `bot_v2/data/polygon_ws.py`
- **Integration:** Replace `_get_realtime_price()` polling
- **Test:** Shadow mode → compare latency vs REST

### Quick Win 2: Alpaca WebSocket (30 min) ⭐ HIGH ROI

- **File to create:** `bot_v2/data/alpaca_ws.py`
- **Integration:** Secondary fallback after Polygon
- **Test:** Shadow mode → compare latency

### Quick Win 3: Finnhub Free Data (2 hrs)

- Insider transactions → confidence boost
- Short interest → squeeze avoidance filter
- Analyst ratings → momentum confirmation

---

## 📝 Implementation Notes

### Polygon WebSocket Integration Points

1. **New file:** `bot_v2/data/polygon_ws.py` - WebSocket client class
2. **Modify:** `bot_v2/data/alpaca_data_helper.py` or create `bot_v2/data/polygon_ws.py`
3. **Modify:** `bot_v2/launcher.py` → `_get_realtime_price()` method
4. **Config:** Add `polygon_ws_enabled` to `ShortCycleConfig` (default True)

### Alpaca WebSocket Integration Points

1. **New file:** `bot_v2/data/alpaca_ws.py`
2. **Modify:** `bot_v2/launcher.py` → `_get_realtime_price()` fallback chain
3. **Config:** Add `alpaca_ws_enabled` to `ShortCycleConfig` (default True)

### Fallback Chain (After Implementation)

```
1. Polygon WebSocket (primary - real-time trades/quotes)
2. Alpaca WebSocket (secondary - real-time quotes)
3. Alpaca REST (get_stock_latest_trade)
4. DataLoader.get_current_price (yfinance fallback)
```

---

## 🧪 Testing Protocol

### Shadow Mode Testing (Per WebSocket)

1. **Deploy** new WS client alongside existing polling
2. **Log** both WS price and REST price with timestamps
3. **Measure:** Latency delta, price delta, uptime
4. **Duration:** 1 trading session (6.5 hrs)
5. **Success criteria:**
   - WS latency < 100ms vs REST 500ms+
   - Price delta < 0.01% (arbitrage check)
   - Uptime > 99.5%

### Rollout Checklist

- [ ] Shadow mode passes for Polygon WS
- [ ] Shadow mode passes for Alpaca WS
- [ ] Fallback chain works (WS → WS → REST → yfinance)
- [ ] No increase in API errors
- [ ] No increase in memory/CPU
- [ ] Switch primary to Polygon WS
- [ ] Monitor for 1 full trading day

---

## 📅 Timeline

| Date       | Milestone                                      |
| ---------- | ---------------------------------------------- |
| 2026-09-26 | Plan created                                   |
| 2026-09-26 | Polygon WS implemented & shadow tested         |
| 2026-09-26 | Alpaca WS implemented & shadow tested          |
| 2026-09-27 | Finnhub free data integrated                   |
| 2026-09-28 | Shadow mode validation complete                |
| 2026-09-29 | Full rollout (switch primary to Polygon WS)    |
| 2026-09-30 | Finnhub data integrated as confidence boosters |

---

## 📊 Success Metrics

| Metric                  | Baseline    | Target              | Measurement                 |
| ----------------------- | ----------- | ------------------- | --------------------------- |
| Price latency (polling) | ~500-2000ms | **<100ms**          | WS message timestamp vs now |
| API calls/min           | ~150        | **<10** (1 WS conn) | Alpaca/Polygon dashboard    |
| Stop loss slippage      | ~0.5-1.0%   | **<0.3%**           | Exit price vs signal price  |
| Stop loss hit rate      | ~40%        | **<30%**            | Exit reason analysis        |
| API errors/min          | ~2-5        | **<0.5**            | Error logs                  |

---

## 🚨 Rollback Plan

If issues arise:

1. **Immediate:** Set `polygon_ws_enabled = False` in config
2. **Fallback:** Alpaca WS → REST → yfinance chain still works
3. **Full rollback:** `git revert <commit>` (single commit per WS)

---

## 📝 Notes

- **Polygon API Key:** Already in `.env` as `POLYGON_API_KEY`
- **Alpaca Credentials:** Already in `.env` as `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`
- **Finnhub Key:** Already in `.env` as `FINNHUB_API_KEY` (check)
- **Polygon Free Tier:** 5 concurrent WS connections, delayed feed (15 min) - sufficient for swing
- **Alpaca Free Tier:** Unlimited WS connections on paper trading

---

_Last Updated: 2026-09-26_
_Next Review: After Polygon WS shadow test_
