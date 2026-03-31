#!/bin/bash
# Safe Bot Launcher
# Use this instead of directly launching the bot.
# It checks readiness first, then launches only if safe.

set -e

cd /home/wes/Desktop/litebotx-usb-deployment

echo "========================================="
echo "🌙 SAFE BOT LAUNCHER"
echo "========================================="
echo ""
echo "Running evening readiness check..."
echo ""

# Activate virtual environment
source litebotx_env/bin/activate

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded .env file"
else
    echo "⚠️  No .env file found - API keys may not be available"
fi

# Run evening check (with notifications if desired)
python3 evening_launch_check.py --notify

CHECK_STATUS=$?

echo ""
echo "========================================="

if [ $CHECK_STATUS -eq 0 ]; then
    echo "✅ PRE-LAUNCH CHECK PASSED"
    echo "========================================="
    echo ""
    echo "Launching bot for tomorrow's trading..."
    echo ""
    
    # Launch the bot
    python3 litebotx_launcher.py
    
else
    echo "⛔ PRE-LAUNCH CHECK FAILED"
    echo "========================================="
    echo ""
    echo "CRITICAL ISSUES DETECTED - BOT NOT STARTED"
    echo ""
    echo "Review the output above for issues."
    echo "Fix problems and run again:"
    echo "  ./safe_launch.sh"
    echo ""
    echo "Or run check only:"
    echo "  python3 evening_launch_check.py"
    echo ""
    
    exit 1
fi
