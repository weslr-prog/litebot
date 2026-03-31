# 🚀 LiteBotX Quick Reference

## Start the Bot
```bash
python3 start_litebotx.py
```

**What it does:**
- ✅ Checks dependencies (yfinance, alpaca-py)
- ✅ Validates watchlist (age < 24h, count 8-15)
- ✅ Auto-refreshes if stale
- ✅ Launches trading bot

---

## Common Commands

### Check Watchlist
```bash
python3 test/check_watchlist_health.py
```

### Manual Watchlist Refresh
```bash
python3 daily_watchlist_refresh.py
```

### View Current Watchlist
```bash
cat logs/current_watchlist.json | jq '.symbols'
```

### Check Positions
```bash
cat positions.json | jq
```

### View Logs
```bash
tail -f logs/trading_bot.log
```

---

## SystemD Service

### Start Service
```bash
sudo systemctl start litebotx.service
```

### Stop Service
```bash
sudo systemctl stop litebotx.service
```

### Check Status
```bash
sudo systemctl status litebotx.service
```

### Enable Auto-Start
```bash
sudo systemctl enable litebotx.service
```

### View Service Logs
```bash
sudo journalctl -u litebotx.service -f
```

---

## Directory Structure

```
📦 Root (29 files - core modules only)
├── start_litebotx.py          ⭐ Production entry point
├── config.py                   Configuration
├── data_loader.py              Data fetching
├── execution_engine.py         Order execution
├── pre_filter.py               Candidate filtering
├── positions.json              Position tracking
└── ...

📁 traders/                     Trading strategies
├── short_cycle_trader.py       Main 1-2 day D+1 trader

📁 logs/                        Logs and data
├── current_watchlist.json      Active 15-stock watchlist
└── *.log                       Log files

📁 docs/                        Documentation (87 files)
├── ZERO_BUY_PREVENTION.md      Zero-buy prevention guide
├── WORKSPACE_CLEANUP_SUMMARY.md This cleanup summary
└── ...

📁 test/                        Test scripts (89 files)
├── check_watchlist_health.py   Watchlist health check
└── test_*.py                   Unit tests

📁 scripts/                     Shell scripts
├── setup_daily_refresh_cron.sh Cron setup
└── archive/                    Old scripts (61 files)

📁 backups/                     Data backups
📁 monitoring/                  Self-monitoring system
```

---

## Automated Systems

### 1. Watchlist Refresh (Primary)
**When:** Every bot startup  
**What:** Checks age/count, refreshes if needed  
**Why:** Ensures fresh data always

### 2. Cron Job (Backup)
**When:** Mon-Fri 4:30 PM ET  
**What:** Daily watchlist refresh  
**Why:** Pre-market preparation

---

## Watchlist Health Indicators

### ✅ GREEN (Healthy)
- Age < 24 hours
- 8-15 symbols
- No action needed

### ⚠️ YELLOW (Stale)
- Age > 24 hours OR
- < 8 symbols
- **Action:** Refresh automatically

### ❌ RED (Critical)
- Age > 48 hours OR
- < 5 symbols
- **Action:** Immediate refresh

---

## Troubleshooting

### Bot won't start
```bash
# Check dependencies
python3 -c "import yfinance, alpaca"

# Check watchlist exists
ls -lh logs/current_watchlist.json

# Check config
python3 -c "from config import Config; print('OK')"
```

### Watchlist too old
```bash
# Manual refresh
python3 daily_watchlist_refresh.py

# Check result
python3 test/check_watchlist_health.py
```

### No trades
1. Check watchlist age
2. Check market hours
3. Check positions.json for same-day blocks
4. See `docs/ZERO_BUY_PREVENTION.md`

---

## File Locations

| What | Where |
|------|-------|
| Startup script | `start_litebotx.py` |
| Active positions | `positions.json` |
| Current watchlist | `logs/current_watchlist.json` |
| Trading logs | `logs/trading_bot.log` |
| Configuration | `config.py`, `stock_config.py` |
| Main trader | `traders/short_cycle_trader.py` |
| Documentation | `docs/` |
| Tests | `test/` |
| Archives | `scripts/archive/` |

---

## Quick Stats (Oct 28, 2024)

**Account:** $972,224 (paper)  
**Watchlist:** 15 stocks (0.3 hours old)  
**Open Positions:** 4 (for D+1 exit tomorrow)  
**Workspace:** 29 core files (down from 300+)

---

## Emergency Contacts

**Documentation:** See `docs/` folder  
**Zero-buy Prevention:** `docs/ZERO_BUY_PREVENTION.md`  
**Cleanup Summary:** `docs/WORKSPACE_CLEANUP_SUMMARY.md`

---

**Last Updated:** October 28, 2024  
**Status:** ✅ Bot fully autonomous and operational
