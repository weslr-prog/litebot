#!/usr/bin/env python3
"""
Self-Monitoring Integration Hook
=================================
Add this code to traders/short_cycle_trader.py to enable automatic
self-monitoring at end of trading day.

INTEGRATION INSTRUCTIONS:
========================

1. Add import at top of short_cycle_trader.py:
   
   from monitoring.monitoring_system import SelfMonitoringSystem

2. Add to __init__ method:
   
   # Self-monitoring system
   try:
       self.monitoring_system = SelfMonitoringSystem()
       self.logger.info("🤖 Self-monitoring system enabled")
   except Exception as e:
       self.logger.warning(f"Self-monitoring unavailable: {e}")
       self.monitoring_system = None

3. Add to end of run() method (after market close):
   
   # Run end-of-day monitoring
   if self.monitoring_system:
       try:
           self.logger.info("🤖 Running end-of-day self-monitoring...")
           monitoring_results = self.monitoring_system.run_end_of_day_check()
           
           # Log summary
           if monitoring_results.get('report_file'):
               self.logger.info(f"📄 Daily report: {monitoring_results['report_file']}")
           
           # Check for critical issues
           if monitoring_results.get('pdt_audit'):
               if monitoring_results['pdt_audit']['violations_found'] > 0:
                   self.logger.critical(
                       f"🚨 PDT VIOLATIONS: {monitoring_results['pdt_audit']['violations_found']} detected"
                   )
           
           if monitoring_results.get('health_check'):
               health_status = monitoring_results['health_check']['overall_status']
               if health_status == 'CRITICAL':
                   self.logger.critical(f"🚨 SYSTEM HEALTH: {health_status}")
               elif health_status != 'HEALTHY':
                   self.logger.warning(f"⚠️ System health: {health_status}")
       
       except Exception as e:
           self.logger.error(f"❌ Self-monitoring failed: {e}", exc_info=True)

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

# This file serves as documentation for integration
# The actual integration will be done in short_cycle_trader.py

INTEGRATION_CODE = '''
# =============================================================================
# SELF-MONITORING SYSTEM INTEGRATION
# =============================================================================

# 1. Add import at top of file (after other imports)
from monitoring.monitoring_system import SelfMonitoringSystem

# 2. Add to __init__ method (after safety_monitor initialization)
# Self-monitoring system
try:
    self.monitoring_system = SelfMonitoringSystem()
    self.logger.info("🤖 Self-monitoring system enabled")
except Exception as e:
    self.logger.warning(f"Self-monitoring unavailable: {e}")
    self.monitoring_system = None

# 3. Add to run() method at end (after "Market closed" section)
# Run end-of-day self-monitoring
if self.monitoring_system:
    try:
        self.logger.info("\\n" + "="*80)
        self.logger.info("🤖 STARTING END-OF-DAY SELF-MONITORING")
        self.logger.info("="*80)
        
        monitoring_results = self.monitoring_system.run_end_of_day_check()
        
        # Log report location
        if monitoring_results.get('report_file'):
            self.logger.info(f"📄 Daily report available: {monitoring_results['report_file']}")
        
        # Alert on PDT violations
        if monitoring_results.get('pdt_audit'):
            pdt_violations = monitoring_results['pdt_audit']['violations_found']
            if pdt_violations > 0:
                self.logger.critical(
                    f"🚨 PDT VIOLATIONS DETECTED: {pdt_violations} violations found"
                )
                self.logger.critical("   Review: monitoring/reports/pdt/")
        
        # Alert on system health
        if monitoring_results.get('health_check'):
            health_status = monitoring_results['health_check']['overall_status']
            health_score = monitoring_results['health_check']['system_health_score']
            
            if health_status == 'CRITICAL':
                self.logger.critical(f"🚨 SYSTEM HEALTH CRITICAL (Score: {health_score}/100)")
            elif health_status == 'DEGRADED':
                self.logger.warning(f"⚠️ System health degraded (Score: {health_score}/100)")
            else:
                self.logger.info(f"✅ System healthy (Score: {health_score}/100)")
        
        # Report auto-corrections
        corrections = monitoring_results.get('corrections_applied', [])
        if corrections:
            self.logger.info(f"🔧 Auto-corrections applied: {len(corrections)}")
            for c in corrections:
                self.logger.info(f"   • {c['parameter']}: {c['old_value']} → {c['new_value']}")
        
        self.logger.info("="*80)
        self.logger.info("🤖 SELF-MONITORING COMPLETE")
        self.logger.info("="*80 + "\\n")
    
    except Exception as e:
        self.logger.error(f"❌ Self-monitoring system error: {e}", exc_info=True)
'''

if __name__ == "__main__":
    print("=" * 80)
    print("SELF-MONITORING SYSTEM INTEGRATION")
    print("=" * 80)
    print("\nThis file contains the integration code for short_cycle_trader.py")
    print("\nTo integrate, add the following code to traders/short_cycle_trader.py:")
    print(INTEGRATION_CODE)
    print("\n" + "=" * 80)
