#!/bin/bash
# Check backtest progress

echo "=========================================="
echo "BACKTEST PROGRESS MONITOR"
echo "=========================================="
echo ""

# Check if process is running
if ps aux | grep -v grep | grep "strategy_backtest.py" > /dev/null; then
    echo "✅ Backtest is RUNNING"
    echo ""
else
    echo "⚠️  Backtest process not found"
    echo ""
fi

# Show last 30 lines of log
echo "Recent log output:"
echo "------------------------------------------"
tail -30 backtest_full.log
echo ""
echo "=========================================="
echo "To view full log: tail -f backtest_full.log"
echo "=========================================="
