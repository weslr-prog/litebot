#!/usr/bin/env python3
"""
Self-Monitoring System Coordinator
===================================
Main entry point for the self-monitoring system. Coordinates all monitoring
modules and generates comprehensive daily reports.

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdt_auditor import PDTAuditor
from daily_health_checker import DailyHealthChecker
from auto_corrector import AutoCorrector
from daily_report_generator import DailyReportGenerator


class SelfMonitoringSystem:
    """
    Coordinates all self-monitoring modules and generates daily reports.
    Called automatically at end of trading day.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize all modules
        self.pdt_auditor = PDTAuditor()
        self.health_checker = DailyHealthChecker()
        self.auto_corrector = AutoCorrector()
        self.report_generator = DailyReportGenerator()
        
        self.logger.info("🤖 Self-Monitoring System initialized")
    
    def run_end_of_day_check(self, trade_date: str = None) -> dict:
        """
        Run complete end-of-day monitoring check.
        
        Args:
            trade_date: Date to check (YYYY-MM-DD). Defaults to today.
            
        Returns:
            Dict containing summary of all checks
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        
        self.logger.info("=" * 80)
        self.logger.info(f"🤖 STARTING END-OF-DAY MONITORING - {trade_date}")
        self.logger.info("=" * 80)
        
        results = {
            'date': trade_date,
            'timestamp': datetime.now().isoformat(),
            'pdt_audit': None,
            'health_check': None,
            'corrections_applied': [],
            'report_file': None
        }
        
        # Step 1: PDT Compliance Audit
        self.logger.info("\n📋 Step 1/4: Running PDT compliance audit...")
        try:
            pdt_report = self.pdt_auditor.audit_daily_trades(trade_date)
            results['pdt_audit'] = pdt_report
            
            if pdt_report['compliance_status'] == 'PASS':
                self.logger.info("✅ PDT audit PASSED")
            else:
                self.logger.warning(f"⚠️ PDT audit FAILED - {pdt_report['violations_found']} violations")
        
        except Exception as e:
            self.logger.error(f"❌ PDT audit failed: {e}", exc_info=True)
        
        # Step 2: System Health Check
        self.logger.info("\n🏥 Step 2/4: Running system health check...")
        try:
            health_report = self.health_checker.run_daily_check(trade_date)
            results['health_check'] = health_report
            
            if health_report['overall_status'] == 'HEALTHY':
                self.logger.info("✅ Health check PASSED")
            else:
                self.logger.warning(f"⚠️ Health status: {health_report['overall_status']}")
        
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}", exc_info=True)
        
        # Step 3: Auto-Corrections (if needed)
        self.logger.info("\n🔧 Step 3/4: Checking for auto-corrections...")
        try:
            if results['health_check']:
                corrections = self.auto_corrector.apply_corrections(results['health_check'])
                results['corrections_applied'] = [c.to_dict() for c in corrections]
                
                if corrections:
                    self.logger.info(f"✅ Applied {len(corrections)} auto-corrections")
                else:
                    self.logger.info("ℹ️ No corrections needed")
            else:
                self.logger.warning("⚠️ Skipping auto-corrections (no health report)")
        
        except Exception as e:
            self.logger.error(f"❌ Auto-corrections failed: {e}", exc_info=True)
        
        # Step 4: Generate Daily Report
        self.logger.info("\n📝 Step 4/4: Generating daily report...")
        try:
            if results['pdt_audit'] and results['health_check']:
                report_file = self.report_generator.generate_daily_report(
                    pdt_report=results['pdt_audit'],
                    health_report=results['health_check'],
                    corrections=results['corrections_applied'],
                    report_date=trade_date
                )
                results['report_file'] = report_file
                
                self.logger.info(f"✅ Daily report generated: {report_file}")
            else:
                self.logger.warning("⚠️ Skipping report generation (missing data)")
        
        except Exception as e:
            self.logger.error(f"❌ Report generation failed: {e}", exc_info=True)
        
        # Final Summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🤖 END-OF-DAY MONITORING COMPLETE")
        self.logger.info("=" * 80)
        self.logger.info(f"PDT Status: {results['pdt_audit']['compliance_status'] if results['pdt_audit'] else 'N/A'}")
        self.logger.info(f"Health Status: {results['health_check']['overall_status'] if results['health_check'] else 'N/A'}")
        self.logger.info(f"Corrections: {len(results['corrections_applied'])}")
        self.logger.info(f"Report: {results['report_file'] or 'Not generated'}")
        self.logger.info("=" * 80)
        
        return results
    
    def get_status_summary(self) -> dict:
        """Get current status summary of monitoring system"""
        
        # Check for active emergency flags
        emergency_pdt = Path("monitoring/EMERGENCY_PDT_MODE.flag").exists()
        
        # Get recent correction history
        correction_summary = self.auto_corrector.get_correction_summary(days=7)
        
        summary = {
            'monitoring_active': True,
            'emergency_pdt_mode': emergency_pdt,
            'recent_corrections': correction_summary['total_corrections'],
            'modules': {
                'pdt_auditor': 'active',
                'health_checker': 'active',
                'auto_corrector': 'active',
                'report_generator': 'active'
            }
        }
        
        return summary


def run_monitoring(date: str = None):
    """
    Convenience function to run monitoring from command line or cron.
    
    Usage:
        python monitoring_system.py
        python monitoring_system.py 2025-10-05
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('monitoring/monitoring_system.log'),
            logging.StreamHandler()
        ]
    )
    
    # Run monitoring
    system = SelfMonitoringSystem()
    results = system.run_end_of_day_check(date)
    
    # Print summary
    print("\n" + "=" * 80)
    print("MONITORING SUMMARY")
    print("=" * 80)
    print(f"Date: {results['date']}")
    print(f"PDT Compliance: {results['pdt_audit']['compliance_status'] if results['pdt_audit'] else 'N/A'}")
    print(f"System Health: {results['health_check']['overall_status'] if results['health_check'] else 'N/A'}")
    print(f"Auto-Corrections: {len(results['corrections_applied'])}")
    print(f"\nDaily Report: {results['report_file']}")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import sys
    
    # Get date from command line if provided
    check_date = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run monitoring
    run_monitoring(check_date)
