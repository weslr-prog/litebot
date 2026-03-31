#!/bin/bash

# Launch Sprint 1 System with TAF Integration
# Complete automated trading system with FINRA TAF fee optimization

echo "=========================================================="
echo "LAUNCHING SPRINT 1 WITH TAF INTEGRATION"
echo "=========================================================="
echo "Date: $(date)"
echo "FINRA TAF Fee Structure: Effective October 4, 2025"
echo "Fee Rate: \$0.000166 per share (capped at \$8.30 per trade)"
echo ""

# Check if we're in the right directory
if [ ! -f "test/sprint1_alpaca_integration.py" ]; then
    echo "❌ Error: sprint1_alpaca_integration.py not found"
    echo "Please run this script from the litebotx-usb-deployment directory"
    exit 1
fi

# Check for required files
echo "🔍 Verifying TAF integration files..."
if [ ! -f "finra_taf_calculator.py" ]; then
    echo "❌ Missing: finra_taf_calculator.py"
    exit 1
fi

if [ ! -f "gui/sprint1_integrated_dashboard.py" ]; then
    echo "❌ Missing: sprint1_integrated_dashboard.py"
    exit 1
fi

echo "✅ All TAF integration files present"
echo ""

# Test TAF system
echo "🧪 Testing TAF integration..."
source litebotx_env/bin/activate && python test_taf_final.py

if [ $? -ne 0 ]; then
    echo "❌ TAF integration test failed"
    exit 1
fi

echo ""
echo "✅ TAF integration test passed"
echo ""

# Launch options
echo "=========================================================="
echo "LAUNCH OPTIONS"
echo "=========================================================="
echo "1. Dashboard Only (Safe - No Trading)"
echo "2. Paper Trading Mode (Alpaca Paper Account)"
echo "3. TAF Integration Demo (Show Fee Optimization)"
echo "4. Full System Health Check"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🖥️ Launching Dashboard Only Mode..."
        echo "This will show real-time market data without executing trades"
        echo ""
        source litebotx_env/bin/activate && python sprint1_integrated_dashboard.py
        ;;
    2)
        echo ""
        echo "📈 Launching Paper Trading Mode..."
        echo "This will execute trades on Alpaca paper account with TAF optimization"
        echo ""
        echo "⚠️ IMPORTANT: This uses your Alpaca paper trading account"
        echo "Current configuration:"
        echo "- Portfolio Size: \$100,000"
        echo "- Risk Per Trade: 1.5%"
        echo "- Max Positions: 15"
        echo "- TAF Fee Optimization: ENABLED"
        echo ""
        read -p "Proceed with paper trading? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            source litebotx_env/bin/activate && python sprint1_alpaca_integration.py
        else
            echo "Paper trading cancelled"
        fi
        ;;
    3)
        echo ""
        echo "🎯 TAF Integration Demo..."
        echo "Demonstrating FINRA TAF fee optimization strategies"
        echo ""
        python -c "
from finra_taf_calculator import FINRATAFCalculator
from datetime import date

print('FINRA TAF Fee Optimization Demo')
print('=' * 50)

calc = FINRATAFCalculator()
calc.effective_date = date(2025, 9, 1)  # Enable for demo

# Demo scenarios
scenarios = [
    {'name': 'Small Position', 'value': 10000, 'price': 100},
    {'name': 'Medium Position', 'value': 500000, 'price': 50},
    {'name': 'Large Position', 'value': 5000000, 'price': 100},
    {'name': 'Threshold Test', 'value': 4999900, 'price': 100}
]

for scenario in scenarios:
    print(f'\n{scenario[\"name\"]}:')
    value = scenario['value']
    price = scenario['price']
    basic_shares = int(value / price)
    basic_fee = calc.calculate_taf_fee(basic_shares)
    
    optimization = calc.optimize_position_size(value, price)
    opt_shares = optimization['recommended']['shares']
    opt_fee = calc.calculate_taf_fee(opt_shares)
    
    print(f'  Target: \${value:,} at \${price}/share')
    print(f'  Basic: {basic_shares:,} shares → \${basic_fee:.2f} TAF fee')
    print(f'  Optimized: {opt_shares:,} shares → \${opt_fee:.2f} TAF fee')
    
    if opt_fee < basic_fee:
        print(f'  💰 Savings: \${basic_fee - opt_fee:.2f}')
    elif opt_shares > basic_shares:
        extra_cost = (opt_shares - basic_shares) * price
        print(f'  📈 Extra investment: \${extra_cost:,} for fee efficiency')
    else:
        print(f'  ✅ Already optimal')

print(f'\n🎯 TAF optimization ready for October 4, 2025!')
"
        ;;
    4)
        echo ""
        echo "🏥 Running System Health Check..."
        echo ""
        source litebotx_env/bin/activate && python quick_health_check.py
        echo ""
        echo "Running TAF-specific tests..."
        source litebotx_env/bin/activate && python test_taf_final.py
        ;;
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=========================================================="
echo "SESSION COMPLETE"
echo "=========================================================="
echo "TAF Integration Status: ✅ READY"
echo "System ready for FINRA TAF fee optimization effective October 4, 2025"
echo ""
