#!/bin/bash
# Quick verification that all PreFilter fixes are applied correctly

echo "======================================================================"
echo "PreFilter Configuration Verification"
echo "======================================================================"
echo ""

# Run all relevant tests
echo "Running PreFilter configuration tests..."
echo ""

# Test 1: Watchlist generation
echo "TEST 1: Watchlist Generation & Price Range Filtering"
echo "----------------------------------------------------------------------"
/home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python test_watchlist_generation.py
test1_result=$?

echo ""
echo "TEST 2: PreFilter Small Portfolio Configuration"
echo "----------------------------------------------------------------------"
/home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python test_prefilter_config.py
test2_result=$?

echo ""
echo "TEST 3: PDT Protection (exit_timestamp persistence)"
echo "----------------------------------------------------------------------"
/home/wes/Desktop/litebotx-usb-deployment/litebotx_env/bin/python test_pdt_protection.py
test3_result=$?

echo ""
echo "======================================================================"
echo "VERIFICATION SUMMARY"
echo "======================================================================"

if [ $test1_result -eq 0 ]; then
    echo "✅ Watchlist Generation: PASSED"
else
    echo "❌ Watchlist Generation: FAILED"
fi

if [ $test2_result -eq 0 ]; then
    echo "✅ PreFilter Config: PASSED"
else
    echo "❌ PreFilter Config: FAILED"
fi

if [ $test3_result -eq 0 ]; then
    echo "✅ PDT Protection: PASSED"
else
    echo "❌ PDT Protection: FAILED"
fi

echo ""

# Check if all tests passed
if [ $test1_result -eq 0 ] && [ $test2_result -eq 0 ] && [ $test3_result -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - Bot ready for small portfolio trading!"
    echo ""
    echo "Configuration Summary:"
    echo "  • Price range: \$10-30 (mid-cap volatiles)"
    echo "  • Expected stocks: PLTR, RIVN, SNAP, HOOD"
    echo "  • Rejected stocks: AMD, SHOP, XOM, AAPL (> \$30)"
    echo "  • Position sizing: 10-20 shares (\$150-200 per position)"
    echo "  • PDT protection: exit_timestamp persists across restarts"
    echo ""
    echo "Next steps:"
    echo "  1. Restart bot: pkill -f start_small_portfolio_trader.py && ./start_small_portfolio_trader.py"
    echo "  2. Check logs: grep 'Final trading universe' logs/short_cycle_trader.log | tail -1"
    echo "  3. Verify universe has \$10-30 stocks (not \$100+ stocks)"
    exit 0
else
    echo "❌ SOME TESTS FAILED - Review output above"
    exit 1
fi
