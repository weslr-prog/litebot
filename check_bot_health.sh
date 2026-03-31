#!/bin/bash
#
# BOT HEALTH CHECK - Quick verification that bot is running and working
#

echo "========================================================================"
echo "  🤖 LITEBOTX HEALTH CHECK"
echo "========================================================================"
echo ""

# Check if bot process is running
echo "1️⃣  PROCESS CHECK"
BOT_PID=$(ps aux | grep "start_small_portfolio_trader.py" | grep -v grep | awk '{print $2}')
if [ -z "$BOT_PID" ]; then
    echo "   ❌ Bot is NOT running"
    echo "   💡 Start with: python3 start_small_portfolio_trader.py &"
    exit 1
else
    echo "   ✅ Bot is running (PID: $BOT_PID)"
    # Check how long it's been running
    UPTIME=$(ps -p $BOT_PID -o etime= | tr -d ' ')
    echo "   ⏱️  Uptime: $UPTIME"
fi

echo ""
echo "2️⃣  CONFIGURATION CHECK"
# Check if enhanced components are being imported
if python3 -c "from traders.short_cycle_trader import AISignalGenerator; from small_portfolio_config import SmallPortfolioConfig; config = SmallPortfolioConfig(); gen = AISignalGenerator(config); print('Has quality_scorer:', hasattr(gen, 'quality_scorer') and gen.quality_scorer is not None)" 2>&1 | grep -q "Has quality_scorer: True"; then
    echo "   ✅ Quality scorer integrated"
else
    echo "   ❌ Quality scorer NOT integrated"
fi

echo ""
echo "3️⃣  LOG FILE CHECK"
LOG_FILE="logs/short_cycle_trader.log"
if [ -f "$LOG_FILE" ]; then
    echo "   ✅ Log file exists: $LOG_FILE"
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo "   📊 Size: $LOG_SIZE"
    
    # Check for recent activity (last 5 minutes)
    FIVE_MIN_AGO=$(date -d '5 minutes ago' '+%Y-%m-%d %H:%M')
    RECENT_LINES=$(grep "$FIVE_MIN_AGO" "$LOG_FILE" 2>/dev/null | wc -l)
    
    if [ $RECENT_LINES -gt 0 ]; then
        echo "   ✅ Recent activity detected ($RECENT_LINES lines in last 5 min)"
    else
        echo "   ⚠️  No recent activity in last 5 minutes"
        echo "   💡 Bot may be sleeping between cycles"
    fi
else
    echo "   ❌ Log file not found"
fi

echo ""
echo "4️⃣  LATEST ACTIVITY"
if [ -f "$LOG_FILE" ]; then
    echo "   Last 10 log entries:"
    echo "   ----------------------------------------"
    tail -10 "$LOG_FILE" | sed 's/^/   /'
    echo "   ----------------------------------------"
fi

echo ""
echo "5️⃣  QUALITY SCORING CHECK"
# Check if quality scoring has been used today
TODAY=$(date '+%Y-%m-%d')
if grep -q "🎯.*quality=.*multiplier=" "$LOG_FILE" 2>/dev/null; then
    echo "   ✅ Quality scoring is ACTIVE"
    QUALITY_COUNT=$(grep "🎯.*quality=.*multiplier=" "$LOG_FILE" | wc -l)
    echo "   📊 Quality scores generated: $QUALITY_COUNT"
    echo ""
    echo "   Latest quality score:"
    echo "   ----------------------------------------"
    grep "🎯.*quality=.*multiplier=" "$LOG_FILE" | tail -3 | sed 's/^/   /'
    echo "   ----------------------------------------"
else
    echo "   ⚠️  No quality scoring seen yet"
    echo "   💡 Normal if no signals have been generated today"
fi

echo ""
echo "========================================================================"
echo "  📊 SUMMARY"
echo "========================================================================"
echo ""

if [ -n "$BOT_PID" ] && [ -f "$LOG_FILE" ]; then
    echo "   ✅ Bot appears to be running normally"
    echo ""
    echo "   🔍 To monitor in real-time:"
    echo "      tail -f $LOG_FILE"
    echo ""
    echo "   🔍 To see signal generation:"
    echo "      grep '🎯.*quality=' $LOG_FILE | tail -20"
    echo ""
    echo "   🔍 To check today's trades:"
    echo "      grep '$(date +%Y-%m-%d)' $LOG_FILE | grep -E '(ENTRY|EXIT|BUY|SELL)'"
else
    echo "   ⚠️  Bot may have issues - check logs"
fi

echo ""
