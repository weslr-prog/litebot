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
echo "5. Sprint 2 ShortCycleTrader (PreFilter, diagnostics)"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "🧪 Running quick validation test..."
        python test/sprint1_minimal_test.py
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
        echo "⚠️  This will execute real paper trades on Alpaca. Press Ctrl+C to stop."
        echo "📊 Launching integrated dashboard..."
        echo ""
        echo "🎯 Connecting to Alpaca..."
        python -c "
import logging
import os

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging with file handler (same as main() function)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sprint1_alpaca.log'),
        logging.StreamHandler()
    ]
)

from test.sprint1_alpaca_integration import Sprint1AlpacaIntegration
from core.config import Sprint1Config
config = Sprint1Config()
integration = Sprint1AlpacaIntegration(launch_gui=True)
print('🚀 Alpaca Paper Trading + Dashboard Started - Press Ctrl+C to stop')
integration.start_paper_trading_with_dashboard(config.test_symbols)
"
        ;;
    4)
        echo "🤖 Running ML training validation..."
        python test/sprint1_ml_training.py
        ;;
    5)
        echo "🚀 Starting Sprint 2 ShortCycleTrader (PreFilter, diagnostics)..."
        echo "⚠️  This will use the new pipeline with PreFilter-driven universe and detailed logs."
        python -c "from traders.short_cycle_trader import ShortCycleTrader; ShortCycleTrader().run_daily_cycle()"
        ;;
    *)
        echo "Invalid option. Running quick test by default..."
        python test/sprint1_minimal_test.py
        ;;
esac

echo ""
echo "📊 Paper Trading Session Complete"
echo "📋 Review logs for performance analysis"
echo "🎯 Target: 1 week validation before Sprint 2"
