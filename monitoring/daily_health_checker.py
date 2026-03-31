#!/usr/bin/env python3
"""
Daily Health Checker
====================
Comprehensive system health monitoring that tracks trading activity,
detects issues, and provides diagnostics for the trading bot.

Author: LiteBotX Self-Monitoring System
Date: October 5, 2025
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict


@dataclass
class HealthIssue:
    """Represents a detected health issue"""
    issue_type: str  # 'NO_TRADES', 'FILTER_FAILURE', 'HIGH_ERRORS', 'EXCESSIVE_BLOCKS'
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    message: str
    metric_value: float
    expected_value: float
    recommendations: List[str]
    auto_fixable: bool = False
    
    def to_dict(self):
        return asdict(self)


class DailyHealthChecker:
    """
    Comprehensive health monitoring system that analyzes daily trading activity
    and identifies potential issues before they become problems.
    """
    
    def __init__(self, 
                 positions_file: str = "positions.json",
                 log_file: str = "logs/short_cycle_trader.log",
                 report_dir: str = "monitoring/reports/health"):
        
        self.positions_file = positions_file
        self.log_file = log_file
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Health thresholds
        self.min_expected_positions = 5  # Expect at least 5 positions per day
        self.max_block_rate = 0.7  # Max 70% of signals blocked
        self.max_errors_per_day = 10
        self.min_prefilter_candidates = 10
        
    def run_daily_check(self, check_date: Optional[str] = None) -> Dict:
        """
        Run comprehensive daily health check.
        
        Args:
            check_date: Date to check in YYYY-MM-DD format. Defaults to today.
            
        Returns:
            Dict containing health report with issues and metrics
        """
        if check_date is None:
            check_date = datetime.now().strftime("%Y-%m-%d")
        
        self.logger.info(f"🏥 Starting daily health check for {check_date}")
        
        # Collect metrics
        metrics = self._collect_metrics(check_date)
        
        # Analyze for issues
        issues = self._analyze_metrics(metrics)
        
        # Generate report
        health_report = {
            'check_date': check_date,
            'check_timestamp': datetime.now().isoformat(),
            'overall_status': self._determine_overall_status(issues),
            'metrics': metrics,
            'issues_found': len(issues),
            'issues': [i.to_dict() for i in issues],
            'system_health_score': self._calculate_health_score(metrics, issues),
            'recommendations': self._generate_recommendations(issues, metrics)
        }
        
        # Save report
        self._save_report(health_report, check_date)
        
        # Log summary
        self._log_health_summary(health_report)
        
        return health_report
    
    def _collect_metrics(self, check_date: str) -> Dict:
        """Collect all relevant metrics for the day"""
        metrics = {
            'date': check_date,
            'positions_opened': 0,
            'positions_closed': 0,
            'signals_generated': 0,
            'signals_blocked': 0,
            'signals_executed': 0,
            'prefilter_candidates': 0,
            'prefilter_input_symbols': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'pdt_blocks': 0,
            'diversification_blocks': 0,
            'filter_failures': defaultdict(int),
            'exit_reasons': defaultdict(int),
            'api_errors': 0
        }
        
        # Analyze positions
        positions = self._load_positions()
        for pos in positions:
            if pos.get('entry_date') == check_date:
                metrics['positions_opened'] += 1
            
            exit_ts = pos.get('exit_timestamp', '')
            if exit_ts and exit_ts.startswith(check_date):
                metrics['positions_closed'] += 1
                exit_reason = pos.get('exit_reason', 'UNKNOWN')
                metrics['exit_reasons'][exit_reason] += 1
        
        # Analyze logs
        log_metrics = self._analyze_logs(check_date)
        metrics.update(log_metrics)
        
        # Calculate derived metrics
        total_signals = metrics['signals_generated']
        if total_signals > 0:
            metrics['block_rate'] = metrics['signals_blocked'] / total_signals
            metrics['execution_rate'] = metrics['signals_executed'] / total_signals
        else:
            metrics['block_rate'] = 0.0
            metrics['execution_rate'] = 0.0
        
        return metrics
    
    def _load_positions(self) -> List[Dict]:
        """Load positions from JSON file"""
        try:
            if not os.path.exists(self.positions_file):
                return []
            
            with open(self.positions_file, 'r') as f:
                positions = json.load(f)
            
            return positions if isinstance(positions, list) else []
        
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            return []
    
    def _analyze_logs(self, check_date: str) -> Dict:
        """Extract metrics from log file"""
        metrics = {
            'signals_generated': 0,
            'signals_blocked': 0,
            'signals_executed': 0,
            'prefilter_candidates': 0,
            'prefilter_input_symbols': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'pdt_blocks': 0,
            'diversification_blocks': 0,
            'api_errors': 0
        }
        
        if not os.path.exists(self.log_file):
            self.logger.warning(f"Log file not found: {self.log_file}")
            return metrics
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    # Only process lines from check_date
                    if check_date not in line:
                        continue
                    
                    # Count signals
                    if 'Signal generated' in line or 'Processing signal' in line:
                        metrics['signals_generated'] += 1
                    
                    if 'Entered position' in line:
                        metrics['signals_executed'] += 1
                    
                    # Count blocks
                    if 'skipped - same-day buy/sell prevention' in line:
                        metrics['signals_blocked'] += 1
                        metrics['pdt_blocks'] += 1
                    
                    if 'concentration limit' in line or 'diversification' in line:
                        metrics['signals_blocked'] += 1
                        metrics['diversification_blocks'] += 1
                    
                    # Pre-filter results
                    if 'Selected universe of' in line or 'universe selected:' in line:
                        try:
                            # Extract number
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.isdigit() and i > 0:
                                    metrics['prefilter_candidates'] = int(part)
                                    break
                        except:
                            pass
                    
                    if 'PRE-FILTER SUMMARY' in line or 'Input:' in line:
                        try:
                            # Extract input symbol count
                            if 'Input:' in line:
                                num = line.split('Input:')[1].split()[0]
                                metrics['prefilter_input_symbols'] = int(num)
                        except:
                            pass
                    
                    # Count errors and warnings
                    if 'ERROR' in line:
                        metrics['errors_count'] += 1
                        if 'API' in line or 'api' in line:
                            metrics['api_errors'] += 1
                    
                    if 'WARNING' in line or 'WARN' in line:
                        metrics['warnings_count'] += 1
        
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {e}")
        
        return metrics
    
    def _analyze_metrics(self, metrics: Dict) -> List[HealthIssue]:
        """Analyze metrics and identify issues"""
        issues = []
        
        # Issue 1: No trades
        if metrics['positions_opened'] == 0:
            issue = HealthIssue(
                issue_type='NO_TRADES',
                severity='HIGH',
                message='No positions opened today',
                metric_value=0,
                expected_value=self.min_expected_positions,
                recommendations=[
                    'Check pre-filter results - may be rejecting all candidates',
                    'Verify market data availability',
                    'Review filter thresholds (may be too strict)',
                    'Check if emergency stop or kill switches are active'
                ],
                auto_fixable=True
            )
            issues.append(issue)
        
        # Issue 2: Very low pre-filter output
        if metrics['prefilter_candidates'] < self.min_prefilter_candidates:
            issue = HealthIssue(
                issue_type='FILTER_FAILURE',
                severity='CRITICAL' if metrics['prefilter_candidates'] == 0 else 'HIGH',
                message=f'Pre-filter returned only {metrics["prefilter_candidates"]} candidates',
                metric_value=metrics['prefilter_candidates'],
                expected_value=self.min_prefilter_candidates,
                recommendations=[
                    'Check data completeness filter (may need to reduce min_rows)',
                    'Review liquidity filter thresholds',
                    'Verify market data is available (free tier limitations)',
                    'Consider relaxing momentum/volatility filters'
                ],
                auto_fixable=True
            )
            issues.append(issue)
        
        # Issue 3: High block rate
        if metrics['block_rate'] > self.max_block_rate:
            issue = HealthIssue(
                issue_type='EXCESSIVE_BLOCKS',
                severity='MEDIUM',
                message=f'High signal block rate: {metrics["block_rate"]:.1%}',
                metric_value=metrics['block_rate'],
                expected_value=self.max_block_rate,
                recommendations=[
                    f'PDT blocks: {metrics["pdt_blocks"]}',
                    f'Diversification blocks: {metrics["diversification_blocks"]}',
                    'Review PDT protection settings if too aggressive',
                    'Check diversification limits'
                ],
                auto_fixable=False
            )
            issues.append(issue)
        
        # Issue 4: High error rate
        if metrics['errors_count'] > self.max_errors_per_day:
            issue = HealthIssue(
                issue_type='HIGH_ERRORS',
                severity='HIGH',
                message=f'{metrics["errors_count"]} errors detected',
                metric_value=metrics['errors_count'],
                expected_value=self.max_errors_per_day,
                recommendations=[
                    f'API errors: {metrics["api_errors"]}',
                    'Check API connectivity',
                    'Verify API key permissions',
                    'Review error logs for patterns'
                ],
                auto_fixable=False
            )
            issues.append(issue)
        
        # Issue 5: No signals generated
        if metrics['signals_generated'] == 0:
            issue = HealthIssue(
                issue_type='NO_SIGNALS',
                severity='CRITICAL',
                message='No trading signals generated',
                metric_value=0,
                expected_value=10,
                recommendations=[
                    'Pre-filter returned 0 candidates',
                    'Check signal generation logic',
                    'Verify strategy is enabled',
                    'Check market hours and trading schedule'
                ],
                auto_fixable=True
            )
            issues.append(issue)
        
        return issues
    
    def _determine_overall_status(self, issues: List[HealthIssue]) -> str:
        """Determine overall system health status"""
        if not issues:
            return 'HEALTHY'
        
        critical_count = sum(1 for i in issues if i.severity == 'CRITICAL')
        high_count = sum(1 for i in issues if i.severity == 'HIGH')
        
        if critical_count > 0:
            return 'CRITICAL'
        elif high_count > 0:
            return 'DEGRADED'
        else:
            return 'WARNING'
    
    def _calculate_health_score(self, metrics: Dict, issues: List[HealthIssue]) -> int:
        """Calculate overall health score (0-100)"""
        score = 100
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == 'CRITICAL':
                score -= 30
            elif issue.severity == 'HIGH':
                score -= 20
            elif issue.severity == 'MEDIUM':
                score -= 10
            else:
                score -= 5
        
        # Bonus for good metrics
        if metrics['positions_opened'] >= self.min_expected_positions:
            score += 5
        
        if metrics['errors_count'] == 0:
            score += 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, issues: List[HealthIssue], metrics: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if not issues:
            recommendations.append("✅ System is healthy - no action required")
            return recommendations
        
        # Prioritize auto-fixable issues
        auto_fixable = [i for i in issues if i.auto_fixable]
        
        if auto_fixable:
            recommendations.append("🔧 AUTO-CORRECTABLE ISSUES DETECTED:")
            for issue in auto_fixable:
                recommendations.append(f"  • {issue.message}")
                recommendations.extend(f"    - {r}" for r in issue.recommendations)
        
        # Manual fixes
        manual_issues = [i for i in issues if not i.auto_fixable]
        if manual_issues:
            recommendations.append("\n⚠️ MANUAL REVIEW REQUIRED:")
            for issue in manual_issues:
                recommendations.append(f"  • {issue.message}")
                recommendations.extend(f"    - {r}" for r in issue.recommendations)
        
        # Specific guidance based on patterns
        if metrics['prefilter_candidates'] == 0:
            recommendations.append("\n💡 QUICK FIX FOR PRE-FILTER:")
            recommendations.append("  Run: Edit pre_filter.py, reduce min_rows from 30 to 20")
        
        return recommendations
    
    def _save_report(self, report: Dict, check_date: str):
        """Save health report to file"""
        filename = self.report_dir / f"health_report_{check_date}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"📄 Health report saved: {filename}")
        
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
    
    def _log_health_summary(self, report: Dict):
        """Log human-readable health summary"""
        self.logger.info("=" * 60)
        self.logger.info(f"🏥 HEALTH CHECK SUMMARY - {report['check_date']}")
        self.logger.info("=" * 60)
        self.logger.info(f"Overall Status: {report['overall_status']}")
        self.logger.info(f"Health Score: {report['system_health_score']}/100")
        self.logger.info(f"Issues Found: {report['issues_found']}")
        
        self.logger.info("\n📊 KEY METRICS:")
        metrics = report['metrics']
        self.logger.info(f"  Positions Opened: {metrics['positions_opened']}")
        self.logger.info(f"  Positions Closed: {metrics['positions_closed']}")
        self.logger.info(f"  Signals Generated: {metrics['signals_generated']}")
        self.logger.info(f"  Signals Blocked: {metrics['signals_blocked']}")
        self.logger.info(f"  Pre-filter Candidates: {metrics['prefilter_candidates']}")
        self.logger.info(f"  Errors: {metrics['errors_count']}")
        
        if report['issues_found'] > 0:
            self.logger.warning("\n⚠️ ISSUES DETECTED:")
            for issue in report['issues']:
                self.logger.warning(f"  • {issue['severity']}: {issue['message']}")
        
        if report['recommendations']:
            self.logger.info("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                self.logger.info(f"  {rec}")
        
        self.logger.info("=" * 60)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run health check
    checker = DailyHealthChecker()
    
    print("\n🏥 Running daily health check...")
    result = checker.run_daily_check()
    
    print(f"\n{'='*60}")
    print(f"System Status: {result['overall_status']}")
    print(f"Health Score: {result['system_health_score']}/100")
    print(f"Issues: {result['issues_found']}")
    print(f"{'='*60}\n")
