#!/bin/bash
# Check backtest cron job health and performance
# Usage: ./check_backtest_health.sh

BACKTEST_LOG="/home/wes/Desktop/litebotx-usb-deployment/backtest/auto_backtest.log"
SUMMARY_CSV="/home/wes/Desktop/litebotx-usb-deployment/backtest/results/summaries.csv"

echo "=========================================="
echo "LITEBOTX BACKTEST HEALTH CHECK"
echo "Date: $(date)"
echo "=========================================="
echo

# 1. Check if cron job is configured
echo "📋 CRON JOB STATUS:"
if crontab -l 2>/dev/null | grep -q "run_nightly_backtest.sh"; then
    echo "✅ Cron job found:"
    crontab -l | grep "run_nightly_backtest.sh"
else
    echo "❌ No backtest cron job found!"
fi
echo

# 2. Check last backtest run
echo "🕐 LAST BACKTEST RUN:"
if [ -f "$BACKTEST_LOG" ]; then
    LAST_RUN=$(grep "Backtest session complete" "$BACKTEST_LOG" | tail -1)
    echo "$LAST_RUN"
    
    # Extract timestamp
    LAST_RUN_DATE=$(echo "$LAST_RUN" | grep -oP '\w+ \w+ +\d+ \d+:\d+:\d+ \w+ \w+ \d+')
    if [ -n "$LAST_RUN_DATE" ]; then
        LAST_RUN_EPOCH=$(date -d "$LAST_RUN_DATE" +%s 2>/dev/null)
        NOW_EPOCH=$(date +%s)
        HOURS_AGO=$(( ($NOW_EPOCH - $LAST_RUN_EPOCH) / 3600 ))
        echo "⏰ Last run: $HOURS_AGO hours ago"
        
        if [ $HOURS_AGO -gt 30 ]; then
            echo "⚠️  WARNING: Last backtest run was >30 hours ago!"
        fi
    fi
else
    echo "❌ Log file not found: $BACKTEST_LOG"
fi
echo

# 3. Check recent results
echo "📊 RECENT BACKTEST RESULTS (Last 5 runs):"
if [ -f "$SUMMARY_CSV" ]; then
    echo "Timestamp                    Symbol  Final Equity  Return%  Sharpe"
    tail -5 "$SUMMARY_CSV" | awk -F',' '{printf "%-25s %-7s $%-12s %-8s %s\n", substr($1,1,19), $2, $7, $8, $9}' | tail -5
    
    # Count total results
    TOTAL_RUNS=$(tail -100 "$SUMMARY_CSV" | wc -l)
    echo
    echo "Total backtest runs in summary: $TOTAL_RUNS (last 100 entries)"
else
    echo "❌ Summary file not found: $SUMMARY_CSV"
fi
echo

# 4. Check for errors in log
echo "⚠️  RECENT ERRORS/WARNINGS:"
if [ -f "$BACKTEST_LOG" ]; then
    ERROR_COUNT=$(tail -1000 "$BACKTEST_LOG" | grep -c "ERROR")
    WARNING_COUNT=$(tail -1000 "$BACKTEST_LOG" | grep -c "WARNING")
    echo "Errors in last 1000 lines: $ERROR_COUNT"
    echo "Warnings in last 1000 lines: $WARNING_COUNT"
    
    if [ $ERROR_COUNT -gt 0 ]; then
        echo
        echo "Last 5 errors:"
        tail -1000 "$BACKTEST_LOG" | grep "ERROR" | tail -5
    fi
fi
echo

# 5. Check if backtests are running now
echo "🔄 CURRENTLY RUNNING:"
if ps aux | grep -E "(test_optimized_backtest|test_backtesting_demo|walkforward_tester)" | grep -v grep > /dev/null; then
    echo "✅ Backtest process is currently running:"
    ps aux | grep -E "(test_optimized_backtest|test_backtesting_demo|walkforward_tester)" | grep -v grep
else
    echo "✅ No backtest processes running (normal during market hours)"
fi
echo

# 6. Check live trading bot status
echo "🤖 LIVE TRADING BOT STATUS:"
if ps aux | grep "litebotx_launcher.py" | grep -v grep > /dev/null; then
    BOT_PID=$(ps aux | grep "litebotx_launcher.py" | grep -v grep | awk '{print $2}')
    BOT_RUNTIME=$(ps -p $BOT_PID -o etime= | tr -d ' ')
    echo "✅ Trading bot is running (PID: $BOT_PID, Runtime: $BOT_RUNTIME)"
else
    echo "❌ Trading bot is NOT running!"
fi
echo

# 7. Check for file conflicts (shared resources)
echo "🔒 FILE LOCK CHECK:"
SHARED_FILES=("positions.json" "trading_bot.log" "cache/*.csv")
CONFLICTS=0
for file in "${SHARED_FILES[@]}"; do
    if lsof "/home/wes/Desktop/litebotx-usb-deployment/$file" 2>/dev/null | grep -q python; then
        echo "⚠️  $file is currently locked by Python process"
        CONFLICTS=$((CONFLICTS + 1))
    fi
done
if [ $CONFLICTS -eq 0 ]; then
    echo "✅ No file conflicts detected"
fi
echo

# 8. Disk usage
echo "💾 DISK USAGE:"
du -sh /home/wes/Desktop/litebotx-usb-deployment/backtest/ 2>/dev/null
echo

# 9. Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "Cron Schedule: Daily at 2:00 AM"
echo "Analysis Duration: ~1-2 seconds"
echo "Impact on Live Trading: None (runs during off-hours)"
echo
echo "Analysis runs:"
echo "  - D+1 Strategy Performance Analysis (last 30 days)"
echo "  - Analyzes actual trades from positions.json"
echo "  - Calculates win rate, profit factor, P&L"
echo "  - Identifies top winners/losers"
echo "  - Validates strategy performance"
echo
echo "Results stored in:"
echo "  - Log: $BACKTEST_LOG"
echo "  - Analysis: backtest/results/d1_performance_analysis_*.txt"
echo "=========================================="
