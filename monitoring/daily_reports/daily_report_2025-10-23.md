================================================================================
LITEBOTX DAILY TRADING REPORT
================================================================================
Date: 2025-10-23
Generated: 2025-10-23 16:00:59

This report summarizes all trading activity, system health, and
compliance checks for the day.
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Overall Status: 🚨 CRITICAL: PDT VIOLATIONS DETECTED

Quick Stats:
  • Positions Opened: 5
  • Positions Closed: 0
  • PDT Compliance: FAIL
  • System Health: CRITICAL (45/100)
  • Issues Detected: 2
  • Auto-Corrections: 0

PDT COMPLIANCE AUDIT
--------------------------------------------------------------------------------
Compliance Status: FAIL
Positions Checked: 10
Violations Found: 1
Critical Violations: 1

⚠️ VIOLATIONS DETECTED:

  Symbol: MMM
  Type: multiple_entries
  Severity: CRITICAL
  Details: Multiple entries (2) for MMM on 2025-10-23. Entry times: 2025-10-23T13:45:00.766412+00:00, 2025-10-23T14:30:25.136986+00:00

SYSTEM HEALTH CHECK
--------------------------------------------------------------------------------
Health Status: CRITICAL
Health Score: 45/100
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
  • Signals Blocked: 0
  • Execution Rate: 0.0%

Pre-Filter Results:
  • Input Symbols: 0
  • Output Candidates: 0

Position Activity:
  • Positions Opened: 5
  • Positions Closed: 0

Error Tracking:
  • Errors: 1
  • Warnings: 3
  • API Errors: 0

RECOMMENDATIONS
--------------------------------------------------------------------------------

🔧 CRITICAL: 1 multiple entry violation(s). Verify entry blocker is checking _has_same_day_activity() before signal execution.
   Action: Enable single-entry-per-symbol-per-day enforcement
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