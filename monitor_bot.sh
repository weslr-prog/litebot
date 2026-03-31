#!/bin/bash
# Simple monitoring script - check if bot is running and show recent activity
# Usage: ./monitor_bot.sh

cd /home/wes/Desktop/litebotx-usb-deployment

echo "=================================="
echo "🔍 Bot Monitoring Dashboard"
echo "=================================="
echo "📅 $(date)"
echo ""

# Check if bot is running
if pgrep -f "bot_v2/launcher.py" > /dev/null; then
    PID=$(pgrep -f "bot_v2/launcher.py")
    echo "✅ Bot is RUNNING (PID: $PID)"
else
    echo "❌ Bot is NOT RUNNING"
fi

echo ""
echo "📊 Current Portfolio Status:"
echo "----------------------------"
python3 << 'EOF'
import json
with open('positions.json') as f:
    positions = json.load(f)
active = [p for p in positions if p['status'] == 'entered']
print(f"Active positions: {len(active)}")
total_value = sum(p['entry_price'] * p['position_size_shares'] for p in active)
print(f"Capital tied up: ${total_value:.2f}")
print(f"\nPositions:")
for p in active:
    value = p['entry_price'] * p['position_size_shares']
    print(f"  {p['symbol']}: ${value:.2f} (entry: {p['entry_date']}, exit: {p['exit_date']})")
EOF

echo ""
echo "📝 Recent Log Activity (Last 20 lines):"
echo "----------------------------------------"
LATEST_LOG=$(ls -t logs/bot_dec17_*.log 2>/dev/null | head -1)
if [ -z "$LATEST_LOG" ]; then
    LATEST_LOG="logs/sprint1_alpaca.log"
fi

if [ -f "$LATEST_LOG" ]; then
    echo "Log: $LATEST_LOG"
    echo ""
    tail -20 "$LATEST_LOG" | grep -E "Exit|SELL|Entry|ERROR|⚠️|✅" || tail -20 "$LATEST_LOG"
else
    echo "No log file found"
fi

echo ""
echo "=================================="
