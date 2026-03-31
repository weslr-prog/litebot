#!/bin/bash
# Quick validation script for October 23 trading session
# Run this after market close to verify all fixes worked

echo "=========================================="
echo "🔍 Oct 23 Fix Validation Report"
echo "=========================================="
echo ""

LOG_FILE="trading_bot.log"

# Check if log exists
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ ERROR: trading_bot.log not found!"
    exit 1
fi

echo "📊 VALIDATION RESULTS:"
echo ""

# Fix #1: PDT Validation
echo "✅ FIX #1: PDT Validation"
PDT_FILTERS=$(grep -c "D+1 Rule: Filtered" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$PDT_FILTERS" -gt 0 ]; then
    echo "   ✅ PDT prevention active ($PDT_FILTERS instances)"
    grep "D+1 Rule: Filtered" "$LOG_FILE" | tail -3
else
    echo "   ⚠️  No PDT filters found (check if any symbols needed filtering)"
fi
echo ""

# Fix #2: Exit Aggregation
echo "✅ FIX #2: Exit Aggregation"
MMM_EXIT=$(grep "Exiting MMM:" "$LOG_FILE" 2>/dev/null)
if [ -n "$MMM_EXIT" ]; then
    echo "   ✅ MMM exit logged:"
    echo "   $MMM_EXIT"
    if echo "$MMM_EXIT" | grep -q "36 shares"; then
        echo "   ✅ CORRECT: Exited exactly 36 shares"
    else
        echo "   ⚠️  WARNING: Check share count"
    fi
else
    echo "   ⚠️  MMM exit not found in logs"
fi
echo ""

# Fix #3: Trailing Stops
echo "✅ FIX #3: Trailing Stops"
TRAILING_STOPS=$(grep -c "Trailing stop" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$TRAILING_STOPS" -gt 0 ]; then
    echo "   ✅ Trailing stops activated ($TRAILING_STOPS times)"
    grep "Trailing stop" "$LOG_FILE" | tail -5
else
    echo "   ℹ️  No trailing stops activated (stocks may not have reached 2% profit)"
fi
echo ""

# Fix #4: Breakout Filter
echo "✅ FIX #4: Breakout Filter"
BREAKOUT_LOGS=$(grep "Breakout Filter:" "$LOG_FILE" 2>/dev/null)
if [ -n "$BREAKOUT_LOGS" ]; then
    echo "   ✅ Breakout filter running:"
    echo "$BREAKOUT_LOGS" | tail -3
else
    echo "   ⚠️  Breakout filter logs not found"
fi
echo ""

# Fix #5: Relative Strength
echo "✅ FIX #5: Relative Strength"
RS_LOGS=$(grep "RS Filter:" "$LOG_FILE" 2>/dev/null)
if [ -n "$RS_LOGS" ]; then
    echo "   ✅ Relative strength filtering active:"
    echo "$RS_LOGS" | tail -2
else
    echo "   ⚠️  RS filter logs not found"
fi
echo ""

# Fix #6: Sector Rotation
echo "✅ FIX #6: Sector Rotation"
SECTOR_LOGS=$(grep "Leading sectors:" "$LOG_FILE" 2>/dev/null)
if [ -n "$SECTOR_LOGS" ]; then
    echo "   ✅ Sector rotation active:"
    echo "$SECTOR_LOGS" | tail -2
else
    echo "   ⚠️  Sector rotation logs not found"
fi
echo ""

# Fix #7: Universe Size
echo "✅ FIX #7: Universe Size (8-15 stocks)"
ENTRY_COUNT=$(grep "Entering position:" "$LOG_FILE" 2>/dev/null | grep "Oct 23" | wc -l)
echo "   📊 New entries today: $ENTRY_COUNT"
if [ "$ENTRY_COUNT" -ge 8 ] && [ "$ENTRY_COUNT" -le 15 ]; then
    echo "   ✅ PERFECT: Within target range (8-15)"
elif [ "$ENTRY_COUNT" -gt 0 ]; then
    echo "   ⚠️  Outside target range (expected 8-15)"
else
    echo "   ⚠️  No entries found for Oct 23"
fi
echo ""

# Summary
echo "=========================================="
echo "📈 PERFORMANCE SUMMARY"
echo "=========================================="
echo ""

# Get today's P&L
PNL_LINE=$(grep "Daily P&L" "$LOG_FILE" 2>/dev/null | tail -1)
if [ -n "$PNL_LINE" ]; then
    echo "$PNL_LINE"
else
    echo "⚠️  Daily P&L not yet available"
fi

# Get win rate
WINS=$(grep "exit.*profit" "$LOG_FILE" 2>/dev/null | grep "Oct 23" | wc -l)
LOSSES=$(grep "exit.*loss" "$LOG_FILE" 2>/dev/null | grep "Oct 23" | wc -l)
TOTAL=$((WINS + LOSSES))

if [ "$TOTAL" -gt 0 ]; then
    WIN_RATE=$((WINS * 100 / TOTAL))
    echo "📊 Win Rate: $WIN_RATE% ($WINS wins, $LOSSES losses)"
else
    echo "ℹ️  No exits yet (positions may still be open)"
fi

echo ""
echo "=========================================="
echo "✅ VALIDATION COMPLETE"
echo "=========================================="
echo ""
echo "To see full logs:"
echo "  tail -200 trading_bot.log"
echo ""
echo "To check specific symbols:"
echo "  grep 'SYMBOL_NAME' trading_bot.log"
echo ""
