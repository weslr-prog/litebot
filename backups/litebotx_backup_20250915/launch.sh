#!/bin/bash
# Main LiteBotX Launcher
# Quick access to all launch options

echo "🚀 LiteBotX Main Launcher"
echo "========================="
echo ""
echo "Available launch options:"
echo "1. Paper Trading System (Full System)"
echo "2. TAF Integrated System (Advanced)"
echo "3. Sprint 1 + Alpaca Paper Trading"
echo "4. Trading Dashboard Only"
echo "5. Quick System Health Check"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "🚀 Launching Paper Trading System..."
        ./scripts/launch_paper_testing.sh
        ;;
    2)
        echo "🚀 Launching TAF Integrated System..."
        ./scripts/launch_taf_integrated_system.sh
        ;;
    3)
        echo "� Launching Sprint 1 + Alpaca Integration..."
        python test/sprint1_alpaca_integration.py
        ;;
    4)
        echo "�📊 Launching Trading Dashboard..."
        python gui/launch_dashboard.py
        ;;
    5)
        echo "🔍 Running Health Check..."
        source litebotx_env/bin/activate && python quick_health_check.py
        ;;
    *)
        echo "Invalid option. Please select 1-5."
        exit 1
        ;;
esac

echo ""
echo "✅ Launch complete!"
