================================================================================
LITEBOTX DAILY TRADING REPORT
================================================================================
Date: 2025-11-04
Generated: 2025-11-04 16:00:59

This report summarizes all trading activity, system health, and
compliance checks for the day.
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Overall Status: 🚨 CRITICAL: SYSTEM HEALTH ISSUES

Quick Stats:
  • Positions Opened: 0
  • Positions Closed: 0
  • PDT Compliance: PASS
  • System Health: CRITICAL (0/100)
  • Issues Detected: 4
  • Auto-Corrections: 0

PDT COMPLIANCE AUDIT
--------------------------------------------------------------------------------
Compliance Status: PASS
Positions Checked: 2
Violations Found: 0
Critical Violations: 0

✅ No PDT violations detected - excellent compliance!

SYSTEM HEALTH CHECK
--------------------------------------------------------------------------------
Health Status: CRITICAL
Health Score: 0/100
Issues Found: 4

⚠️ ISSUES DETECTED:

  • HIGH: No positions opened today
    Current: 0
    Expected: 5
    Auto-fixable: Yes

  • CRITICAL: Pre-filter returned only 0 candidates
    Current: 0
    Expected: 10
    Auto-fixable: Yes

  • HIGH: 12 errors detected
    Current: 12
    Expected: 10

  • CRITICAL: No trading signals generated
    Current: 0
    Expected: 10
    Auto-fixable: Yes

TRADING PERFORMANCE
--------------------------------------------------------------------------------

Signal Processing:
  • Signals Generated: 0
  • Signals Executed: 0
  • Signals Blocked: 3
  • Execution Rate: 0.0%

Pre-Filter Results:
  • Input Symbols: 0
  • Output Candidates: 0

Position Activity:
  • Positions Opened: 0
  • Positions Closed: 0

Error Tracking:
  • Errors: 12
  • Warnings: 12
  • API Errors: 0

RECOMMENDATIONS
--------------------------------------------------------------------------------

✅ No PDT violations detected - system is compliant
🔧 AUTO-CORRECTABLE ISSUES DETECTED:
  • No positions opened today
    - Check pre-filter results - may be rejecting all candidates
    - Verify market data availability
    - Review filter thresholds (may be too strict)
    - Check if emergency stop or kill switches are active
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

⚠️ MANUAL REVIEW REQUIRED:
  • 12 errors detected
    - API errors: 0
    - Check API connectivity
    - Verify API key permissions
    - Review error logs for patterns

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