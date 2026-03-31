#!/bin/bash

# LiteBotX Paper Trading Launch Script
# Activate environment and launch various testing modes

set -e  # Exit on any error

echo "🤖 LiteBotX Paper Trading Launcher"
echo "=================================="

# Activate virtual environment
if [ -d "litebotx_env" ]; then
    echo "🔧 Activating virtual environment..."
    source litebotx_env/bin/activate
    echo "✅ Environment activated"
else
    echo "❌ Virtual environment not found. Please run ubuntu_setup.sh first"
    exit 1
fi

# Check system readiness
echo ""
echo "📊 Checking system readiness..."
python3 -c "
import yfinance as yf
import pandas as pd
import numpy as np
from traders.short_cycle_trader import ShortCycleTrader
print('✅ All required packages available')
"

if [ $? -ne 0 ]; then
    echo "❌ System not ready. Please check dependencies."
    exit 1
fi

echo ""
echo "🎯 Paper Trading Options:"
echo "1. Quick validation test (5 minutes)"
echo "2. Live market session (30 minutes)"
echo "3. Continuous live trading (normal mode)"
echo "4. Exit"
echo ""
read -p "Choose option [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "🧪 Starting Quick Validation Test..."
        echo "⏱️  Duration: ~5 minutes"
        echo "🎯 Tests all core systems without live trading"
        echo ""
        
        python3 sprint1_minimal_test.py
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Quick test completed successfully!"
            echo "💡 Ready for live paper trading during market hours"
        else
            echo ""
            echo "❌ Quick test failed"
            exit 1
        fi
        ;;
        
    2)
        echo ""
        echo "🎪 Starting Live Market Session..."
        echo "⏱️  Duration: 30 minutes"
        echo "🔴 REAL paper trades will be made with Alpaca!"
        echo "🎯 You'll see the bot's unique dynamic behaviors in action"
        echo ""
        
        python3 live_market_session.py
        ;;
        
    3)
        echo ""
        echo "🚀 Starting Continuous Live Trading Mode..."
        echo "⏱️  Duration: Until you stop it (Ctrl+C)"
        echo "🔴 REAL paper trades during market hours!"
        echo "🎯 Bot will run its full autonomous trading cycle"
        echo "📅 Respects market hours: 9:30 AM - 4:00 PM ET"
        echo "� Sleeps when market is closed"
        echo ""
        
        python3 continuous_live_trading.py
        ;;
        
    4)
        echo "�👋 Goodbye!"
        exit 0
        ;;
        
    *)
        echo "❌ Invalid option. Please choose 1, 2, 3, or 4."
        exit 1
        ;;
esac

echo ""
echo "🎪 Session complete! Bot showed its dynamic behaviors:"
echo "   📈 Portfolio auto-scaling from live Alpaca data"
echo "   🧠 AI-driven signal generation and filtering"
echo "   🛡️ Real-time risk management"
echo "   🎯 Confidence-based trade selection"
echo ""
echo "🚀 To see full live trading, run during market hours (9:30 AM - 4:00 PM ET)"
