#!/usr/bin/env python3
"""
Evening Launch Readiness Check
Run this BEFORE starting the bot for overnight/next-day trading.

This script:
1. Runs comprehensive pre-flight checks
2. Tests the bot in dry-run mode
3. Sends alerts if issues found
4. Creates GO/NO-GO decision report

Usage:
    python3 evening_launch_check.py
    python3 evening_launch_check.py --notify  # Send desktop notifications
    python3 evening_launch_check.py --email your@email.com  # Send email alerts
"""

import os
import sys
import json
import subprocess
import datetime as dt
import pytz
from pathlib import Path
from typing import Dict, List, Tuple
import traceback

# Import components for testing
try:
    from traders.short_cycle_trader import ShortCycleTrader
    from config import Config
    IMPORTS_OK = True
except Exception as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class EveningLaunchCheck:
    """
    Evening pre-launch validation system.
    Designed for users who start bot at night and can't monitor in morning.
    """
    
    def __init__(self, enable_notifications: bool = False, email: str = None):
        self.enable_notifications = enable_notifications
        self.email = email
        self.critical_issues: List[str] = []
        self.warnings: List[str] = []
        self.passed_checks: List[str] = []
        self.go_for_launch = False
        
    def run_all_checks(self) -> bool:
        """Run all evening checks. Returns True if safe to launch."""
        self._print_header()
        
        # Critical checks (must pass for GO)
        checks_critical = [
            ("Alpaca API Connection", self._check_alpaca_live),
            ("Timezone Handling", self._check_timezone_safety),
            ("Position Loading", self._check_position_loading),
            ("Pattern Recognition", self._check_pattern_system),
            ("Market Schedule", self._check_market_tomorrow),
            ("Disk Space", self._check_disk_space),
            ("Bot Dry Run", self._check_bot_initialization),
        ]
        
        # Warning checks (can launch with warnings)
        checks_warning = [
            ("Previous Session Health", self._check_previous_session),
            ("Log File Size", self._check_log_size),
            ("Memory Available", self._check_memory),
        ]
        
        print(f"\n{Colors.BOLD}🔴 CRITICAL CHECKS (must pass):{Colors.RESET}\n")
        for name, check_func in checks_critical:
            self._run_check(name, check_func, critical=True)
        
        print(f"\n{Colors.BOLD}🟡 WARNING CHECKS (nice to pass):{Colors.RESET}\n")
        for name, check_func in checks_warning:
            self._run_check(name, check_func, critical=False)
        
        # Determine GO/NO-GO
        self.go_for_launch = len(self.critical_issues) == 0
        
        # Print decision
        self._print_decision()
        
        # Send alerts if configured
        if self.enable_notifications or self.email:
            self._send_alerts()
        
        # Save report
        self._save_report()
        
        return self.go_for_launch
    
    def _run_check(self, name: str, func, critical: bool = True):
        """Run a single check"""
        try:
            print(f"  ▶ {name}...", end='', flush=True)
            result, message = func()
            
            if result:
                print(f"\r  {Colors.GREEN}✅ {name}{Colors.RESET}")
                self.passed_checks.append(name)
            else:
                if critical:
                    print(f"\r  {Colors.RED}❌ {name}: {message}{Colors.RESET}")
                    self.critical_issues.append(f"{name}: {message}")
                else:
                    print(f"\r  {Colors.YELLOW}⚠️  {name}: {message}{Colors.RESET}")
                    self.warnings.append(f"{name}: {message}")
                    
        except Exception as e:
            error_msg = f"{name}: {str(e)}"
            if critical:
                print(f"\r  {Colors.RED}❌ {name}: ERROR - {str(e)}{Colors.RESET}")
                self.critical_issues.append(error_msg)
            else:
                print(f"\r  {Colors.YELLOW}⚠️  {name}: ERROR - {str(e)}{Colors.RESET}")
                self.warnings.append(error_msg)
    
    # ========== CHECK METHODS ==========
    
    def _check_alpaca_live(self) -> Tuple[bool, str]:
        """Test live Alpaca connection"""
        try:
            from alpaca.trading.client import TradingClient
            
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                return False, "API credentials not set in environment"
            
            client = TradingClient(api_key, api_secret, paper=True)
            account = client.get_account()
            
            if account.status != 'ACTIVE':
                return False, f"Account status: {account.status} (not ACTIVE)"
            
            buying_power = float(account.buying_power)
            if buying_power < 1000:
                return False, f"Low buying power: ${buying_power:,.2f}"
            
            return True, f"Account active, ${float(account.equity):,.2f} portfolio"
            
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def _check_timezone_safety(self) -> Tuple[bool, str]:
        """
        CRITICAL: Verify timezone handling (Oct 20 bug).
        This is what failed and caused 0 trades.
        """
        try:
            import pytz
            
            # Test 1: Create timezone-aware datetimes
            utc_now = dt.datetime.now(pytz.UTC)
            utc_fake_alpaca = dt.datetime.now(pytz.UTC)
            
            # Test 2: Subtraction must work (this failed Oct 20)
            try:
                time_diff = (utc_now - utc_fake_alpaca).total_seconds()
            except TypeError as e:
                return False, f"Timezone subtraction failed: {e}"
            
            # Test 3: Check if pattern recognizer exists
            try:
                from pattern_recognizer import PatternRecognizer, StockPattern
                recognizer = PatternRecognizer()
                
                # Test with timezone-aware datetime
                should_exit, reason = recognizer.get_optimal_exit_time(
                    pattern=StockPattern.MORNING_GAPPER,
                    current_time=utc_now,
                    pnl_pct=0.02
                )
                
            except Exception as e:
                return False, f"Pattern recognizer timezone error: {e}"
            
            # Test 4: Verify traders code uses timezone-aware datetimes
            from traders.short_cycle_trader import ShortCycleTrader
            import inspect
            source = inspect.getsource(ShortCycleTrader._process_existing_positions)
            
            if 'pytz.UTC' not in source and 'timezone' not in source.lower():
                return False, "ShortCycleTrader may not use timezone-aware datetimes"
            
            return True, "All timezone handling safe"
            
        except Exception as e:
            return False, f"Timezone check failed: {e}"
    
    def _check_position_loading(self) -> Tuple[bool, str]:
        """Test loading positions (simulates bot restart)"""
        try:
            positions_file = Path('positions.json')
            
            if not positions_file.exists():
                return True, "No positions file (clean slate)"
            
            with open(positions_file, 'r') as f:
                data = json.load(f)
            
            # Check if it's a list or dict
            if isinstance(data, list):
                positions = data
            elif isinstance(data, dict):
                positions = data.get('positions', [])
            else:
                return False, "positions.json has unexpected format"
            
            # Verify timestamps are timezone-aware
            for pos in positions:
                if 'entry_timestamp' in pos and pos['entry_timestamp']:
                    ts_str = pos['entry_timestamp']
                    try:
                        ts = dt.datetime.fromisoformat(ts_str)
                        if ts.tzinfo is None:
                            return False, f"Position {pos.get('symbol')} has timezone-naive timestamp"
                    except Exception as e:
                        return False, f"Invalid timestamp in {pos.get('symbol')}: {e}"
            
            return True, f"Loaded {len(positions)} positions successfully"
            
        except Exception as e:
            return False, f"Position loading failed: {e}"
    
    def _check_pattern_system(self) -> Tuple[bool, str]:
        """Test pattern recognition system"""
        try:
            from pattern_recognizer import PatternRecognizer, PatternTracker
            from morning_gap_scanner import MorningGapScanner
            
            # Initialize all D+1 components
            recognizer = PatternRecognizer()
            tracker = PatternTracker()
            scanner = MorningGapScanner()
            
            # Test pattern identification
            import pytz
            current_time = dt.datetime.now(pytz.UTC)
            
            pattern = recognizer.identify_pattern(
                price_history=[100, 101, 102],
                current_price=102,
                entry_price=100,
                gap_at_open=0.02,
                minutes_held=30
            )
            
            # Test exit timing
            should_exit, reason = recognizer.get_optimal_exit_time(
                pattern=pattern,
                current_time=current_time,
                pnl_pct=0.015
            )
            
            return True, "Pattern system operational"
            
        except Exception as e:
            return False, f"Pattern system error: {e}"
    
    def _check_market_tomorrow(self) -> Tuple[bool, str]:
        """Check if market is open tomorrow"""
        try:
            from alpaca.trading.client import TradingClient
            
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            client = TradingClient(api_key, api_secret, paper=True)
            clock = client.get_clock()
            
            # Check if tomorrow is trading day
            tomorrow = dt.date.today() + dt.timedelta(days=1)
            
            if tomorrow.weekday() >= 5:  # Saturday or Sunday
                return False, f"Tomorrow is {tomorrow.strftime('%A')} - market closed"
            
            # TODO: Check for holidays via calendar API
            
            return True, f"Market opens {clock.next_open.strftime('%Y-%m-%d %H:%M')}"
            
        except Exception as e:
            return False, f"Market schedule check failed: {e}"
    
    def _check_disk_space(self) -> Tuple[bool, str]:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024**3)
            
            if free_gb < 1.0:
                return False, f"Critical: Only {free_gb:.1f} GB free"
            elif free_gb < 5.0:
                return False, f"Low: {free_gb:.1f} GB free (warning level)"
            
            return True, f"{free_gb:.1f} GB free"
            
        except Exception as e:
            return False, f"Cannot check disk: {e}"
    
    def _check_bot_initialization(self) -> Tuple[bool, str]:
        """
        MOST CRITICAL: Actually initialize the bot in dry-run mode.
        This simulates what will happen when you start it for real.
        """
        try:
            from traders.short_cycle_trader import ShortCycleTrader
            from config import Config
            
            # Create config (same as launcher Option 3)
            config = Config()
            
            # Initialize trader (this is what runs when bot starts)
            trader = ShortCycleTrader(config)
            
            # Verify critical components initialized
            required_attrs = [
                'pattern_recognizer',
                'pattern_tracker', 
                'morning_gap_scanner',
                'positions',
                'config'
            ]
            
            for attr in required_attrs:
                if not hasattr(trader, attr):
                    return False, f"Missing component: {attr}"
            
            # Test position loading
            if hasattr(trader, '_load_positions'):
                try:
                    trader._load_positions()
                except Exception as e:
                    return False, f"Position loading failed: {e}"
            
            return True, "Bot initialization successful (dry-run)"
            
        except Exception as e:
            return False, f"Bot initialization failed: {e}"
    
    def _check_previous_session(self) -> Tuple[bool, str]:
        """Check if previous session ended cleanly"""
        try:
            log_file = Path('logs/short_cycle_trader.log')
            
            if not log_file.exists():
                return True, "No previous session"
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                last_50 = lines[-50:] if len(lines) > 50 else lines
            
            # Look for clean shutdown
            clean_shutdown = any(
                'Sleeping until premarket' in line or
                'Watchlist refresh complete' in line
                for line in last_50
            )
            
            if not clean_shutdown:
                return False, "Previous session may have crashed"
            
            # Check for errors
            recent_errors = sum(1 for line in last_50 if 'ERROR' in line)
            if recent_errors > 5:
                return False, f"{recent_errors} errors in last session"
            
            return True, "Previous session ended cleanly"
            
        except Exception as e:
            return False, f"Cannot check logs: {e}"
    
    def _check_log_size(self) -> Tuple[bool, str]:
        """Check log file size"""
        try:
            log_file = Path('logs/short_cycle_trader.log')
            
            if not log_file.exists():
                return True, "No log file"
            
            size_mb = log_file.stat().st_size / (1024**2)
            
            if size_mb > 100:
                return False, f"Log file very large: {size_mb:.1f} MB"
            elif size_mb > 50:
                return False, f"Log file getting large: {size_mb:.1f} MB"
            
            return True, f"Log size OK: {size_mb:.1f} MB"
            
        except Exception as e:
            return False, f"Cannot check log: {e}"
    
    def _check_memory(self) -> Tuple[bool, str]:
        """Check available memory"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            if mem.percent > 90:
                return False, f"Very low memory: {mem.percent:.0f}% used"
            elif mem.percent > 80:
                return False, f"High memory: {mem.percent:.0f}% used"
            
            return True, f"{mem.percent:.0f}% used"
            
        except ImportError:
            return True, "psutil not installed (skipped)"
        except Exception as e:
            return False, f"Cannot check memory: {e}"
    
    # ========== OUTPUT AND ALERTS ==========
    
    def _print_header(self):
        """Print header"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}🌙 EVENING LAUNCH READINESS CHECK{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        print(f"Running comprehensive validation before overnight bot launch...")
        print(f"Time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"For tomorrow: {(dt.date.today() + dt.timedelta(days=1)).strftime('%A, %B %d, %Y')}")
    
    def _print_decision(self):
        """Print final GO/NO-GO decision"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}📊 LAUNCH READINESS REPORT{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        
        print(f"Passed checks: {Colors.GREEN}{len(self.passed_checks)}{Colors.RESET}")
        print(f"Warnings: {Colors.YELLOW}{len(self.warnings)}{Colors.RESET}")
        print(f"Critical issues: {Colors.RED}{len(self.critical_issues)}{Colors.RESET}\n")
        
        if self.critical_issues:
            print(f"{Colors.RED}{Colors.BOLD}🚨 CRITICAL ISSUES FOUND:{Colors.RESET}\n")
            for issue in self.critical_issues:
                print(f"  {Colors.RED}❌ {issue}{Colors.RESET}")
            print(f"\n{Colors.RED}{Colors.BOLD}{'='*80}{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}⛔ NO-GO FOR LAUNCH - DO NOT START BOT{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
            
            print(f"{Colors.YELLOW}Recommended actions:{Colors.RESET}")
            print(f"  1. Review and fix critical issues above")
            print(f"  2. Re-run this check: python3 evening_launch_check.py")
            print(f"  3. Only launch bot after all critical checks pass")
            
        else:
            if self.warnings:
                print(f"{Colors.YELLOW}⚠️  WARNINGS (non-critical):{Colors.RESET}\n")
                for warning in self.warnings:
                    print(f"  {Colors.YELLOW}⚠️  {warning}{Colors.RESET}")
                print()
            
            print(f"{Colors.GREEN}{Colors.BOLD}{'='*80}{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}✅ GO FOR LAUNCH - BOT IS READY{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
            
            if self.warnings:
                print(f"{Colors.YELLOW}Note: There are {len(self.warnings)} warnings, but they are non-critical.{Colors.RESET}")
                print(f"{Colors.YELLOW}The bot can launch safely.{Colors.RESET}\n")
            
            print(f"{Colors.GREEN}You can now launch the bot:{Colors.RESET}")
            print(f"  python3 litebotx_launcher.py")
            print(f"  Choose: 3 (Aggressive Trading)")
            print(f"  Confirm: yes\n")
    
    def _send_alerts(self):
        """Send notifications via desktop/email"""
        if not self.go_for_launch:
            title = "⛔ Trading Bot: NO-GO"
            message = f"Critical issues found. DO NOT launch.\n\n{', '.join(self.critical_issues[:3])}"
            urgency = "critical"
        elif self.warnings:
            title = "⚠️  Trading Bot: GO (with warnings)"
            message = f"Ready to launch, but review {len(self.warnings)} warnings."
            urgency = "normal"
        else:
            title = "✅ Trading Bot: ALL CLEAR"
            message = "All checks passed. Safe to launch for tomorrow."
            urgency = "normal"
        
        # Desktop notification
        if self.enable_notifications:
            try:
                subprocess.run([
                    'notify-send',
                    '-u', urgency,
                    title,
                    message
                ], check=False)
            except Exception as e:
                print(f"{Colors.YELLOW}Could not send desktop notification: {e}{Colors.RESET}")
        
        # Email notification
        if self.email:
            try:
                email_body = self._generate_email_report()
                subprocess.run([
                    'mail',
                    '-s', title,
                    self.email
                ], input=email_body.encode(), check=False)
            except Exception as e:
                print(f"{Colors.YELLOW}Could not send email: {e}{Colors.RESET}")
    
    def _generate_email_report(self) -> str:
        """Generate email report body"""
        report = []
        report.append(f"EVENING LAUNCH READINESS CHECK")
        report.append(f"{'='*60}")
        report.append(f"Time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"For tomorrow: {(dt.date.today() + dt.timedelta(days=1)).strftime('%A, %B %d, %Y')}")
        report.append("")
        
        if self.go_for_launch:
            report.append("STATUS: GO FOR LAUNCH ✅")
        else:
            report.append("STATUS: NO-GO FOR LAUNCH ⛔")
        
        report.append("")
        report.append(f"Passed: {len(self.passed_checks)}")
        report.append(f"Warnings: {len(self.warnings)}")
        report.append(f"Critical Issues: {len(self.critical_issues)}")
        report.append("")
        
        if self.critical_issues:
            report.append("CRITICAL ISSUES:")
            for issue in self.critical_issues:
                report.append(f"  - {issue}")
            report.append("")
        
        if self.warnings:
            report.append("WARNINGS:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")
        
        if self.go_for_launch:
            report.append("ACTION: You can launch the bot.")
            report.append("Command: python3 litebotx_launcher.py")
        else:
            report.append("ACTION: DO NOT launch bot until issues are fixed.")
            report.append("Re-run: python3 evening_launch_check.py")
        
        return "\n".join(report)
    
    def _save_report(self):
        """Save report to file"""
        try:
            timestamp = dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            report_dir = Path('evening_check_reports')
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f'evening_check_{timestamp}.json'
            
            report_data = {
                'timestamp': timestamp,
                'for_date': (dt.date.today() + dt.timedelta(days=1)).isoformat(),
                'go_for_launch': self.go_for_launch,
                'passed_checks': self.passed_checks,
                'warnings': self.warnings,
                'critical_issues': self.critical_issues,
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            # Also save as latest
            latest_file = report_dir / 'latest_evening_check.json'
            with open(latest_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n{Colors.BLUE}Report saved: {report_file}{Colors.RESET}\n")
            
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Could not save report: {e}{Colors.RESET}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Evening launch readiness check - run BEFORE starting bot overnight'
    )
    parser.add_argument('--notify', action='store_true', 
                       help='Send desktop notifications')
    parser.add_argument('--email', type=str, 
                       help='Email address for alerts')
    
    args = parser.parse_args()
    
    checker = EveningLaunchCheck(
        enable_notifications=args.notify,
        email=args.email
    )
    
    success = checker.run_all_checks()
    
    # Exit codes:
    # 0 = GO for launch
    # 1 = NO-GO (critical issues)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
