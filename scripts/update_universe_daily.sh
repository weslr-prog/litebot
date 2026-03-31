#!/bin/bash
# Daily Universe Update Script
# Run this daily at 4:30 PM ET (after market close) to refresh the trading universe

cd /home/wes/Desktop/litebotx-usb-deployment

# Load environment
if [ -f .env ]; then
    source .env
fi

# Run universe generator
echo "========================================"
echo "Daily Universe Update - $(date)"
echo "========================================"

/home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python3 \
    /home/wes/Desktop/litebotx-usb-deployment/dynamic_universe_generator.py

echo ""
echo "========================================"
echo "Update Complete"
echo "========================================"
