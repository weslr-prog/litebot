"""
AI Performance Tracker - Performance monitoring, reporting, and dashboard updates
Extracted from ShortCycleTrader for modular architecture
"""
import logging
import json
import datetime as dt
from typing import Dict, List, Any, Optional


class AIPerformanceTracker:
    """
    Manages performance tracking, daily reports, and monitoring.
    
    Responsibilities:
    - Generate daily performance reports
    - Track portfolio summaries
    - Manage dashboard callbacks
    - Run end-of-day monitoring
    - Calculate performance metrics (win rate, drawdown, etc.)
    """
    
    def __init__(self, config, monitoring_system=None, logger: Optional[logging.Logger] = None):
        """
        Initialize performance tracker
        
        Args:
            config: ShortCycleConfig with trading parameters
            monitoring_system: Optional SelfMonitoringSystem
            logger: Optional logger instance
        """
        self.config = config
        self.monitoring_system = monitoring_system
        self.logger = logger or logging.getLogger(__name__)
        
        # Dashboard callbacks
        self.signal_callbacks = []
        self.trade_callbacks = []
        
        # Recent trades buffer for performance metrics
        self.recent_trades: List[Any] = []
    
    def generate_daily_report(self, portfolio_state, positions: List[Any], kill_switches: Dict[str, bool]):
        """
        Generate daily performance and status report.
        
        Args:
            portfolio_state: PortfolioState object
            positions: List of ShortCyclePosition objects
            kill_switches: Dictionary of kill switch states
        """
        from ..models.positions import PositionStatus
        
        active_positions = [p for p in positions if p.status == PositionStatus.ENTERED]
        
        report = {
            "date": dt.date.today().isoformat(),
            "portfolio_value": portfolio_state.portfolio_value,
            "active_positions": len(active_positions),
            "daily_pnl": portfolio_state.daily_pnl,
            "daily_realized_pnl": portfolio_state.daily_realized_pnl,
            "daily_unrealized_pnl": portfolio_state.daily_unrealized_pnl,
            "weekly_pnl": portfolio_state.weekly_pnl,
            "trades_today": portfolio_state.trades_today,
            "late_entries_today": portfolio_state.late_entries_today,
            "kill_switches": kill_switches
        }
        
        self.logger.info(f"📊 Daily Report: {json.dumps(report, indent=2)}")
        return report
    
    def add_signal_callback(self, callback):
        """Add callback for signal generation events"""
        self.signal_callbacks.append(callback)
    
    def add_trade_callback(self, callback):
        """Add callback for trade execution events"""
        self.trade_callbacks.append(callback)
    
    def notify_signal_generated(self, symbol: str, signal_data: dict):
        """Notify all signal callbacks"""
        for callback in self.signal_callbacks:
            try:
                callback(symbol, signal_data)
            except Exception as e:
                self.logger.error(f"Signal callback error: {e}")
    
    def notify_trade_executed(self, symbol: str, trade_data: dict):
        """Notify all trade callbacks"""
        for callback in self.trade_callbacks:
            try:
                callback(symbol, trade_data)
            except Exception as e:
                self.logger.error(f"Trade callback error: {e}")
    
    def add_trade_to_history(self, position):
        """Add trade to recent trades buffer for performance tracking"""
        try:
            trade_record = type("_Trade", (), {})()
            trade_record.net_pnl = position.realized_pnl
            trade_record.symbol = position.symbol
            self.recent_trades.append(trade_record)
            self.recent_trades = self.recent_trades[-50:]  # Keep last 50
        except Exception:
            pass
    
    def estimate_win_rate(self) -> float:
        """Estimate win rate from recent trades"""
        try:
            wins = sum(1 for t in self.recent_trades if getattr(t, 'net_pnl', 0) > 0)
            total = len(self.recent_trades)
            return wins / total if total else 0.0
        except Exception:
            return 0.0
    
    def estimate_consecutive_losses(self) -> int:
        """Count consecutive losses from recent trades"""
        try:
            count = 0
            for t in reversed(self.recent_trades):
                if getattr(t, 'net_pnl', 0) <= 0:
                    count += 1
                else:
                    break
            return count
        except Exception:
            return 0
    
    def estimate_drawdown(self) -> float:
        """Estimate current drawdown (placeholder for future enhancement)"""
        return 0.0
    
    def run_end_of_day_monitoring(self):
        """Run self-monitoring at end of trading day"""
        if not self.monitoring_system:
            self.logger.debug("Self-monitoring not available")
            return
            
        try:
            self.logger.info("🤖 Running end-of-day self-monitoring...")
            results = self.monitoring_system.run_end_of_day_check()
            
            # Log report location
            if results.get('report_file'):
                self.logger.info(f"📄 Daily report saved: {results['report_file']}")
            
            # Alert on PDT violations
            if results.get('pdt_audit'):
                violations = results['pdt_audit'].get('violations_found', 0)
                if violations > 0:
                    self.logger.critical(f"🚨 PDT VIOLATIONS DETECTED: {violations}")
                    self.logger.critical("   ⚠️ Review report and reduce trading frequency!")
                else:
                    self.logger.info(f"✅ PDT Check: No violations (Score: {results['pdt_audit'].get('pdt_score', 100)}/100)")
            
            # Alert on health status
            if results.get('health_check'):
                status = results['health_check'].get('overall_status', 'UNKNOWN')
                score = results['health_check'].get('system_health_score', 0)
                
                if status == 'CRITICAL':
                    self.logger.critical(f"🚨 SYSTEM HEALTH CRITICAL ({score}/100)")
                    self.logger.critical("   ⚠️ Immediate attention required!")
                elif status == 'WARNING':
                    self.logger.warning(f"⚠️ System health degraded ({score}/100)")
                else:
                    self.logger.info(f"✅ System Health: {status} ({score}/100)")
            
            # Alert on auto-corrections
            if results.get('auto_correct'):
                adjustments = results['auto_correct'].get('adjustments_made', 0)
                if adjustments > 0:
                    self.logger.info(f"🔧 Auto-corrections applied: {adjustments}")
                    for adjustment in results['auto_correct'].get('details', []):
                        self.logger.info(f"   • {adjustment}")
                        
            self.logger.info("✅ End-of-day monitoring complete")
            
        except Exception as e:
            self.logger.error(f"❌ Self-monitoring failed: {e}")
            self.logger.error("   System will continue operating, but manual review recommended")
    
    def get_runtime_state(self, weekly_return: float, symbols_covered: int, signals_today: int, trades_today: int) -> Dict[str, Any]:
        """
        Generate runtime state for performance controller.
        
        Returns:
            Dictionary with current performance metrics
        """
        return {
            "mode": "paper",
            "weekly_return": weekly_return,
            "drawdown": self.estimate_drawdown(),
            "win_rate": self.estimate_win_rate(),
            "consecutive_losses": self.estimate_consecutive_losses(),
            "symbols_covered": symbols_covered,
            "signals_today": signals_today,
            "trades_today": trades_today
        }
