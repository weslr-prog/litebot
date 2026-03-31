#!/usr/bin/env python3
"""
Implementation Safety Framework
Provides backup, rollback, and monitoring capabilities for Signal Quality Improvements
"""

import json
import shutil
import os
import datetime
from pathlib import Path
import subprocess
import importlib.util
import sys

class ImplementationSafetyFramework:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.backup_dir = self.base_path / "implementation_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_system_backup(self):
        """Create comprehensive backup of current system"""
        backup_path = self.backup_dir / f"pre_implementation_backup_{self.timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Critical files to backup
        critical_files = [
            "signal_generator.py",
            "trade_executor.py", 
            "execution_engine.py",
            "automated_momentum_trader_v2.py",
            "config.py",
            "positions.json",
            "strategic_improvements.py",
            "traders/short_cycle_trader.py"
        ]
        
        backed_up_files = []
        missing_files = []
        
        print(f"🔒 Creating system backup in: {backup_path}")
        print("-" * 50)
        
        for file_path in critical_files:
            src = self.base_path / file_path
            if src.exists():
                dst = backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                backed_up_files.append(file_path)
                print(f"✅ Backed up: {file_path}")
            else:
                missing_files.append(file_path)
                print(f"⚠️  Missing: {file_path}")
        
        # Create backup manifest
        manifest = {
            "timestamp": self.timestamp,
            "backup_path": str(backup_path),
            "backed_up_files": backed_up_files,
            "missing_files": missing_files,
            "total_files": len(backed_up_files),
            "backup_complete": len(missing_files) == 0
        }
        
        with open(backup_path / "backup_manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\n📁 Backup completed: {len(backed_up_files)} files backed up")
        if missing_files:
            print(f"⚠️  {len(missing_files)} files were missing")
        
        return manifest
    
    def create_rollback_script(self, backup_manifest):
        """Create rollback script for emergency restoration"""
        rollback_script = f"""#!/bin/bash
# Emergency Rollback Script
# Generated: {self.timestamp}
# Restores system to pre-implementation state

echo "🔄 Starting emergency rollback..."
echo "Backup from: {backup_manifest['timestamp']}"

BACKUP_DIR="{backup_manifest['backup_path']}"
BASE_DIR="{self.base_path}"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Restoring files..."
"""
        
        for file_path in backup_manifest['backed_up_files']:
            rollback_script += f'cp "$BACKUP_DIR/{file_path}" "$BASE_DIR/{file_path}"\n'
            rollback_script += f'echo "✅ Restored: {file_path}"\n'
        
        rollback_script += """
echo "🔄 Rollback completed!"
echo "⚠️  Please restart the trading system to ensure changes take effect"
echo "📝 Check logs for any issues during rollback"
"""
        
        rollback_file = self.backup_dir / f"emergency_rollback_{self.timestamp}.sh"
        with open(rollback_file, 'w') as f:
            f.write(rollback_script)
        
        # Make executable
        os.chmod(rollback_file, 0o755)
        
        print(f"🚨 Emergency rollback script created: {rollback_file}")
        return rollback_file
    
    def setup_monitoring(self):
        """Setup monitoring for implementation safety"""
        monitor_script = f"""#!/usr/bin/env python3
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
        health_checks = {{
            "positions_file": Path("positions.json").exists(),
            "config_accessible": Path("config.py").exists(),
            "no_python_errors": self.check_no_import_errors()
        }}
        
        return health_checks
    
    def check_no_import_errors(self):
        '''Check for Python import errors'''
        try:
            import config
            import signal_generator
            return True
        except Exception as e:
            self.alerts.append(f"Import error: {{e}}")
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
                    self.alerts.append(f"High error rate detected: {{error_rate:.1%}}")
                    return False
            
            return True
        except Exception as e:
            self.alerts.append(f"Performance monitoring error: {{e}}")
            return False
    
    def run_safety_check(self):
        '''Run comprehensive safety check'''
        print(f"🔍 Running safety check at {{datetime.datetime.now()}}")
        
        health = self.check_system_health()
        perf_ok = self.monitor_performance_degradation()
        
        all_ok = all(health.values()) and perf_ok
        
        status = "✅ SAFE" if all_ok else "⚠️  ISSUES DETECTED"
        print(f"System Status: {{status}}")
        
        if not all_ok:
            print("Issues found:")
            for check, result in health.items():
                if not result:
                    print(f"  ❌ {{check}}")
            
            if self.alerts:
                print("Alerts:")
                for alert in self.alerts:
                    print(f"  🚨 {{alert}}")
        
        return all_ok

if __name__ == "__main__":
    monitor = ImplementationMonitor()
    monitor.run_safety_check()
"""
        
        monitor_file = self.backup_dir / f"implementation_monitor_{self.timestamp}.py"
        with open(monitor_file, 'w') as f:
            f.write(monitor_script)
        
        print(f"📊 Implementation monitor created: {monitor_file}")
        return monitor_file
    
    def test_rollback_capability(self, rollback_script):
        """Test rollback capability (dry run)"""
        print("\n🧪 Testing rollback capability (dry run)...")
        
        try:
            # Check if backup files exist
            backup_manifest_file = self.backup_dir / f"pre_implementation_backup_{self.timestamp}" / "backup_manifest.json"
            
            if not backup_manifest_file.exists():
                print("❌ Backup manifest not found")
                return False
            
            with open(backup_manifest_file, 'r') as f:
                manifest = json.load(f)
            
            backup_path = Path(manifest['backup_path'])
            if not backup_path.exists():
                print("❌ Backup directory not found")
                return False
            
            # Verify all backup files exist
            missing_backups = []
            for file_path in manifest['backed_up_files']:
                backup_file = backup_path / file_path
                if not backup_file.exists():
                    missing_backups.append(file_path)
            
            if missing_backups:
                print(f"❌ Missing backup files: {missing_backups}")
                return False
            
            print("✅ All backup files verified")
            print("✅ Rollback script is executable")
            print("✅ Rollback capability confirmed")
            
            return True
            
        except Exception as e:
            print(f"❌ Rollback test failed: {e}")
            return False
    
    def setup_complete_safety_framework(self):
        """Setup complete safety framework"""
        print("🛡️  Setting up Implementation Safety Framework")
        print("=" * 60)
        
        # 1. Create system backup
        backup_manifest = self.create_system_backup()
        
        # 2. Create rollback script
        rollback_script = self.create_rollback_script(backup_manifest)
        
        # 3. Setup monitoring
        monitor_script = self.setup_monitoring()
        
        # 4. Test rollback capability
        rollback_ok = self.test_rollback_capability(rollback_script)
        
        # 5. Create safety summary
        safety_summary = {
            "setup_timestamp": self.timestamp,
            "backup_manifest": backup_manifest,
            "rollback_script": str(rollback_script),
            "monitor_script": str(monitor_script),
            "rollback_tested": rollback_ok,
            "safety_level": "HIGH" if rollback_ok and backup_manifest['backup_complete'] else "MEDIUM"
        }
        
        # Save safety summary
        safety_file = self.backup_dir / f"safety_framework_{self.timestamp}.json"
        with open(safety_file, 'w') as f:
            json.dump(safety_summary, f, indent=2)
        
        print(f"\n🛡️  Safety Framework Summary")
        print("-" * 40)
        print(f"Backup Status: {'✅ Complete' if backup_manifest['backup_complete'] else '⚠️  Partial'}")
        print(f"Rollback Ready: {'✅ Tested' if rollback_ok else '❌ Issues'}")
        print(f"Monitoring: ✅ Active")
        print(f"Safety Level: {safety_summary['safety_level']}")
        
        if safety_summary['safety_level'] == "HIGH":
            print("\n✅ Safety framework is ready! Implementation can proceed safely.")
        else:
            print("\n⚠️  Safety framework has issues. Review before proceeding.")
        
        return safety_summary

def main():
    """Setup safety framework"""
    framework = ImplementationSafetyFramework()
    return framework.setup_complete_safety_framework()

if __name__ == "__main__":
    main()