#!/bin/bash
# LiteBotX - 1 Hour Optimization Runner
# Runs parameter optimization for 1 hour, saves results, can be resumed

cd /home/wes/Desktop/litebotx-usb-deployment

echo "=========================================="
echo "LiteBotX Parameter Optimization Engine"
echo "=========================================="
echo ""
echo "This will run automated backtests for 1 hour"
echo "Testing momentum, mean reversion, candlestick, and hybrid strategies"
echo ""
echo "Results will be saved to: optimization_results/"
echo "Progress is auto-saved every 10 tests"
echo ""
read -p "Press ENTER to start optimization..."

# Activate virtual environment if exists
if [ -d "litebotx_env" ]; then
    source litebotx_env/bin/activate
fi

# Run optimization for 1 hour
python3 optimize_parameters.py --duration 60

echo ""
echo "=========================================="
echo "Optimization Complete!"
echo "=========================================="
echo ""
echo "Results saved in: optimization_results/"
echo ""
echo "📊 View all results:"
echo "   cat optimization_results/all_results.csv"
echo ""
echo "🏆 View best parameters:"
echo "   cat optimization_results/best_parameters.json"
echo ""
echo "🔝 View top performers by metric:"
echo "   cat optimization_results/top_10_weekly_return.csv"
echo "   cat optimization_results/top_10_sharpe_ratio.csv"
echo "   cat optimization_results/top_10_win_rate.csv"
echo ""
echo "🔄 To continue optimization for another hour:"
echo "   python3 optimize_parameters.py --duration 60 --resume"
echo ""
