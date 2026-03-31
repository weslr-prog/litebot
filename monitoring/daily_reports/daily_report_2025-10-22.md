================================================================================
LITEBOTX DAILY TRADING REPORT
================================================================================
Date: 2025-10-22
Generated: 2025-10-22 16:01:00

This report summarizes all trading activity, system health, and
compliance checks for the day.
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Overall Status: 🚨 CRITICAL: SYSTEM HEALTH ISSUES

Quick Stats:
  • Positions Opened: 5
  • Positions Closed: 0
  • PDT Compliance: PASS
  • System Health: CRITICAL (50/100)
  • Issues Detected: 2
  • Auto-Corrections: 0

PDT COMPLIANCE AUDIT
--------------------------------------------------------------------------------
Compliance Status: PASS
Positions Checked: 13
Violations Found: 0
Critical Violations: 0

✅ No PDT violations detected - excellent compliance!

SYSTEM HEALTH CHECK
--------------------------------------------------------------------------------
Health Status: CRITICAL
Health Score: 50/100
Issues Found: 2

⚠️ ISSUES DETECTED:

  • CRITICAL: Pre-filter returned only 0 candidates
    Current: 0
    Expected: 10
    Auto-fixable: Yes

  • CRITICAL: No trading signals generated
    Current: 0
    Expected: 10
    Auto-fixable: Yes

TRADING PERFORMANCE
--------------------------------------------------------------------------------

Signal Processing:
  • Signals Generated: 0
  • Signals Executed: 0
  • Signals Blocked: 1
  • Execution Rate: 0.0%

Pre-Filter Results:
  • Input Symbols: 0
  • Output Candidates: 0

Position Activity:
  • Positions Opened: 5
  • Positions Closed: 0

Error Tracking:
  • Errors: 0
  • Warnings: 39
  • API Errors: 0

RECOMMENDATIONS
--------------------------------------------------------------------------------

✅ No PDT violations detected - system is compliant
🔧 AUTO-CORRECTABLE ISSUES DETECTED:
  • Pre-filter returned only 0 candidates
    - Check data completeness filter (may need to reduce min_rows)
    - Review liquidity filter thresholds
    - Verify market data is available (free tier limitations)
    - Consider relaxing momentum/volatility filters
  • No trading signals generated
    - Pre-filter returned 0 candidates
    - Check signal generation logic
    - Verify strategy is enabled
    - Check market hours and trading schedule

💡 QUICK FIX FOR PRE-FILTER:
  Run: Edit pre_filter.py, reduce min_rows from 30 to 20

================================================================================
END OF REPORT

For detailed logs, see:
  • PDT Audit: monitoring/reports/pdt/
  • Health Reports: monitoring/reports/health/
  • Trading Logs: logs/short_cycle_trader.log

Questions? Check SELF_MONITORING_SYSTEM_PROPOSAL.md for details.
================================================================================