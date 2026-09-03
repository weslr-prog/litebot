#!/bin/bash
# Paper Trading Launch Script for Sprint 1 Validation
# 1-Week Real Market Data Testing

echo "🚀 LiteBotX Sprint 1 Paper Trading Launch"
echo "Weekly High Yield ROI - Real Market Data Validation"
echo "======================================================="

# Check if virtual environment exists
if [ ! -d "litebotx_env" ]; then
    echo "❌ Virtual environment not found. Run setup first."
    exit 1
fi

# Activate virtual environment
source litebotx_env/bin/activate

echo "✅ Virtual environment activated"
echo ""

# Check system readiness
echo "📊 Checking system readiness..."
python -c "
import yfinance as yf
import pandas as pd
import numpy as np
import sklearn
print('✅ All required packages available')
"

if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip install yfinance pandas numpy scikit-learn xgboost
fi

echo ""
echo "🎯 Paper Trading Options:"
echo "1. Quick validation test (5 minutes)"
echo "2. Extended paper trading session (signals only)"
echo "3. Sprint 1 + Alpaca paper trading (with real trades!)"
echo "4. ML training validation"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        echo "🧪 Running quick validation test..."
        python sprint1_minimal_test.py
        ;;
    2)
        echo "📈 Starting extended paper trading session (signals only)..."
        echo "⚠️  This will run continuously. Press Ctrl+C to stop."
        echo "📊 Launching dashboard..."
        echo ""
        echo "🚀 Starting Sprint 1 Paper Trading..."
        python -c "
from test.sprint1_real_data_integration import ShortCycleDataIntegration
from core.config import Sprint1Config
import tkinter as tk
import threading

# Try to launch simple dashboard
try:
    from gui.sprint1_integrated_dashboard import create_integrated_dashboard
    
    config = Sprint1Config()
    integration = ShortCycleDataIntegration()
    
    # Create basic dashboard
    dashboard = create_integrated_dashboard(integration, config)
    
    # Start integration in background thread
    def run_integration():
        integration.start_paper_trading(config.test_symbols)
    
    trading_thread = threading.Thread(target=run_integration, daemon=True)
    trading_thread.start()
    
    print('🚀 Paper Trading + Dashboard Started - Close dashboard window to stop')
    dashboard.run()
    
except ImportError:
    # Fallback to no GUI
    config = Sprint1Config()
    integration = ShortCycleDataIntegration()
    print('🚀 Paper Trading Started (No GUI) - Press Ctrl+C to stop')
    integration.start_paper_trading(config.test_symbols)
"
        ;;
    3)
        echo "🚀 Starting Sprint 1 + Alpaca paper trading (with real trades!)..."
        echo "⚠️  This will execute real paper trades on Alpaca using ROI-optimized schedule."
        echo "� Trading only during market hours: 9:30 AM - 4:00 PM ET"
        echo "🎯 Schedule: 8:00, 9:30, 10:00, 15:00, 15:30, 15:45(Fri), 16:15 ET"
        echo "Press Ctrl+C to stop."
        echo ""
        echo "🎯 Connecting to Alpaca..."
        python -c "
from test.sprint1_alpaca_integration import Sprint1AlpacaIntegration
from core.config import Sprint1Config
import schedule
import time

config = Sprint1Config()
integration = Sprint1AlpacaIntegration(launch_gui=False)

# Initialize system
if not integration.initialize_system():
    print('❌ Failed to initialize system')
    exit(1)

# Setup ROI-optimized schedule
integration.setup_schedule()

print('✅ ROI-optimized schedule configured')
print('📅 Trading Schedule:')
print('   08:00 ET - Pre-Market Validation')
print('   09:30 ET - Primary Entry Window')
print('   10:00 ET - Mid-Execution Follow-up')
print('   15:00 ET - Market Close Management')
print('   15:30 ET - Final Management Check')
print('   15:45 ET - Friday Weekend Risk (Fridays only)')
print('   16:15 ET - Strategic Scan (Next Day Prep)')
print('')
print('🚀 Scheduled paper trading started - Press Ctrl+C to stop')
print('⏰ System will only trade during market hours')

try:
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for scheduled jobs
except KeyboardInterrupt:
    print('\\n🛑 Paper trading stopped by user')
"
        ;;
    4)
        echo "🤖 Running ML training validation..."
        python sprint1_ml_training.py
        ;;
    *)
        echo "Invalid option. Running quick test by default..."
        python sprint1_minimal_test.py
        ;;
esac

echo ""
echo "📊 Paper Trading Session Complete"
echo "📋 Review logs for performance analysis"
echo "🎯 Target: 1 week validation before Sprint 2"
