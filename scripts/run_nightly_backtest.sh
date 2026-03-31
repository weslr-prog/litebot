#!/bin/bash
# Run LiteBotX D+1 Strategy Performance Analysis
# Analyzes actual trading results from positions.json
cd /home/wes/Desktop/litebotx-usb-deployment

echo "==== D+1 Strategy Performance Analysis: $(date) ====" >> backtest/auto_backtest.log
python3 analyze_d1_performance.py >> backtest/auto_backtest.log 2>&1

# Clean up old logs (keep last 30 days)
find backtest/ -name "*.log" -mtime +30 -delete 2>/dev/null
find backtest/results/ -name "*.csv" -mtime +30 -delete 2>/dev/null
find backtest/results/ -name "*.txt" -mtime +30 -delete 2>/dev/null

echo "==== Analysis session complete: $(date) ====" >> backtest/auto_backtest.log
