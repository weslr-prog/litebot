#!/usr/bin/env python3
'''
Implementation Monitor
Monitors system health during Signal Quality Implementation
'''

import json
import time
import datetime
from pathlib import Path

class ImplementationMonitor:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.start_time = datetime.datetime.now()
        self.alerts = []
        
    def check_system_health(self):
        '''Check critical system components'''
        health_checks = {
            "positions_file": Path("positions.json").exists(),
            "config_accessible": Path("config.py").exists(),
            "no_python_errors": self.check_no_import_errors()
        }
        
        return health_checks
    
    def check_no_import_errors(self):
        '''Check for Python import errors'''
        try:
            import config
            import signal_generator
            return True
        except Exception as e:
            self.alerts.append(f"Import error: {e}")
            return False
    
    def monitor_performance_degradation(self):
        '''Monitor for unexpected performance drops'''
        try:
            with open("positions.json", 'r') as f:
                positions = json.load(f)
            
            recent_positions = positions[-10:] if len(positions) >= 10 else positions
            
            if recent_positions:
                error_count = sum(1 for p in recent_positions if p.get('status') == 'error')
                error_rate = error_count / len(recent_positions)
                
                if error_rate > 0.3:  # More than 30% errors
                    self.alerts.append(f"High error rate detected: {error_rate:.1%}")
                    return False
            
            return True
        except Exception as e:
            self.alerts.append(f"Performance monitoring error: {e}")
            return False
    
    def run_safety_check(self):
        '''Run comprehensive safety check'''
        print(f"🔍 Running safety check at {datetime.datetime.now()}")
        
        health = self.check_system_health()
        perf_ok = self.monitor_performance_degradation()
        
        all_ok = all(health.values()) and perf_ok
        
        status = "✅ SAFE" if all_ok else "⚠️  ISSUES DETECTED"
        print(f"System Status: {status}")
        
        if not all_ok:
            print("Issues found:")
            for check, result in health.items():
                if not result:
                    print(f"  ❌ {check}")
            
            if self.alerts:
                print("Alerts:")
                for alert in self.alerts:
                    print(f"  🚨 {alert}")
        
        return all_ok

if __name__ == "__main__":
    monitor = ImplementationMonitor()
    monitor.run_safety_check()
