#!/bin/bash
# Automated Nightly Pre-Flight Check
# Run this via cron every night at 8 PM to ensure bot is ready for next morning
#
# Add to crontab with:
#   crontab -e
#   0 20 * * * /home/wes/Desktop/litebotx-usb-deployment/nightly_check.sh >> /home/wes/Desktop/litebotx-usb-deployment/logs/nightly_checks.log 2>&1

set -e

# Change to bot directory
cd /home/wes/Desktop/litebotx-usb-deployment

echo "========================================="
echo "NIGHTLY PRE-FLIGHT CHECK"
echo "Date: $(date)"
echo "========================================="
echo ""

# Activate virtual environment
source litebotx_env/bin/activate

# Run comprehensive pre-flight check
python3 pre_flight_check.py --verbose

CHECK_STATUS=$?

echo ""
echo "========================================="
if [ $CHECK_STATUS -eq 0 ]; then
    echo "✅ NIGHTLY CHECK PASSED - Bot ready for tomorrow"
    echo "========================================="
    
    # Optional: Send notification (uncomment and configure)
    # notify-send "Trading Bot" "Pre-flight check PASSED - ready for tomorrow"
    
    exit 0
else
    echo "❌ NIGHTLY CHECK FAILED - FIX BEFORE TRADING"
    echo "========================================="
    
    # Optional: Send urgent notification (uncomment and configure)
    # notify-send -u critical "Trading Bot" "Pre-flight check FAILED - DO NOT TRADE"
    
    # Optional: Send email alert
    # echo "Pre-flight check failed. Review logs at: $(pwd)/logs/nightly_checks.log" | \
    #   mail -s "URGENT: Trading Bot Pre-Flight FAILED" your-email@example.com
    
    exit 1
fi
