#!/bin/bash
# Setup nightly backtesting automation
# Run this script to install the cron job

SCRIPT_DIR="/home/wes/Desktop/litebotx-usb-deployment"
CRON_TIME="0 2"  # 2:00 AM daily

echo "📅 Setting up nightly backtesting automation..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_nightly_backtest.sh"; then
    echo "⚠️  Cron job already exists. Removing old version..."
    crontab -l 2>/dev/null | grep -v "run_nightly_backtest.sh" | crontab -
fi

# Add new cron job
echo "🔧 Installing new cron job..."
(crontab -l 2>/dev/null; echo "$CRON_TIME * * * cd $SCRIPT_DIR && ./run_nightly_backtest.sh") | crontab -

echo "✅ Nightly backtesting scheduled for 2:00 AM daily"
echo "📝 To check: crontab -l"
echo "📝 To remove: crontab -e"

# Test the script works
echo "🧪 Testing backtest script..."
cd "$SCRIPT_DIR"
if ./run_nightly_backtest.sh; then
    echo "✅ Backtest script test successful"
else
    echo "❌ Backtest script test failed"
fi

echo "📊 Backtest automation setup complete!"