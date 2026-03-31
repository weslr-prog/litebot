#!/bin/bash
# Quick Commands for Self-Monitoring System
# Run these when you get home from work

echo "🤖 LITEBOTX SELF-MONITORING - QUICK COMMANDS"
echo "=============================================="
echo ""

# Function to show today's report
show_report() {
    TODAY=$(date +%Y-%m-%d)
    REPORT="monitoring/daily_reports/daily_report_${TODAY}.txt"
    
    if [ -f "$REPORT" ]; then
        echo "📄 TODAY'S REPORT ($TODAY):"
        echo "=============================================="
        cat "$REPORT"
    else
        echo "❌ No report found for today. Running monitoring now..."
        python monitoring/monitoring_system.py
        if [ -f "$REPORT" ]; then
            cat "$REPORT"
        fi
    fi
}

# Function to check status
check_status() {
    echo "📊 CHECKING SYSTEM STATUS..."
    echo ""
    
    # Check if emergency PDT mode is active
    if [ -f "monitoring/EMERGENCY_PDT_MODE.flag" ]; then
        echo "🚨 WARNING: EMERGENCY PDT MODE IS ACTIVE"
        echo "   Review: cat monitoring/EMERGENCY_PDT_MODE.flag"
        echo ""
    fi
    
    # Check recent reports
    echo "Recent Reports:"
    ls -lt monitoring/daily_reports/ | head -5
    echo ""
    
    # Check recent corrections
    if [ -f "monitoring/correction_history.json" ]; then
        echo "Recent Auto-Corrections:"
        python -c "import json; h=json.load(open('monitoring/correction_history.json')); print(f'  Total: {len(h)}'); [print(f'  • {c[\"parameter\"]}: {c[\"old_value\"]} → {c[\"new_value\"]} ({c[\"timestamp\"][:10]})') for c in h[-5:]]" 2>/dev/null || echo "  (Run monitoring first)"
    fi
}

# Function to run monitoring manually
run_monitoring() {
    echo "🔄 RUNNING MONITORING SYSTEM..."
    python monitoring/monitoring_system.py
}

# Main menu
if [ "$1" == "report" ]; then
    show_report
elif [ "$1" == "status" ]; then
    check_status
elif [ "$1" == "run" ]; then
    run_monitoring
else
    echo "Usage:"
    echo "  ./monitor.sh report   - Show today's report"
    echo "  ./monitor.sh status   - Check system status"
    echo "  ./monitor.sh run      - Run monitoring now"
    echo ""
    echo "Quick shortcuts:"
    echo "  cat monitoring/daily_reports/daily_report_\$(date +%Y-%m-%d).txt"
    echo "  python monitoring/monitoring_system.py"
    echo ""
    echo "Tip: Just run './monitor.sh report' when you get home!"
fi
