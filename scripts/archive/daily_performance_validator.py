#!/usr/bin/env python3
"""
Integrated Daily Performance Validator
Runs automatically as part of bot's routine to validate strategy performance
"""

import sys
import os
import json
from datetime import datetime, timedelta
import logging

# Setup path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from core.adaptive_threshold_manager import AdaptiveThresholdManager

logger = logging.getLogger(__name__)

class DailyPerformanceValidator:
    """Lightweight daily validation integrated into bot routine"""
    
    def __init__(self):
        self.adaptive_manager = AdaptiveThresholdManager()
        self.alert_thresholds = {
            'min_win_rate': 0.50,      # Alert if win rate < 50%
            'min_sharpe': 1.5,         # Alert if Sharpe < 1.5
            'max_drawdown': 0.15,      # Alert if drawdown > 15%
            'min_trades': 5            # Need minimum trades for valid analysis
        }
        
    def run_daily_validation(self) -> dict:
        """Run lightweight daily performance validation"""
        print("📊 Running daily performance validation...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'daily_routine',
            'alerts': [],
            'performance_summary': {},
            'recommendation': 'continue'
        }
        
        try:
            # Analyze last 7 days
            recent_metrics = self.adaptive_manager.analyze_trade_logs(days=7)
            
            # Analyze last 30 days for context
            monthly_metrics = self.adaptive_manager.analyze_trade_logs(days=30)
            
            results['performance_summary'] = {
                'recent_7d': {
                    'win_rate': recent_metrics.win_rate,
                    'total_trades': recent_metrics.total_trades,
                    'sharpe_ratio': recent_metrics.sharpe_ratio,
                    'avg_return': recent_metrics.avg_return,
                    'max_drawdown': recent_metrics.max_drawdown
                },
                'monthly_30d': {
                    'win_rate': monthly_metrics.win_rate,
                    'total_trades': monthly_metrics.total_trades,
                    'sharpe_ratio': monthly_metrics.sharpe_ratio,
                    'avg_return': monthly_metrics.avg_return,
                    'max_drawdown': monthly_metrics.max_drawdown
                }
            }
            
            print(f"   📈 Recent (7d): {recent_metrics.win_rate:.1%} win rate, {recent_metrics.total_trades} trades")
            print(f"   📊 Monthly (30d): {monthly_metrics.win_rate:.1%} win rate, {monthly_metrics.total_trades} trades")
            
            # Check alert conditions
            self._check_alert_conditions(recent_metrics, monthly_metrics, results)
            
            # Generate recommendation
            results['recommendation'] = self._generate_recommendation(recent_metrics, monthly_metrics, results)
            
            print(f"   🎯 Recommendation: {results['recommendation'].upper()}")
            
            return results
            
        except Exception as e:
            logger.error(f"Daily validation failed: {e}")
            results['error'] = str(e)
            results['recommendation'] = 'investigate'
            return results
    
    def _check_alert_conditions(self, recent_metrics, monthly_metrics, results):
        """Check for performance alerts"""
        alerts = []
        
        # Recent performance alerts (7-day)
        if recent_metrics.total_trades >= self.alert_thresholds['min_trades']:
            if recent_metrics.win_rate < self.alert_thresholds['min_win_rate']:
                alerts.append({
                    'type': 'win_rate_low',
                    'severity': 'warning',
                    'message': f"Recent win rate {recent_metrics.win_rate:.1%} below {self.alert_thresholds['min_win_rate']:.1%}",
                    'current_value': recent_metrics.win_rate,
                    'threshold': self.alert_thresholds['min_win_rate']
                })
            
            if recent_metrics.sharpe_ratio < self.alert_thresholds['min_sharpe']:
                alerts.append({
                    'type': 'sharpe_low',
                    'severity': 'warning',
                    'message': f"Recent Sharpe ratio {recent_metrics.sharpe_ratio:.2f} below {self.alert_thresholds['min_sharpe']:.2f}",
                    'current_value': recent_metrics.sharpe_ratio,
                    'threshold': self.alert_thresholds['min_sharpe']
                })
        
        # Monthly performance alerts (30-day)
        if monthly_metrics.max_drawdown > self.alert_thresholds['max_drawdown']:
            alerts.append({
                'type': 'drawdown_high',
                'severity': 'critical',
                'message': f"Monthly drawdown {monthly_metrics.max_drawdown:.1%} exceeds {self.alert_thresholds['max_drawdown']:.1%}",
                'current_value': monthly_metrics.max_drawdown,
                'threshold': self.alert_thresholds['max_drawdown']
            })
        
        # Trade frequency alerts
        if recent_metrics.total_trades == 0:
            alerts.append({
                'type': 'no_trades',
                'severity': 'info',
                'message': "No trades in last 7 days - check market conditions or signal generation",
                'current_value': 0,
                'threshold': 1
            })
        elif recent_metrics.total_trades < 3 and monthly_metrics.total_trades < 10:
            alerts.append({
                'type': 'low_activity',
                'severity': 'info', 
                'message': "Low trading activity - consider reviewing confidence threshold",
                'current_value': recent_metrics.total_trades,
                'threshold': 3
            })
        
        results['alerts'] = alerts
        
        # Print alerts
        if alerts:
            print(f"   ⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                severity_emoji = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🚨'}
                print(f"      {severity_emoji.get(alert['severity'], '⚠️')} {alert['message']}")
        else:
            print(f"   ✅ No performance alerts")
    
    def _generate_recommendation(self, recent_metrics, monthly_metrics, results):
        """Generate actionable recommendation"""
        alerts = results['alerts']
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in alerts if a['severity'] == 'warning']
        
        if critical_alerts:
            return 'review_immediately'
        elif len(warning_alerts) >= 2:
            return 'review_within_24h'
        elif warning_alerts:
            return 'monitor_closely'
        elif recent_metrics.total_trades > 0 and recent_metrics.win_rate > 0.55:
            return 'continue_excellent'
        elif recent_metrics.total_trades > 0:
            return 'continue_monitor'
        else:
            return 'continue_low_activity'
    
    def save_validation_results(self, results):
        """Save validation results to log file"""
        log_file = "/home/wes/Desktop/litebotx-usb-deployment/logs/daily_validation.json"
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Load existing logs
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Add new result
        logs.append(results)
        
        # Keep only last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        logs = [log for log in logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff_date]
        
        # Save updated logs
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"   💾 Validation results saved to {log_file}")

def run_integrated_validation():
    """Main function for integrated daily validation"""
    print("🤖 INTEGRATED DAILY PERFORMANCE VALIDATION")
    print("=" * 50)
    
    validator = DailyPerformanceValidator()
    
    # Run validation
    results = validator.run_daily_validation()
    
    # Save results
    validator.save_validation_results(results)
    
    # Return summary for bot integration
    return {
        'status': 'completed',
        'recommendation': results['recommendation'],
        'alert_count': len(results.get('alerts', [])),
        'critical_alerts': len([a for a in results.get('alerts', []) if a['severity'] == 'critical']),
        'performance_ok': results['recommendation'] in ['continue_excellent', 'continue_monitor', 'continue_low_activity']
    }

if __name__ == "__main__":
    # Run as standalone script
    summary = run_integrated_validation()
    
    print(f"\n📋 VALIDATION SUMMARY:")
    print(f"   Status: {summary['status']}")
    print(f"   Recommendation: {summary['recommendation']}")
    print(f"   Total alerts: {summary['alert_count']}")
    print(f"   Critical alerts: {summary['critical_alerts']}")
    print(f"   Performance OK: {'✅' if summary['performance_ok'] else '❌'}")
    
    # Exit with appropriate code
    if summary['critical_alerts'] > 0:
        sys.exit(2)  # Critical issues
    elif not summary['performance_ok']:
        sys.exit(1)  # Performance concerns
    else:
        sys.exit(0)  # All good