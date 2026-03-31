#!/usr/bin/env python3
"""
Daily Report Generator
======================
Creates human-readable daily trading summary reports that you can
review when you get home from work.

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class DailyReportGenerator:
    """
    Generates comprehensive human-readable daily reports combining
    PDT audit, health check, and trading performance.
    """
    
    def __init__(self, report_dir: str = "monitoring/daily_reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
    def generate_daily_report(self, 
                            pdt_report: Dict,
                            health_report: Dict,
                            corrections: List[Dict],
                            report_date: Optional[str] = None) -> str:
        """
        Generate comprehensive daily report.
        
        Args:
            pdt_report: PDT audit results
            health_report: Health check results
            corrections: List of auto-corrections applied
            report_date: Date for report (defaults to today)
            
        Returns:
            Path to generated report file
        """
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")
        
        self.logger.info(f"📝 Generating daily report for {report_date}")
        
        # Build report sections
        report_lines = []
        
        # Header
        report_lines.extend(self._build_header(report_date))
        
        # Executive Summary
        report_lines.extend(self._build_executive_summary(
            pdt_report, health_report, corrections
        ))
        
        # PDT Compliance Section
        report_lines.extend(self._build_pdt_section(pdt_report))
        
        # System Health Section
        report_lines.extend(self._build_health_section(health_report))
        
        # Trading Performance Section
        report_lines.extend(self._build_performance_section(health_report['metrics']))
        
        # Auto-Corrections Section
        if corrections:
            report_lines.extend(self._build_corrections_section(corrections))
        
        # Recommendations Section
        report_lines.extend(self._build_recommendations_section(
            pdt_report, health_report
        ))
        
        # Footer
        report_lines.extend(self._build_footer())
        
        # Save report
        report_text = '\n'.join(report_lines)
        report_file = self._save_report(report_text, report_date)
        
        return report_file
    
    def _build_header(self, report_date: str) -> List[str]:
        """Build report header"""
        return [
            "=" * 80,
            "LITEBOTX DAILY TRADING REPORT",
            "=" * 80,
            f"Date: {report_date}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This report summarizes all trading activity, system health, and",
            "compliance checks for the day.",
            "=" * 80,
            ""
        ]
    
    def _build_executive_summary(self, pdt_report: Dict, health_report: Dict, 
                                corrections: List[Dict]) -> List[str]:
        """Build executive summary section"""
        
        # Determine overall status
        pdt_status = pdt_report['compliance_status']
        health_status = health_report['overall_status']
        
        if pdt_status == 'PASS' and health_status == 'HEALTHY':
            overall = "✅ ALL SYSTEMS OPERATIONAL"
        elif pdt_status == 'FAIL':
            overall = "🚨 CRITICAL: PDT VIOLATIONS DETECTED"
        elif health_status == 'CRITICAL':
            overall = "🚨 CRITICAL: SYSTEM HEALTH ISSUES"
        elif health_status == 'DEGRADED':
            overall = "⚠️ WARNING: SYSTEM DEGRADED"
        else:
            overall = "⚠️ ATTENTION REQUIRED"
        
        lines = [
            "EXECUTIVE SUMMARY",
            "-" * 80,
            f"Overall Status: {overall}",
            "",
            "Quick Stats:",
            f"  • Positions Opened: {health_report['metrics']['positions_opened']}",
            f"  • Positions Closed: {health_report['metrics']['positions_closed']}",
            f"  • PDT Compliance: {pdt_status}",
            f"  • System Health: {health_status} ({health_report['system_health_score']}/100)",
            f"  • Issues Detected: {health_report['issues_found']}",
            f"  • Auto-Corrections: {len(corrections)}",
            ""
        ]
        
        return lines
    
    def _build_pdt_section(self, pdt_report: Dict) -> List[str]:
        """Build PDT compliance section"""
        lines = [
            "PDT COMPLIANCE AUDIT",
            "-" * 80,
            f"Compliance Status: {pdt_report['compliance_status']}",
            f"Positions Checked: {pdt_report['positions_checked']}",
            f"Violations Found: {pdt_report['violations_found']}",
            f"Critical Violations: {pdt_report['critical_violations']}",
            ""
        ]
        
        if pdt_report['violations_found'] > 0:
            lines.append("⚠️ VIOLATIONS DETECTED:")
            lines.append("")
            
            for v in pdt_report['violations']:
                lines.append(f"  Symbol: {v['symbol']}")
                lines.append(f"  Type: {v['violation_type']}")
                lines.append(f"  Severity: {v['severity']}")
                lines.append(f"  Details: {v['details']}")
                lines.append("")
        else:
            lines.append("✅ No PDT violations detected - excellent compliance!")
            lines.append("")
        
        return lines
    
    def _build_health_section(self, health_report: Dict) -> List[str]:
        """Build system health section"""
        lines = [
            "SYSTEM HEALTH CHECK",
            "-" * 80,
            f"Health Status: {health_report['overall_status']}",
            f"Health Score: {health_report['system_health_score']}/100",
            f"Issues Found: {health_report['issues_found']}",
            ""
        ]
        
        if health_report['issues_found'] > 0:
            lines.append("⚠️ ISSUES DETECTED:")
            lines.append("")
            
            for issue in health_report['issues']:
                lines.append(f"  • {issue['severity']}: {issue['message']}")
                lines.append(f"    Current: {issue['metric_value']}")
                lines.append(f"    Expected: {issue['expected_value']}")
                if issue.get('auto_fixable'):
                    lines.append(f"    Auto-fixable: Yes")
                lines.append("")
        else:
            lines.append("✅ System is healthy - all checks passed!")
            lines.append("")
        
        return lines
    
    def _build_performance_section(self, metrics: Dict) -> List[str]:
        """Build trading performance section"""
        lines = [
            "TRADING PERFORMANCE",
            "-" * 80,
            "",
            "Signal Processing:",
            f"  • Signals Generated: {metrics.get('signals_generated', 0)}",
            f"  • Signals Executed: {metrics.get('signals_executed', 0)}",
            f"  • Signals Blocked: {metrics.get('signals_blocked', 0)}",
            f"  • Execution Rate: {metrics.get('execution_rate', 0):.1%}",
            "",
            "Pre-Filter Results:",
            f"  • Input Symbols: {metrics.get('prefilter_input_symbols', 0)}",
            f"  • Output Candidates: {metrics.get('prefilter_candidates', 0)}",
            "",
            "Position Activity:",
            f"  • Positions Opened: {metrics.get('positions_opened', 0)}",
            f"  • Positions Closed: {metrics.get('positions_closed', 0)}",
            "",
            "Error Tracking:",
            f"  • Errors: {metrics.get('errors_count', 0)}",
            f"  • Warnings: {metrics.get('warnings_count', 0)}",
            f"  • API Errors: {metrics.get('api_errors', 0)}",
            ""
        ]
        
        # Exit reasons breakdown
        exit_reasons = metrics.get('exit_reasons', {})
        if exit_reasons:
            lines.append("Exit Reasons:")
            for reason, count in exit_reasons.items():
                lines.append(f"  • {reason}: {count}")
            lines.append("")
        
        return lines
    
    def _build_corrections_section(self, corrections: List[Dict]) -> List[str]:
        """Build auto-corrections section"""
        lines = [
            "AUTO-CORRECTIONS APPLIED",
            "-" * 80,
            f"Total Corrections: {len(corrections)}",
            ""
        ]
        
        for i, correction in enumerate(corrections, 1):
            lines.append(f"{i}. {correction['parameter'].upper()}")
            lines.append(f"   Old Value: {correction['old_value']}")
            lines.append(f"   New Value: {correction['new_value']}")
            lines.append(f"   Reason: {correction['reason']}")
            lines.append(f"   Status: {'✅ Success' if correction['success'] else '❌ Failed'}")
            lines.append("")
        
        return lines
    
    def _build_recommendations_section(self, pdt_report: Dict, 
                                     health_report: Dict) -> List[str]:
        """Build recommendations section"""
        lines = [
            "RECOMMENDATIONS",
            "-" * 80,
            ""
        ]
        
        # Collect all recommendations
        all_recommendations = []
        
        if pdt_report.get('recommendations'):
            all_recommendations.extend(pdt_report['recommendations'])
        
        if health_report.get('recommendations'):
            all_recommendations.extend(health_report['recommendations'])
        
        if all_recommendations:
            for rec in all_recommendations:
                lines.append(rec)
        else:
            lines.append("✅ No action required - system is operating optimally")
        
        lines.append("")
        
        return lines
    
    def _build_footer(self) -> List[str]:
        """Build report footer"""
        return [
            "=" * 80,
            "END OF REPORT",
            "",
            "For detailed logs, see:",
            "  • PDT Audit: monitoring/reports/pdt/",
            "  • Health Reports: monitoring/reports/health/",
            "  • Trading Logs: logs/short_cycle_trader.log",
            "",
            "Questions? Check SELF_MONITORING_SYSTEM_PROPOSAL.md for details.",
            "=" * 80
        ]
    
    def _save_report(self, report_text: str, report_date: str) -> str:
        """Save report to file"""
        # Save as text file
        txt_file = self.report_dir / f"daily_report_{report_date}.txt"
        
        with open(txt_file, 'w') as f:
            f.write(report_text)
        
        self.logger.info(f"📄 Daily report saved: {txt_file}")
        
        # Also save as markdown for better readability
        md_file = self.report_dir / f"daily_report_{report_date}.md"
        
        with open(md_file, 'w') as f:
            f.write(report_text)
        
        self.logger.info(f"📄 Markdown report saved: {md_file}")
        
        return str(txt_file)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n📝 Daily Report Generator")
    print("This module generates human-readable daily reports.")
    print("It's called automatically by the monitoring system.")
