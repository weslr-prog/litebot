#!/usr/bin/env python3
"""
PDT Compliance Auditor
======================
Post-trade audit system that scans positions.json for PDT violations
and generates detailed reports with auto-correction triggers.

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path


@dataclass
class PDTViolation:
    """Represents a detected PDT violation"""
    symbol: str
    violation_date: str
    violation_type: str  # 'same_day_exit', 'multiple_entries', 'rapid_reentry'
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM'
    entry_timestamp: Optional[str] = None
    exit_timestamp: Optional[str] = None
    entry_count: int = 1
    details: str = ""
    
    def to_dict(self):
        return asdict(self)


class PDTAuditor:
    """
    Comprehensive PDT violation detection and reporting system.
    Scans completed trades and identifies patterns that violate PDT rules.
    """
    
    def __init__(self, positions_file: str = "positions.json", 
                 report_dir: str = "monitoring/reports/pdt"):
        self.positions_file = positions_file
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Violation thresholds
        self.max_same_day_entries = 0  # Zero tolerance - strict D+1
        self.min_hold_days = 1  # Must hold at least 1 day
        self.reentry_cooldown_hours = 12  # Minimum time between exit and re-entry
        
    def audit_daily_trades(self, trade_date: Optional[str] = None) -> Dict:
        """
        Audit all trades for a specific date for PDT compliance.
        
        Args:
            trade_date: Date to audit in YYYY-MM-DD format. Defaults to today.
            
        Returns:
            Dict containing audit results and violations found
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        
        self.logger.info(f"🔍 Starting PDT audit for {trade_date}")
        
        # Load positions
        positions = self._load_positions()
        
        # Filter to relevant date
        daily_positions = self._filter_by_date(positions, trade_date)
        
        # Run violation checks
        violations = []
        violations.extend(self._check_same_day_exits(daily_positions))
        violations.extend(self._check_multiple_entries(daily_positions))
        violations.extend(self._check_rapid_reentry(positions, trade_date))
        
        # Generate report
        audit_report = {
            'audit_date': trade_date,
            'audit_timestamp': datetime.now().isoformat(),
            'positions_checked': len(daily_positions),
            'violations_found': len(violations),
            'violations': [v.to_dict() for v in violations],
            'compliance_status': 'PASS' if len(violations) == 0 else 'FAIL',
            'critical_violations': sum(1 for v in violations if v.severity == 'CRITICAL'),
            'recommendations': self._generate_recommendations(violations)
        }
        
        # Save report
        self._save_report(audit_report, trade_date)
        
        # Log summary
        self._log_audit_summary(audit_report)
        
        # Trigger auto-correction if needed
        if audit_report['critical_violations'] > 0:
            self._trigger_emergency_mode(audit_report)
        
        return audit_report
    
    def _load_positions(self) -> List[Dict]:
        """Load positions from JSON file"""
        try:
            if not os.path.exists(self.positions_file):
                self.logger.warning(f"Positions file not found: {self.positions_file}")
                return []
            
            with open(self.positions_file, 'r') as f:
                positions = json.load(f)
            
            return positions if isinstance(positions, list) else []
        
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            return []
    
    def _filter_by_date(self, positions: List[Dict], trade_date: str) -> List[Dict]:
        """Filter positions that were active on the given date"""
        daily = []
        
        for pos in positions:
            entry_date = pos.get('entry_date', '')
            exit_date = pos.get('exit_date', '')
            
            # Include if entered or exited on this date
            if entry_date == trade_date or exit_date == trade_date:
                daily.append(pos)
        
        return daily
    
    def _check_same_day_exits(self, positions: List[Dict]) -> List[PDTViolation]:
        """Check for positions that were entered and exited on the same day"""
        violations = []
        
        for pos in positions:
            entry_date = pos.get('entry_date')
            exit_timestamp = pos.get('exit_timestamp')
            
            if not entry_date or not exit_timestamp:
                continue
            
            # Extract date from exit timestamp
            exit_date = exit_timestamp.split('T')[0] if 'T' in exit_timestamp else exit_timestamp
            
            if entry_date == exit_date:
                violation = PDTViolation(
                    symbol=pos.get('symbol', 'UNKNOWN'),
                    violation_date=entry_date,
                    violation_type='same_day_exit',
                    severity='CRITICAL',
                    entry_timestamp=pos.get('entry_timestamp'),
                    exit_timestamp=exit_timestamp,
                    details=f"Position entered and exited on same day {entry_date}. "
                            f"Entry: {pos.get('entry_timestamp', 'N/A')}, "
                            f"Exit: {exit_timestamp}. "
                            f"Exit reason: {pos.get('exit_reason', 'N/A')}"
                )
                violations.append(violation)
                
                self.logger.critical(
                    f"🚨 PDT VIOLATION: {pos.get('symbol')} same-day exit on {entry_date}"
                )
        
        return violations
    
    def _check_multiple_entries(self, positions: List[Dict]) -> List[PDTViolation]:
        """Check for multiple entries of the same symbol on the same day"""
        # Group by symbol and entry_date
        entries_by_symbol_date = defaultdict(list)
        
        for pos in positions:
            symbol = pos.get('symbol')
            entry_date = pos.get('entry_date')
            
            if symbol and entry_date:
                key = f"{symbol}_{entry_date}"
                entries_by_symbol_date[key].append(pos)
        
        violations = []
        
        for key, entries in entries_by_symbol_date.items():
            if len(entries) > 1:
                symbol, entry_date = key.rsplit('_', 1)
                
                violation = PDTViolation(
                    symbol=symbol,
                    violation_date=entry_date,
                    violation_type='multiple_entries',
                    severity='CRITICAL',
                    entry_count=len(entries),
                    details=f"Multiple entries ({len(entries)}) for {symbol} on {entry_date}. "
                            f"Entry times: {', '.join(e.get('entry_timestamp', 'N/A') for e in entries)}"
                )
                violations.append(violation)
                
                self.logger.critical(
                    f"🚨 PDT VIOLATION: {symbol} has {len(entries)} entries on {entry_date}"
                )
        
        return violations
    
    def _check_rapid_reentry(self, positions: List[Dict], check_date: str) -> List[PDTViolation]:
        """Check for re-entries too soon after exits (within cooldown period)"""
        violations = []
        
        # Group positions by symbol
        by_symbol = defaultdict(list)
        for pos in positions:
            symbol = pos.get('symbol')
            if symbol:
                by_symbol[symbol].append(pos)
        
        for symbol, symbol_positions in by_symbol.items():
            # Sort by entry timestamp
            sorted_pos = sorted(
                symbol_positions,
                key=lambda p: p.get('entry_timestamp', ''),
                reverse=False
            )
            
            # Check for rapid re-entries
            for i in range(len(sorted_pos) - 1):
                current = sorted_pos[i]
                next_pos = sorted_pos[i + 1]
                
                exit_ts = current.get('exit_timestamp')
                next_entry_ts = next_pos.get('entry_timestamp')
                
                if not exit_ts or not next_entry_ts:
                    continue
                
                try:
                    exit_time = datetime.fromisoformat(exit_ts.replace('Z', '+00:00'))
                    entry_time = datetime.fromisoformat(next_entry_ts.replace('Z', '+00:00'))
                    
                    time_diff = (entry_time - exit_time).total_seconds() / 3600  # hours
                    
                    if 0 < time_diff < self.reentry_cooldown_hours:
                        # Check if this involves the audit date
                        exit_date = exit_ts.split('T')[0]
                        entry_date = next_entry_ts.split('T')[0]
                        
                        if exit_date == check_date or entry_date == check_date:
                            violation = PDTViolation(
                                symbol=symbol,
                                violation_date=check_date,
                                violation_type='rapid_reentry',
                                severity='HIGH',
                                exit_timestamp=exit_ts,
                                entry_timestamp=next_entry_ts,
                                details=f"Re-entry after {time_diff:.1f} hours (minimum: {self.reentry_cooldown_hours}h). "
                                        f"Exit: {exit_ts}, Re-entry: {next_entry_ts}"
                            )
                            violations.append(violation)
                            
                            self.logger.warning(
                                f"⚠️ PDT RISK: {symbol} re-entered after {time_diff:.1f}h "
                                f"(cooldown: {self.reentry_cooldown_hours}h)"
                            )
                
                except Exception as e:
                    self.logger.debug(f"Error parsing timestamps for {symbol}: {e}")
        
        return violations
    
    def _generate_recommendations(self, violations: List[PDTViolation]) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        if not violations:
            recommendations.append("✅ No PDT violations detected - system is compliant")
            return recommendations
        
        # Count violation types
        violation_types = defaultdict(int)
        for v in violations:
            violation_types[v.violation_type] += 1
        
        if violation_types['same_day_exit'] > 0:
            recommendations.append(
                f"🔧 CRITICAL: {violation_types['same_day_exit']} same-day exit(s) detected. "
                "Verify D+1 exit blocker is active in position monitoring loop."
            )
            recommendations.append(
                "   Action: Enable EMERGENCY_PDT_MODE to enforce strict 2-day hold minimum"
            )
        
        if violation_types['multiple_entries'] > 0:
            recommendations.append(
                f"🔧 CRITICAL: {violation_types['multiple_entries']} multiple entry violation(s). "
                "Verify entry blocker is checking _has_same_day_activity() before signal execution."
            )
            recommendations.append(
                "   Action: Enable single-entry-per-symbol-per-day enforcement"
            )
        
        if violation_types['rapid_reentry'] > 0:
            recommendations.append(
                f"⚠️ WARNING: {violation_types['rapid_reentry']} rapid re-entry violation(s). "
                f"Consider increasing cooldown period from {self.reentry_cooldown_hours}h to 24h."
            )
        
        # General recommendation if violations exist
        if len(violations) >= 3:
            recommendations.append(
                "🚨 EMERGENCY: Multiple violations detected - recommend halting trading "
                "until PDT protection is verified and tested"
            )
        
        return recommendations
    
    def _save_report(self, report: Dict, trade_date: str):
        """Save audit report to file"""
        filename = self.report_dir / f"pdt_audit_{trade_date}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"📄 Audit report saved: {filename}")
        
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
    
    def _log_audit_summary(self, report: Dict):
        """Log human-readable audit summary"""
        self.logger.info("=" * 60)
        self.logger.info(f"📊 PDT AUDIT SUMMARY - {report['audit_date']}")
        self.logger.info("=" * 60)
        self.logger.info(f"Positions Checked: {report['positions_checked']}")
        self.logger.info(f"Violations Found: {report['violations_found']}")
        self.logger.info(f"Critical Violations: {report['critical_violations']}")
        self.logger.info(f"Compliance Status: {report['compliance_status']}")
        
        if report['violations_found'] > 0:
            self.logger.warning("\n⚠️ VIOLATIONS DETECTED:")
            for v in report['violations']:
                self.logger.warning(f"  • {v['severity']}: {v['symbol']} - {v['violation_type']}")
                self.logger.warning(f"    {v['details']}")
        
        if report['recommendations']:
            self.logger.info("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                self.logger.info(f"  {rec}")
        
        self.logger.info("=" * 60)
    
    def _trigger_emergency_mode(self, report: Dict):
        """Trigger emergency PDT protection mode when violations detected"""
        self.logger.critical("🔒 TRIGGERING EMERGENCY PDT MODE")
        
        # Create emergency flag file
        flag_file = Path("monitoring/EMERGENCY_PDT_MODE.flag")
        flag_file.parent.mkdir(parents=True, exist_ok=True)
        
        flag_data = {
            'activated': datetime.now().isoformat(),
            'reason': f"{report['critical_violations']} critical PDT violations detected",
            'violations': report['violations'],
            'auto_recovery': False,
            'manual_override_required': True
        }
        
        with open(flag_file, 'w') as f:
            json.dump(flag_data, f, indent=2)
        
        self.logger.critical(f"🔒 Emergency flag created: {flag_file}")
        self.logger.critical("   Trading will be restricted until manual override")
    
    def generate_weekly_summary(self, start_date: Optional[str] = None) -> Dict:
        """
        Generate a weekly PDT compliance summary.
        
        Args:
            start_date: Start of week in YYYY-MM-DD format. Defaults to last Monday.
            
        Returns:
            Dict containing weekly summary statistics
        """
        if start_date is None:
            today = datetime.now()
            days_since_monday = today.weekday()
            start_date = (today - timedelta(days=days_since_monday)).strftime("%Y-%m-%d")
        
        self.logger.info(f"📊 Generating weekly PDT summary starting {start_date}")
        
        # Load positions
        positions = self._load_positions()
        
        # Filter to week
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        week_positions = []
        
        for pos in positions:
            entry_date = pos.get('entry_date', '')
            if entry_date:
                try:
                    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                    if start_dt <= entry_dt < start_dt + timedelta(days=7):
                        week_positions.append(pos)
                except:
                    pass
        
        # Analyze week
        total_violations = 0
        daily_summaries = []
        
        for day_offset in range(7):
            check_date = (start_dt + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            daily_audit = self.audit_daily_trades(check_date)
            total_violations += daily_audit['violations_found']
            
            daily_summaries.append({
                'date': check_date,
                'violations': daily_audit['violations_found'],
                'status': daily_audit['compliance_status']
            })
        
        weekly_summary = {
            'week_start': start_date,
            'week_end': (start_dt + timedelta(days=6)).strftime("%Y-%m-%d"),
            'total_positions': len(week_positions),
            'total_violations': total_violations,
            'daily_summaries': daily_summaries,
            'compliance_rate': (
                ((len(week_positions) - total_violations) / len(week_positions) * 100)
                if len(week_positions) > 0 else 100.0
            ),
            'overall_status': 'PASS' if total_violations == 0 else 'FAIL'
        }
        
        # Save weekly report
        week_file = self.report_dir / f"pdt_weekly_{start_date}.json"
        with open(week_file, 'w') as f:
            json.dump(weekly_summary, f, indent=2)
        
        self.logger.info(f"📄 Weekly summary saved: {week_file}")
        
        return weekly_summary


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run audit
    auditor = PDTAuditor()
    
    # Audit today
    print("\n🔍 Running daily PDT audit...")
    result = auditor.audit_daily_trades()
    
    print(f"\n{'='*60}")
    print(f"Audit complete: {result['compliance_status']}")
    print(f"Violations found: {result['violations_found']}")
    print(f"{'='*60}\n")
