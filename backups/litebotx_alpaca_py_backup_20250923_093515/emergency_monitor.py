#!/usr/bin/env python3
"""
Emergency Stop Monitor for LiteBotX
Checks for emergency stop signals and halts trading
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

class EmergencyMonitor:
    def __init__(self):
        self.emergency_flag_file = 'EMERGENCY_STOP.flag'
        self.risk_settings_file = 'risk_settings.json'
        self.default_risk_settings = {
            'max_position_pct': 5,
            'stop_loss_pct': 3,
            'max_exposure_pct': 85,
            'daily_loss_limit_pct': 2
        }
        
    def check_emergency_stop(self):
        """Check if emergency stop has been triggered"""
        if os.path.exists(self.emergency_flag_file):
            with open(self.emergency_flag_file, 'r') as f:
                flag_content = f.read()
            print(f"🛑 EMERGENCY STOP DETECTED: {flag_content}")
            return True
        return False
    
    def clear_emergency_stop(self):
        """Clear the emergency stop flag"""
        if os.path.exists(self.emergency_flag_file):
            os.remove(self.emergency_flag_file)
            print("✅ Emergency stop flag cleared")
    
    def load_risk_settings(self):
        """Load current risk settings"""
        try:
            if os.path.exists(self.risk_settings_file):
                with open(self.risk_settings_file, 'r') as f:
                    settings = json.load(f)
                return settings
            else:
                return self.default_risk_settings
        except Exception as e:
            print(f"⚠️ Error loading risk settings: {e}")
            return self.default_risk_settings
    
    def save_risk_settings(self, settings):
        """Save risk settings to file"""
        try:
            settings['updated_at'] = datetime.now().isoformat()
            with open(self.risk_settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print(f"✅ Risk settings saved: {settings}")
        except Exception as e:
            print(f"❌ Error saving risk settings: {e}")
    
    def check_risk_limits(self, portfolio_value, daily_pnl, position_value=None):
        """Check if current trading is within risk limits"""
        settings = self.load_risk_settings()
        
        # Check daily loss limit
        daily_loss_pct = (daily_pnl / portfolio_value) * 100 if portfolio_value > 0 else 0
        if daily_loss_pct < -settings['daily_loss_limit_pct']:
            print(f"⚠️ DAILY LOSS LIMIT EXCEEDED: {daily_loss_pct:.2f}% (limit: -{settings['daily_loss_limit_pct']}%)")
            return False, "daily_loss_limit"
        
        # Check position size limit
        if position_value:
            position_pct = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0
            if position_pct > settings['max_position_pct']:
                print(f"⚠️ POSITION SIZE LIMIT EXCEEDED: {position_pct:.2f}% (limit: {settings['max_position_pct']}%)")
                return False, "position_size_limit"
        
        return True, "within_limits"
    
    def create_emergency_stop(self, reason="Manual emergency stop"):
        """Create emergency stop flag"""
        try:
            with open(self.emergency_flag_file, 'w') as f:
                f.write(f"Emergency stop: {reason} at {datetime.now()}")
            print(f"🛑 Emergency stop created: {reason}")
        except Exception as e:
            print(f"❌ Error creating emergency stop: {e}")

# Standalone emergency stop function for trading bots
def check_trading_allowed():
    """Quick check if trading is allowed - call this before each trade"""
    monitor = EmergencyMonitor()
    
    # Check emergency stop
    if monitor.check_emergency_stop():
        return False, "Emergency stop active"
    
    return True, "Trading allowed"

# Command line interface
if __name__ == "__main__":
    monitor = EmergencyMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "stop":
            monitor.create_emergency_stop("Command line emergency stop")
        elif command == "clear":
            monitor.clear_emergency_stop()
        elif command == "check":
            if monitor.check_emergency_stop():
                print("🛑 Emergency stop is ACTIVE")
                sys.exit(1)
            else:
                print("✅ Trading is ALLOWED")
                sys.exit(0)
        elif command == "settings":
            settings = monitor.load_risk_settings()
            print("📊 Current Risk Settings:")
            for key, value in settings.items():
                print(f"   {key}: {value}")
        else:
            print("Usage: python emergency_monitor.py [stop|clear|check|settings]")
    else:
        print("LiteBotX Emergency Monitor")
        print("Commands:")
        print("  stop     - Create emergency stop")
        print("  clear    - Clear emergency stop")
        print("  check    - Check if trading allowed")
        print("  settings - Show risk settings")
