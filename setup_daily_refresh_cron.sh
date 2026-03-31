#!/bin/bash
# Setup Daily Watchlist Refresh Cron Job
# Runs every weekday at 4:30 PM ET (after market close)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)
LOG_DIR="$SCRIPT_DIR/logs"

echo "========================================"
echo "Daily Watchlist Refresh - Cron Setup"
echo "========================================"
echo ""
echo "Script Directory: $SCRIPT_DIR"
echo "Python Path: $PYTHON_PATH"
echo "Log Directory: $LOG_DIR"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Load environment variables from .env file
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
    echo "✅ Loaded .env file"
else
    echo "⚠️  No .env file found"
fi

# Create the cron job command
CRON_COMMAND="30 16 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $SCRIPT_DIR/daily_watchlist_refresh.py >> $LOG_DIR/cron_watchlist.log 2>&1"

echo ""
echo "Cron job to add:"
echo "$CRON_COMMAND"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "daily_watchlist_refresh.py"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    read -p "Do you want to replace it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 0
    fi
    # Remove existing job
    crontab -l 2>/dev/null | grep -v "daily_watchlist_refresh.py" | crontab -
    echo "✅ Removed old cron job"
fi

# Add the cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

echo ""
echo "✅ Cron job added successfully!"
echo ""
echo "Schedule: Every weekday (Mon-Fri) at 4:30 PM ET"
echo "Action: Refresh watchlist with top 15 momentum stocks"
echo ""
echo "To view your cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove this cron job:"
echo "  crontab -l | grep -v 'daily_watchlist_refresh.py' | crontab -"
echo ""
echo "Log file: $LOG_DIR/cron_watchlist.log"
echo "========================================"
