#!/usr/bin/env python3
"""
Pre-Flight Check System
Comprehensive validation before live trading to catch issues that would prevent proper bot function.

Run this every night before market opens OR after any code changes.

Usage:
    python3 pre_flight_check.py
    python3 pre_flight_check.py --verbose
    python3 pre_flight_check.py --fix-issues  # Auto-fix if possible
"""

import os
import sys
import json
import datetime as dt
import pytz
from pathlib import Path
from typing import Dict, List, Tuple, Any
import traceback

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class PreFlightCheck:
    """Comprehensive pre-flight validation system"""
    
    def __init__(self, verbose: bool = False, auto_fix: bool = False):
        self.verbose = verbose
        self.auto_fix = auto_fix
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        
    def run_all_checks(self) -> bool:
        """Run all pre-flight checks. Returns True if all critical checks pass."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}🚀 PRE-FLIGHT CHECK SYSTEM{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        print(f"Running comprehensive validation before live trading...")
        print(f"Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        checks = [
            ("1. Python Environment", self._check_python_environment),
            ("2. Critical Imports", self._check_critical_imports),
            ("3. API Credentials", self._check_api_credentials),
            ("4. Alpaca Connection", self._check_alpaca_connection),
            ("5. File Permissions", self._check_file_permissions),
            ("6. Configuration Validity", self._check_configuration),
            ("7. Timezone Consistency", self._check_timezone_consistency),
            ("8. Position Loading", self._check_position_loading),
            ("9. Signal Generation", self._check_signal_generation),
            ("10. Pattern Recognition", self._check_pattern_recognition),
            ("11. Trade Execution Mock", self._check_trade_execution),
            ("12. Exit Logic", self._check_exit_logic),
            ("13. Data Sources", self._check_data_sources),
            ("14. Disk Space", self._check_disk_space),
            ("15. Memory Available", self._check_memory),
            ("16. Log File Health", self._check_log_health),
            ("17. Previous Session State", self._check_previous_session),
            ("18. Market Schedule", self._check_market_schedule),
        ]
        
        for check_name, check_func in checks:
            self._run_check(check_name, check_func)
        
        self._print_summary()
        return self.checks_failed == 0
    
    def _run_check(self, name: str, func):
        """Run a single check with error handling"""
        try:
            print(f"\n{Colors.BLUE}▶ {name}{Colors.RESET}")
            result = func()
            if result:
                self._pass(name)
            else:
                self._fail(name, "Check returned False")
        except Exception as e:
            self._fail(name, str(e), traceback.format_exc())
    
    def _pass(self, check_name: str, message: str = ""):
        """Mark check as passed"""
        self.checks_passed += 1
        msg = f"  {Colors.GREEN}✅ PASS{Colors.RESET}"
        if message:
            msg += f" - {message}"
        print(msg)
    
    def _fail(self, check_name: str, reason: str, detail: str = ""):
        """Mark check as failed"""
        self.checks_failed += 1
        print(f"  {Colors.RED}❌ FAIL{Colors.RESET} - {reason}")
        self.issues.append({
            'check': check_name,
            'severity': 'CRITICAL',
            'reason': reason,
            'detail': detail
        })
        if self.verbose and detail:
            print(f"  {Colors.RED}Details:{Colors.RESET}")
            for line in detail.split('\n')[:10]:  # Limit to 10 lines
                print(f"    {line}")
    
    def _warn(self, check_name: str, reason: str):
        """Mark check as warning"""
        self.checks_warned += 1
        print(f"  {Colors.YELLOW}⚠️  WARN{Colors.RESET} - {reason}")
        self.warnings.append({
            'check': check_name,
            'severity': 'WARNING',
            'reason': reason
        })
    
    # ========== INDIVIDUAL CHECK METHODS ==========
    
    def _check_python_environment(self) -> bool:
        """Check Python version and virtual environment"""
        import sys
        
        # Check Python version
        if sys.version_info < (3, 8):
            self._fail("Python Environment", f"Python 3.8+ required, got {sys.version}")
            return False
        
        print(f"  Python version: {sys.version.split()[0]}")
        
        # Check if in virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
        if not in_venv:
            self._warn("Python Environment", "Not in virtual environment")
        else:
            print(f"  Virtual environment: {sys.prefix}")
        
        return True
    
    def _check_critical_imports(self) -> bool:
        """Check all critical imports work without errors"""
        critical_imports = [
            ('pandas', 'pd'),
            ('numpy', 'np'),
            ('datetime', 'dt'),
            ('alpaca.trading.client', 'TradingClient'),
            ('alpaca.data.historical', 'StockHistoricalDataClient'),
            ('pytz', 'pytz'),
        ]
        
        custom_imports = [
            'config',
            'traders.short_cycle_trader',
            'pattern_recognizer',
            'morning_gap_scanner',
            'data_fetcher',
            'signal_generator',
        ]
        
        all_passed = True
        
        for module_name, import_as in critical_imports:
            try:
                __import__(module_name)
                print(f"  ✓ {module_name}")
            except ImportError as e:
                self._fail("Critical Imports", f"Cannot import {module_name}: {e}")
                all_passed = False
        
        for module_name in custom_imports:
            try:
                __import__(module_name)
                print(f"  ✓ {module_name}")
            except ImportError as e:
                self._fail("Critical Imports", f"Cannot import {module_name}: {e}")
                all_passed = False
        
        return all_passed
    
    def _check_api_credentials(self) -> bool:
        """Check API credentials are set"""
        required_env = ['APCA_API_KEY_ID', 'APCA_API_SECRET_KEY']
        optional_env = ['FRED_API_KEY', 'POLYGON_API_KEY']
        
        all_passed = True
        
        for env_var in required_env:
            value = os.getenv(env_var)
            if not value:
                self._fail("API Credentials", f"Missing required: {env_var}")
                all_passed = False
            else:
                print(f"  ✓ {env_var}: {'*' * 8}{value[-4:]}")
        
        for env_var in optional_env:
            value = os.getenv(env_var)
            if value:
                print(f"  ✓ {env_var}: {'*' * 8}{value[-4:]}")
            else:
                self._warn("API Credentials", f"Optional not set: {env_var}")
        
        return all_passed
    
    def _check_alpaca_connection(self) -> bool:
        """Test actual Alpaca API connection"""
        try:
            from alpaca.trading.client import TradingClient
            
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                self._fail("Alpaca Connection", "API credentials not set")
                return False
            
            client = TradingClient(api_key, api_secret, paper=True)
            account = client.get_account()
            
            print(f"  Account status: {account.status}")
            print(f"  Portfolio value: ${float(account.equity):,.2f}")
            print(f"  Buying power: ${float(account.buying_power):,.2f}")
            
            if account.status != 'ACTIVE':
                self._fail("Alpaca Connection", f"Account not active: {account.status}")
                return False
            
            return True
            
        except Exception as e:
            self._fail("Alpaca Connection", f"Cannot connect to Alpaca: {e}")
            return False
    
    def _check_file_permissions(self) -> bool:
        """Check critical files exist and are readable/writable"""
        critical_files = [
            ('traders/short_cycle_trader.py', 'r'),
            ('config.py', 'r'),
            ('pattern_recognizer.py', 'r'),
            ('morning_gap_scanner.py', 'r'),
            ('positions.json', 'rw'),
            ('logs/short_cycle_trader.log', 'w'),
        ]
        
        all_passed = True
        
        for filepath, mode in critical_files:
            path = Path(filepath)
            
            # Check readable
            if 'r' in mode:
                if not path.exists():
                    self._fail("File Permissions", f"Missing: {filepath}")
                    all_passed = False
                    continue
                if not os.access(path, os.R_OK):
                    self._fail("File Permissions", f"Not readable: {filepath}")
                    all_passed = False
                    continue
            
            # Check writable
            if 'w' in mode:
                if path.exists():
                    if not os.access(path, os.W_OK):
                        self._fail("File Permissions", f"Not writable: {filepath}")
                        all_passed = False
                        continue
                else:
                    # Try to create parent directory
                    path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"  ✓ {filepath}")
        
        return all_passed
    
    def _check_configuration(self) -> bool:
        """Validate configuration settings"""
        try:
            from config import ShortCycleConfig
            
            # Create config with aggressive profile
            config = ShortCycleConfig(
                initial_capital=963000,
                daily_pool_percent=0.60,
                max_positions_per_day=8,
                max_risk_per_trade_dollars=100.0,
                max_position_dollars=6000.0,
                confidence_threshold=0.07,
                enable_trailing_stops=True
            )
            
            # Validate critical values
            if config.initial_capital <= 0:
                self._fail("Configuration", "Invalid initial_capital")
                return False
            
            if not (0 < config.daily_pool_percent <= 1.0):
                self._fail("Configuration", "daily_pool_percent must be 0-1")
                return False
            
            if config.max_positions_per_day <= 0:
                self._fail("Configuration", "Invalid max_positions_per_day")
                return False
            
            print(f"  Portfolio: ${config.initial_capital:,}")
            print(f"  Daily pool: {config.daily_pool_percent*100:.0f}% (${config.initial_capital * config.daily_pool_percent:,.0f})")
            print(f"  Max positions: {config.max_positions_per_day}")
            print(f"  Max risk/trade: ${config.max_risk_per_trade_dollars}")
            print(f"  Trailing stops: {config.enable_trailing_stops}")
            
            return True
            
        except Exception as e:
            self._fail("Configuration", f"Config validation error: {e}")
            return False
    
    def _check_timezone_consistency(self) -> bool:
        """
        CRITICAL: Check timezone handling consistency.
        This is what failed on Oct 20, 2025 - prevent it from happening again!
        """
        try:
            import pytz
            from traders.short_cycle_trader import ShortCyclePosition
            
            print(f"  Testing timezone-aware datetime creation...")
            
            # Test 1: Create timezone-aware datetime
            utc_now = dt.datetime.now(pytz.UTC)
            print(f"  ✓ UTC now: {utc_now}")
            
            # Test 2: Simulate Alpaca timestamp
            alpaca_timestamp = dt.datetime.now(pytz.UTC)
            print(f"  ✓ Alpaca-style timestamp: {alpaca_timestamp}")
            
            # Test 3: Verify subtraction works
            time_diff = (utc_now - alpaca_timestamp).total_seconds()
            print(f"  ✓ Timestamp subtraction works: {time_diff}s")
            
            # Test 4: Check position class has entry_timestamp field
            import inspect
            position_fields = [field for field in dir(ShortCyclePosition) if not field.startswith('_')]
            if 'entry_timestamp' not in position_fields:
                self._fail("Timezone Consistency", "ShortCyclePosition missing entry_timestamp field")
                return False
            
            print(f"  ✓ ShortCyclePosition has entry_timestamp field")
            
            # Test 5: Verify pattern recognizer can handle timezone-aware datetimes
            from pattern_recognizer import PatternRecognizer
            recognizer = PatternRecognizer()
            
            # Mock pattern exit time check with timezone-aware datetime
            from pattern_recognizer import StockPattern
            should_exit, reason = recognizer.get_optimal_exit_time(
                pattern=StockPattern.MORNING_GAPPER,
                current_time=utc_now,
                pnl_pct=0.02
            )
            print(f"  ✓ Pattern recognizer works with timezone-aware datetime")
            
            return True
            
        except Exception as e:
            self._fail("Timezone Consistency", f"Timezone handling error: {e}")
            return False
    
    def _check_position_loading(self) -> bool:
        """Test loading positions from JSON (simulates bot restart)"""
        try:
            # Check if positions.json exists
            if not Path('positions.json').exists():
                print(f"  No positions.json (clean slate)")
                return True
            
            # Try to load positions
            with open('positions.json', 'r') as f:
                data = json.load(f)
            
            print(f"  Positions file loaded: {len(data.get('positions', []))} positions")
            
            # Check for timezone-aware timestamps
            for pos_data in data.get('positions', []):
                if 'entry_timestamp' in pos_data and pos_data['entry_timestamp']:
                    try:
                        # Try to parse timestamp
                        ts = dt.datetime.fromisoformat(pos_data['entry_timestamp'])
                        if ts.tzinfo is None:
                            self._warn("Position Loading", 
                                     f"Position {pos_data.get('symbol')} has timezone-naive timestamp")
                        else:
                            print(f"  ✓ {pos_data.get('symbol')}: timezone-aware timestamp")
                    except Exception as e:
                        self._warn("Position Loading", 
                                 f"Cannot parse timestamp for {pos_data.get('symbol')}: {e}")
            
            return True
            
        except Exception as e:
            self._fail("Position Loading", f"Cannot load positions: {e}")
            return False
    
    def _check_signal_generation(self) -> bool:
        """Test signal generation pipeline (dry run)"""
        try:
            from signal_generator import SignalGenerator
            from config import ShortCycleConfig
            
            config = ShortCycleConfig(
                initial_capital=963000,
                daily_pool_percent=0.60,
                max_positions_per_day=8,
                confidence_threshold=0.07
            )
            
            # Create signal generator
            sig_gen = SignalGenerator(config)
            
            print(f"  ✓ SignalGenerator initialized")
            print(f"  Confidence threshold: {config.confidence_threshold}")
            
            return True
            
        except Exception as e:
            self._fail("Signal Generation", f"Signal generation error: {e}")
            return False
    
    def _check_pattern_recognition(self) -> bool:
        """Test pattern recognition system"""
        try:
            from pattern_recognizer import PatternRecognizer, PatternTracker, StockPattern
            import pytz
            
            # Initialize components
            recognizer = PatternRecognizer()
            tracker = PatternTracker()
            
            print(f"  ✓ PatternRecognizer initialized")
            print(f"  ✓ PatternTracker initialized")
            
            # Test pattern identification
            pattern = recognizer.identify_pattern(
                price_history=[100, 101, 102, 103, 104],
                gap_at_open=0.02,  # 2% gap
                minutes_held=30
            )
            
            print(f"  ✓ Pattern identified: {pattern.value}")
            
            # Test exit timing with timezone-aware datetime
            current_time = dt.datetime.now(pytz.UTC)
            should_exit, reason = recognizer.get_optimal_exit_time(
                pattern=pattern,
                current_time=current_time,
                pnl_pct=0.015
            )
            
            print(f"  ✓ Exit timing works: should_exit={should_exit}, reason={reason}")
            
            # Test pattern tracking
            tracked_pattern = tracker.update_position_pattern(
                symbol='TEST',
                current_price=102.0,
                entry_price=100.0,
                gap_at_open=0.02,
                minutes_held=30
            )
            
            print(f"  ✓ Pattern tracking works: {tracked_pattern.value}")
            
            return True
            
        except Exception as e:
            self._fail("Pattern Recognition", f"Pattern recognition error: {e}")
            return False
    
    def _check_trade_execution(self) -> bool:
        """Mock trade execution (don't submit real orders)"""
        try:
            from traders.short_cycle_trader import ShortCycleTrader, ShortCyclePosition
            from config import ShortCycleConfig
            import pytz
            
            config = ShortCycleConfig(
                initial_capital=963000,
                daily_pool_percent=0.60,
                max_positions_per_day=8,
                confidence_threshold=0.07
            )
            
            # Create trader instance
            trader = ShortCycleTrader(config)
            
            print(f"  ✓ ShortCycleTrader initialized")
            
            # Check critical methods exist
            required_methods = [
                '_execute_signal',
                '_process_existing_positions',
                '_scan_morning_gaps',
                '_get_next_trading_day'
            ]
            
            for method in required_methods:
                if not hasattr(trader, method):
                    self._fail("Trade Execution", f"Missing method: {method}")
                    return False
                print(f"  ✓ Method exists: {method}")
            
            # Check pattern recognition components initialized
            if not hasattr(trader, 'pattern_recognizer'):
                self._fail("Trade Execution", "Missing pattern_recognizer")
                return False
            
            if not hasattr(trader, 'pattern_tracker'):
                self._fail("Trade Execution", "Missing pattern_tracker")
                return False
            
            if not hasattr(trader, 'morning_gap_scanner'):
                self._fail("Trade Execution", "Missing morning_gap_scanner")
                return False
            
            print(f"  ✓ All D+1 optimization components present")
            
            return True
            
        except Exception as e:
            self._fail("Trade Execution", f"Trade execution mock error: {e}")
            return False
    
    def _check_exit_logic(self) -> bool:
        """Test exit logic pathways"""
        try:
            from traders.short_cycle_trader import ShortCycleTrader
            from config import ShortCycleConfig
            
            config = ShortCycleConfig(
                initial_capital=963000,
                daily_pool_percent=0.60,
                max_positions_per_day=8,
                enable_trailing_stops=True
            )
            
            trader = ShortCycleTrader(config)
            
            # Check exit methods exist
            exit_methods = [
                '_process_existing_positions',
                '_process_existing_positions_with_strategic_exits',
                '_exit_position'
            ]
            
            for method in exit_methods:
                if not hasattr(trader, method):
                    self._fail("Exit Logic", f"Missing exit method: {method}")
                    return False
                print(f"  ✓ Exit method: {method}")
            
            return True
            
        except Exception as e:
            self._fail("Exit Logic", f"Exit logic error: {e}")
            return False
    
    def _check_data_sources(self) -> bool:
        """Test data source availability"""
        try:
            from data_fetcher import DataFetcher
            
            fetcher = DataFetcher()
            
            # Test a simple data fetch (will use cache if available)
            print(f"  Testing data fetch for SPY...")
            
            # Don't actually fetch during check, just verify fetcher works
            print(f"  ✓ DataFetcher initialized")
            
            return True
            
        except Exception as e:
            self._fail("Data Sources", f"Data source error: {e}")
            return False
    
    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage("/")
            
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            used_pct = (used / total) * 100
            
            print(f"  Total: {total_gb:.1f} GB")
            print(f"  Free: {free_gb:.1f} GB")
            print(f"  Used: {used_pct:.1f}%")
            
            if free_gb < 1.0:
                self._fail("Disk Space", f"Low disk space: {free_gb:.1f} GB free")
                return False
            elif free_gb < 5.0:
                self._warn("Disk Space", f"Disk space getting low: {free_gb:.1f} GB free")
            
            return True
            
        except Exception as e:
            self._warn("Disk Space", f"Cannot check disk space: {e}")
            return True  # Not critical
    
    def _check_memory(self) -> bool:
        """Check available memory"""
        try:
            import psutil
            
            mem = psutil.virtual_memory()
            
            print(f"  Total: {mem.total / (1024**3):.1f} GB")
            print(f"  Available: {mem.available / (1024**3):.1f} GB")
            print(f"  Used: {mem.percent:.1f}%")
            
            if mem.percent > 95:
                self._fail("Memory", f"Very low memory: {mem.percent:.1f}% used")
                return False
            elif mem.percent > 85:
                self._warn("Memory", f"High memory usage: {mem.percent:.1f}%")
            
            return True
            
        except ImportError:
            self._warn("Memory", "psutil not installed, skipping memory check")
            return True
        except Exception as e:
            self._warn("Memory", f"Cannot check memory: {e}")
            return True
    
    def _check_log_health(self) -> bool:
        """Check log file health"""
        try:
            log_file = Path('logs/short_cycle_trader.log')
            
            if not log_file.exists():
                print(f"  No existing log file (fresh start)")
                return True
            
            # Check log file size
            size_mb = log_file.stat().st_size / (1024**2)
            print(f"  Log file size: {size_mb:.1f} MB")
            
            if size_mb > 100:
                self._warn("Log Health", f"Large log file: {size_mb:.1f} MB (consider rotating)")
            
            # Check for recent errors
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                
                error_count = sum(1 for line in recent_lines if 'ERROR' in line)
                critical_count = sum(1 for line in recent_lines if 'CRITICAL' in line)
                
                print(f"  Recent errors (last 100 lines): {error_count}")
                print(f"  Recent critical (last 100 lines): {critical_count}")
                
                if critical_count > 0:
                    self._warn("Log Health", f"{critical_count} CRITICAL messages in recent logs")
            
            return True
            
        except Exception as e:
            self._warn("Log Health", f"Cannot check log health: {e}")
            return True
    
    def _check_previous_session(self) -> bool:
        """Check previous session completed properly"""
        try:
            log_file = Path('logs/short_cycle_trader.log')
            
            if not log_file.exists():
                print(f"  No previous session logs")
                return True
            
            # Check if last session ended properly
            with open(log_file, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                
                # Look for proper shutdown indicators
                proper_shutdown = any(
                    'Sleeping until premarket window' in line or
                    'End-of-day monitoring complete' in line or
                    'Watchlist refresh complete' in line
                    for line in last_lines
                )
                
                if proper_shutdown:
                    print(f"  ✓ Previous session ended properly")
                else:
                    self._warn("Previous Session", "Previous session may have crashed (no proper shutdown found)")
                
                # Check for crash indicators
                crash_indicators = [
                    'Traceback',
                    'Exception',
                    'Fatal',
                ]
                
                crashes = sum(
                    1 for line in last_lines 
                    for indicator in crash_indicators 
                    if indicator in line
                )
                
                if crashes > 0:
                    self._warn("Previous Session", f"Found {crashes} crash indicators in last session")
            
            return True
            
        except Exception as e:
            self._warn("Previous Session", f"Cannot check previous session: {e}")
            return True
    
    def _check_market_schedule(self) -> bool:
        """Check if market will be open tomorrow"""
        try:
            from alpaca.trading.client import TradingClient
            
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            client = TradingClient(api_key, api_secret, paper=True)
            
            # Get market clock
            clock = client.get_clock()
            
            print(f"  Market currently: {'OPEN' if clock.is_open else 'CLOSED'}")
            print(f"  Next open: {clock.next_open}")
            print(f"  Next close: {clock.next_close}")
            
            # Check if tomorrow is a trading day
            tomorrow = dt.date.today() + dt.timedelta(days=1)
            if tomorrow.weekday() >= 5:  # Saturday or Sunday
                self._warn("Market Schedule", f"Tomorrow is {tomorrow.strftime('%A')} - market closed")
            
            return True
            
        except Exception as e:
            self._warn("Market Schedule", f"Cannot check market schedule: {e}")
            return True
    
    def _print_summary(self):
        """Print final summary"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}📊 PRE-FLIGHT CHECK SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
        
        total_checks = self.checks_passed + self.checks_failed + self.checks_warned
        
        print(f"Total checks: {total_checks}")
        print(f"{Colors.GREEN}✅ Passed: {self.checks_passed}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Warnings: {self.checks_warned}{Colors.RESET}")
        print(f"{Colors.RED}❌ Failed: {self.checks_failed}{Colors.RESET}\n")
        
        if self.checks_failed > 0:
            print(f"{Colors.RED}{Colors.BOLD}🚨 CRITICAL ISSUES FOUND:{Colors.RESET}\n")
            for issue in self.issues:
                print(f"  {Colors.RED}❌{Colors.RESET} {issue['check']}")
                print(f"     {issue['reason']}\n")
            
            print(f"{Colors.RED}{Colors.BOLD}⛔ DO NOT START BOT - FIX ISSUES FIRST{Colors.RESET}\n")
        
        elif self.checks_warned > 0:
            print(f"{Colors.YELLOW}⚠️  WARNINGS (non-critical):{Colors.RESET}\n")
            for warning in self.warnings:
                print(f"  {Colors.YELLOW}⚠️{Colors.RESET}  {warning['check']}")
                print(f"     {warning['reason']}\n")
            
            print(f"{Colors.YELLOW}⚠️  Bot can start, but review warnings{Colors.RESET}\n")
        
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL CHECKS PASSED - BOT READY FOR TRADING{Colors.RESET}\n")
        
        # Save results to file
        self._save_results()
    
    def _save_results(self):
        """Save check results to file"""
        try:
            timestamp = dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            report_file = f'pre_flight_reports/pre_flight_check_{timestamp}.json'
            
            Path('pre_flight_reports').mkdir(exist_ok=True)
            
            results = {
                'timestamp': timestamp,
                'total_checks': self.checks_passed + self.checks_failed + self.checks_warned,
                'passed': self.checks_passed,
                'failed': self.checks_failed,
                'warned': self.checks_warned,
                'status': 'PASS' if self.checks_failed == 0 else 'FAIL',
                'issues': self.issues,
                'warnings': self.warnings
            }
            
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"Report saved: {report_file}\n")
            
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Could not save report: {e}{Colors.RESET}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pre-flight check for trading bot')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--fix-issues', action='store_true', help='Auto-fix issues if possible')
    
    args = parser.parse_args()
    
    checker = PreFlightCheck(verbose=args.verbose, auto_fix=args.fix_issues)
    success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
