#!/bin/bash
#
# Quick Bot Restart Script with New Optimizations
# December 26, 2025
#

set -e  # Exit on error

echo "=========================================="
echo "🔄 Bot Restart with Optimizations"
echo "=========================================="
echo ""

# Change to project directory
cd /home/wes/Desktop/litebotx-usb-deployment

# 1. Stop existing bot
echo "1️⃣  Stopping existing bot..."
PID=$(ps aux | grep "python.*launcher" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "   Found bot process: PID $PID"
    kill $PID
    sleep 2
    echo "   ✅ Bot stopped"
else
    echo "   ℹ️  No bot process found"
fi

# 2. Check for stuck positions
echo ""
echo "2️⃣  Checking for stuck positions..."
source litebotx_env/bin/activate
python3 -c "
from connect_real_trading import RealPaperTradingEngine
try:
    engine = RealPaperTradingEngine(paper=True)
    positions = engine.get_positions()
    print(f'   Active positions: {len(positions)}')
    if positions:
        for p in positions:
            print(f'     {p[\"symbol\"]}: {p[\"qty\"]} shares @ \${float(p[\"current_price\"]):.2f}')
    else:
        print('   ✅ No open positions')
except Exception as e:
    print(f'   ⚠️  Could not check positions: {e}')
" 2>/dev/null || echo "   ⚠️  Could not connect to Alpaca"

# 3. Initialize blacklist
echo ""
echo "3️⃣  Initializing automated blacklist..."
python3 bot_v2/utils/symbol_blacklist_manager.py analyze 2>&1 | grep -E "BLACKLIST|symbols blocked|Analysis complete" || echo "   ℹ️  Blacklist analysis running..."
sleep 1

# 4. Show blacklist summary
echo ""
echo "4️⃣  Blacklist summary:"
python3 bot_v2/utils/symbol_blacklist_manager.py report 2>&1 | grep -A 10 "PERMANENT BLACKLIST" || echo "   ℹ️  Blacklist report generated"

# 5. Start bot
echo ""
echo "5️⃣  Starting bot with new optimizations..."
echo "   - RSI Entry: ≤ 30 (was 35)"
echo "   - Profit Target: 2% (was 3%)"
echo "   - Force Exit: 10:30 AM (was 2:30 PM)"
echo "   - Smart Exit Manager: 9 strategies"
echo "   - Automated Blacklist: Active"
echo ""

# Start bot in background
nohup python3 bot_v2/launcher.py > /dev/null 2>&1 &
NEW_PID=$!

sleep 3

# Verify it started
if ps -p $NEW_PID > /dev/null; then
    echo "   ✅ Bot started successfully (PID: $NEW_PID)"
else
    echo "   ❌ Bot failed to start"
    exit 1
fi

# 6. Monitor startup logs
echo ""
echo "6️⃣  Monitoring startup (10 seconds)..."
sleep 2
tail -20 logs/sprint1_alpaca.log | grep -E "Symbol blacklist|Smart exit|bot_v2 Launcher" || tail -20 logs/sprint1_alpaca.log

echo ""
echo "=========================================="
echo "✅ Bot Restart Complete"
echo "=========================================="
echo ""
echo "📊 Monitor logs:"
echo "   tail -f logs/sprint1_alpaca.log"
echo ""
echo "🔍 Check for errors:"
echo "   grep -i 'error\|exception' logs/sprint1_alpaca.log | tail -20"
echo ""
echo "🎯 Check smart exits:"
echo "   grep 'Smart Exit' logs/sprint1_alpaca.log"
echo ""
echo "🚫 Check blacklist:"
echo "   grep 'Blacklist Filter' logs/sprint1_alpaca.log"
echo ""
