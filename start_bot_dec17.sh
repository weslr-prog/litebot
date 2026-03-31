#!/bin/bash
# Bot V2 Startup Script - Overnight & Next Day Trading
# Created: December 16, 2025
# Run tonight, let it run through tomorrow

cd /home/wes/Desktop/litebotx-usb-deployment

echo "=========================================="
echo "🚀 Starting Bot V2 - Overnight Mode"
echo "=========================================="
echo "📅 Started: $(date)"
echo "📋 Expected: 12 positions to exit tomorrow"
echo "💰 Expected buying power after exits: ~$483"
echo "🌙 Will run overnight and trade tomorrow"
echo ""

# Activate virtual environment
source litebotx_env/bin/activate

# Create timestamped log file
LOGFILE="logs/bot_overnight_$(date +%Y%m%d_%H%M%S).log"

echo "📝 Main log: $LOGFILE"
echo "📊 Activity log: logs/trading_activity.log"
echo "🔍 Debug log: logs/debug_detailed.log"
echo ""
echo "🖥️  Bot will run in FOREGROUND (terminal output visible)"
echo "⚠️  Keep this terminal open - Ctrl+C to stop"
echo ""
echo "=========================================="
echo ""

# Start bot in foreground with output to both terminal and log
python3 bot_v2/launcher.py 2>&1 | tee "$LOGFILE"

echo ""
echo "=========================================="
echo "🛑 Bot stopped at $(date)"
echo "=========================================="
