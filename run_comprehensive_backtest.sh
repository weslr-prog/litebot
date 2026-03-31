#!/bin/bash

# Quick launcher for comprehensive 3-phase backtest
# Tests top 3 strategies across 2011-2024 (14 years)

echo "=========================================="
echo "COMPREHENSIVE 3-PHASE BACKTEST"
echo "=========================================="
echo ""
echo "Phases:"
echo "  • In-Sample: 2011-2016 (parameter validation)"
echo "  • Validation: 2017-2019 (overfitting check)"
echo "  • Out-of-Sample: 2020-2024 (real-world test)"
echo ""
echo "Strategies:"
echo "  1. Mean Reversion RSI #2852 (RSI 7, exit @50)"
echo "  2. Mean Reversion RSI #3831 (RSI 21, exit @80)"
echo "  3. Hybrid #4872 (momentum + mean reversion)"
echo ""
echo "Runtime: ~15-30 minutes"
echo "=========================================="
echo ""

# Check if yfinance is installed
python3 -c "import yfinance" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  yfinance not found. Installing..."
    pip install yfinance
    echo ""
fi

# Check if pandas is installed
python3 -c "import pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  pandas not found. Installing..."
    pip install pandas
    echo ""
fi

# Create results directory
mkdir -p backtest/results/comprehensive
mkdir -p backtest/cache

# Run backtest
echo "🚀 Starting backtest..."
echo ""
python3 backtest/comprehensive_strategy_backtest.py

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Backtest complete!"
    echo ""
    echo "📊 Results saved to: backtest/results/comprehensive/"
    echo ""
    echo "📄 Files:"
    ls -lh backtest/results/comprehensive/ | tail -n +2 | awk '{printf "   %s (%s)\n", $9, $5}'
    echo ""
    echo "💡 Next steps:"
    echo "   1. Review summary report (*_summary_*.txt)"
    echo "   2. Check trade logs (*_trades_*.csv)"
    echo "   3. Identify best performing strategy"
    echo "   4. If Out-of-Sample >= 5% weekly, proceed to paper trading"
    echo ""
else
    echo ""
    echo "❌ Backtest failed. Check errors above."
    echo ""
    echo "Common issues:"
    echo "   • Missing dependencies: pip install yfinance pandas numpy"
    echo "   • Network issues: Check internet connection"
    echo "   • Data errors: Some symbols may not have 2011-2016 data"
    echo ""
fi
