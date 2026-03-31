#!/bin/bash
# Enhanced Log Viewer - Quick debugging and analysis tool
# Usage: ./view_logs.sh [option]

cd /home/wes/Desktop/litebotx-usb-deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

show_menu() {
    echo ""
    echo "=========================================="
    echo "📊 Enhanced Log Viewer"
    echo "=========================================="
    echo "1) Activity Timeline (human-readable)"
    echo "2) Debug Details (verbose)"
    echo "3) Daily Summary (JSON)"
    echo "4) Main Log (sprint1_alpaca.log)"
    echo "5) Errors Only"
    echo "6) Entries & Exits Only"
    echo "7) Position Status"
    echo "8) Performance Metrics"
    echo "9) Live Tail (follow logs)"
    echo "10) Search Logs"
    echo "0) Exit"
    echo "=========================================="
    echo -n "Select option [0-10]: "
}

view_activity() {
    echo ""
    echo "=========================================="
    echo "📋 Trading Activity Timeline"
    echo "=========================================="
    if [ -f "logs/trading_activity.log" ]; then
        echo ""
        tail -100 logs/trading_activity.log | while IFS= read -r line; do
            if [[ $line == *"[ENTRY]"* ]]; then
                echo -e "${GREEN}$line${NC}"
            elif [[ $line == *"[EXIT]"* ]]; then
                echo -e "${BLUE}$line${NC}"
            elif [[ $line == *"[ERROR]"* ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ $line == *"[WARNING]"* ]]; then
                echo -e "${YELLOW}$line${NC}"
            else
                echo "$line"
            fi
        done
    else
        echo "No activity log found yet"
    fi
}

view_debug() {
    echo ""
    echo "=========================================="
    echo "🔍 Debug Details (Last 50 lines)"
    echo "=========================================="
    if [ -f "logs/debug_detailed.log" ]; then
        echo ""
        tail -50 logs/debug_detailed.log
    else
        echo "No debug log found yet"
    fi
}

view_summary() {
    echo ""
    echo "=========================================="
    echo "📊 Daily Summary (Structured Data)"
    echo "=========================================="
    LATEST_SUMMARY=$(ls -t logs/daily_summary_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_SUMMARY" ]; then
        echo ""
        echo "File: $LATEST_SUMMARY"
        echo ""
        python3 << EOF
import json
with open('$LATEST_SUMMARY') as f:
    data = json.load(f)
    
print(f"Date: {data.get('date', 'N/A')}")
print(f"Start Time: {data.get('start_time', 'N/A')}")
print()

# Position counts
positions = data.get('positions', {})
print(f"Positions Entered: {len(positions.get('entered', []))}")
print(f"Positions Exited: {len(positions.get('exited', []))}")
print()

# Exits with P&L
if positions.get('exited'):
    print("Exit Details:")
    for exit in positions['exited']:
        symbol = exit['symbol']
        pnl = exit['pnl']
        pnl_pct = exit['pnl_pct']
        result = exit['result']
        print(f"  {symbol}: ${pnl:+.2f} ({pnl_pct:+.2f}%) - {result}")
    print()

# Errors
errors = data.get('errors', [])
if errors:
    print(f"Errors: {len(errors)}")
    for err in errors[-5:]:  # Last 5 errors
        print(f"  {err['context']}: {err['error_type']}")
    print()

# Events summary
events = data.get('events', [])
print(f"Total Events: {len(events)}")
print(f"Event Types: {', '.join(set(e['type'] for e in events))}")
EOF
    else
        echo "No summary log found yet"
    fi
}

view_main_log() {
    echo ""
    echo "=========================================="
    echo "📝 Main Log (Last 100 lines)"
    echo "=========================================="
    if [ -f "logs/sprint1_alpaca.log" ]; then
        echo ""
        tail -100 logs/sprint1_alpaca.log | grep -E --color=always "ERROR|WARNING|\[INFO\]|Entry|Exit|SELL|BUY|📈|📉|⚠️|❌|✅"
    else
        echo "No main log found yet"
    fi
}

view_errors() {
    echo ""
    echo "=========================================="
    echo "❌ Errors Only"
    echo "=========================================="
    echo ""
    
    # Check all log files for errors
    for logfile in logs/*.log; do
        if [ -f "$logfile" ]; then
            errors=$(grep -i "error\|exception\|failed" "$logfile" 2>/dev/null | tail -20)
            if [ -n "$errors" ]; then
                echo "From: $logfile"
                echo "$errors" | while IFS= read -r line; do
                    echo -e "${RED}$line${NC}"
                done
                echo ""
            fi
        fi
    done
}

view_trades() {
    echo ""
    echo "=========================================="
    echo "💼 Entries & Exits"
    echo "=========================================="
    echo ""
    
    echo -e "${GREEN}=== ENTRIES ===${NC}"
    grep -h "ENTRY\|Entry executed\|📈" logs/*.log 2>/dev/null | tail -20 | while IFS= read -r line; do
        echo -e "${GREEN}$line${NC}"
    done
    
    echo ""
    echo -e "${BLUE}=== EXITS ===${NC}"
    grep -h "EXIT\|Exit executed\|📉" logs/*.log 2>/dev/null | tail -20 | while IFS= read -r line; do
        echo -e "${BLUE}$line${NC}"
    done
}

view_positions() {
    echo ""
    echo "=========================================="
    echo "📊 Current Position Status"
    echo "=========================================="
    echo ""
    python3 << 'EOF'
import json
import datetime as dt

with open('positions.json') as f:
    positions = json.load(f)

active = [p for p in positions if p['status'] == 'entered']
exited = [p for p in positions if p['status'] == 'exited']

print(f"Total Positions: {len(positions)}")
print(f"Active: {len(active)}")
print(f"Exited: {len(exited)}")
print()

if active:
    print("Active Positions:")
    today = dt.date.today()
    total_value = 0
    for p in active:
        entry_date = dt.date.fromisoformat(p['entry_date'])
        exit_date = dt.date.fromisoformat(p['exit_date'])
        value = p['entry_price'] * p['position_size_shares']
        total_value += value
        days_held = (today - entry_date).days
        status = "⚠️ OVERDUE" if today > exit_date else "✅ OK"
        print(f"  {p['symbol']}: ${value:.2f} | Entry: {entry_date} | Exit: {exit_date} | Days: {days_held} | {status}")
    print(f"\nTotal Capital in Positions: ${total_value:.2f}")
EOF
}

view_performance() {
    echo ""
    echo "=========================================="
    echo "⚡ Performance Metrics"
    echo "=========================================="
    echo ""
    
    echo "Signal Generation Times:"
    grep "SIGNALS\|PREFILTER" logs/*.log 2>/dev/null | tail -10
    
    echo ""
    echo "Monitoring Cycles:"
    grep "MONITORING:" logs/debug_detailed.log 2>/dev/null | tail -10
}

live_tail() {
    echo ""
    echo "=========================================="
    echo "📡 Live Log Feed (Ctrl+C to stop)"
    echo "=========================================="
    echo ""
    
    # Find the most recent log file
    LATEST_LOG=$(ls -t logs/bot_*.log logs/sprint1_alpaca.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        LATEST_LOG="logs/sprint1_alpaca.log"
    fi
    
    echo "Following: $LATEST_LOG"
    echo ""
    
    tail -f "$LATEST_LOG" | while IFS= read -r line; do
        if [[ $line == *"ERROR"* ]] || [[ $line == *"❌"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]] || [[ $line == *"⚠️"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"ENTRY"* ]] || [[ $line == *"📈"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"EXIT"* ]] || [[ $line == *"📉"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ $line == *"✅"* ]]; then
            echo -e "${GREEN}$line${NC}"
        else
            echo "$line"
        fi
    done
}

search_logs() {
    echo ""
    echo -n "Enter search term: "
    read search_term
    
    echo ""
    echo "=========================================="
    echo "🔍 Search Results for: $search_term"
    echo "=========================================="
    echo ""
    
    grep -i "$search_term" logs/*.log 2>/dev/null | tail -50
}

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1) view_activity ;;
        2) view_debug ;;
        3) view_summary ;;
        4) view_main_log ;;
        5) view_errors ;;
        6) view_trades ;;
        7) view_positions ;;
        8) view_performance ;;
        9) live_tail ;;
        10) search_logs ;;
        0) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option" ;;
    esac
    
    echo ""
    echo -n "Press Enter to continue..."
    read
done
