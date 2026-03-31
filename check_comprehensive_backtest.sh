#!/bin/bash
# Monitor comprehensive backtest progress

echo "=========================================="
echo "COMPREHENSIVE BACKTEST MONITOR"
echo "=========================================="
echo ""

# Check if process is running
if ps aux | grep -v grep | grep "run_comprehensive_backtest.py" > /dev/null; then
    echo "✅ Backtest is RUNNING"
    
    # Count how many configurations completed
    configs_done=$(grep -c "Results for" comprehensive_backtest.log 2>/dev/null || echo "0")
    total_configs=12  # 6 configs × 2 time periods
    
    echo "Progress: $configs_done / $total_configs configurations completed"
    echo ""
    
    # Show current configuration being tested
    echo "Current activity:"
    tail -20 comprehensive_backtest.log | grep -E "Testing:|Fetching|Results for" | tail -5
    
else
    echo "⚠️  Backtest process not found"
    
    # Check if completed
    if grep -q "BACKTEST COMPLETE" comprehensive_backtest.log 2>/dev/null; then
        echo "✅ BACKTEST COMPLETED!"
        echo ""
        echo "Summary of results:"
        grep -A 20 "HISTORICAL DATA COMPARISON" comprehensive_backtest.log | tail -15
    fi
fi

echo ""
echo "=========================================="
echo "Full log: tail -f comprehensive_backtest.log"
echo "=========================================="
