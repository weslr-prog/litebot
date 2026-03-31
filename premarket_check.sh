#!/bin/bash
# Quick Start Script for Nov 20 Live Trading
# Run this before market open (before 9:30 AM)

echo "=============================================================================="
echo "LITEBOTX LIVE TRADING - PRE-MARKET CHECKLIST"
echo "=============================================================================="
echo ""

# Navigate to bot directory
cd /home/wes/Desktop/litebotx-usb-deployment

# 1. Verify Trading Mode (based on API URL)
echo "[1] Checking trading mode..."
API_URL=$(grep APCA_API_BASE_URL .env | cut -d'=' -f2)
if [[ "$API_URL" == *"paper"* ]]; then
    echo "    📝 PAPER TRADING MODE"
    echo "    To switch to live: Update API keys and URL in .env"
else
    echo "    ✅ LIVE TRADING MODE"
    echo "    ⚠️  Real money at risk!"
fi
echo ""

# 2. Check Day Trades Available
echo "[2] Checking day trade availability..."
python3 - << 'PY'
from utils.day_trade_tracker import DayTradeTracker
tracker = DayTradeTracker()
count = tracker.count_in_window()
remaining = tracker.trades_remaining()
print(f"    Day trades used in window: {count}/3")
print(f"    Day trades available today: {remaining}/3")
if remaining == 3:
    print("    ✅ Full allowance available")
elif remaining > 0:
    print(f"    ⚠️  Limited to {remaining} emergency trades")
else:
    print("    ❌ No day trades available (D+1 holds only)")
PY
echo ""

# 3. Check Today's Position Limits
echo "[3] Checking today's position limits..."
python3 - << 'PY'
import datetime as dt
from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
trader = ShortCycleTrader(config=ShortCycleConfig(), launch_gui=False)
day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][dt.datetime.now().weekday()]
max_pos, max_pct = trader.get_max_positions_for_day()
print(f"    {day_name} limits:")
print(f"      Max positions: {max_pos}")
print(f"      Max portfolio: {max_pct*100:.0f}%")
if max_pos == 0:
    print("    ⚠️  Friday with no emergency trades - no entries allowed")
elif max_pos <= 3:
    print("    ✅ Conservative day (Mon-Wed)")
else:
    print("    ✅ Aggressive day (Thursday)")
PY
echo ""

# 4. System Status
echo "[4] Verifying bot systems..."
python3 - << 'PY'
from connect_real_trading import RealPaperTradingEngine
import sys
try:
    engine = RealPaperTradingEngine()
    print("    ✅ Trading engine initialized")
except Exception as e:
    print(f"    ❌ Trading engine error: {e}")
    sys.exit(1)
PY
echo ""

echo "=============================================================================="
echo "PRE-MARKET CHECKLIST COMPLETE"
echo "=============================================================================="
echo ""
echo "To start live trading at 9:30 AM:"
echo "  python3 start_small_portfolio_trader.py"
echo ""
echo "To monitor in real-time:"
echo "  tail -f trading_bot.log"
echo ""
echo "=============================================================================="
