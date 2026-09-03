"""
Enhanced logging system for bot_v2
Provides structured, rich logging for fast debugging

Features:
- Multiple log files for different purposes
- Structured JSON logs for parsing
- Human-readable summary logs
- Activity timeline tracking
- Performance metrics logging
- Error context capture
"""

import logging
import json
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional


class EnhancedLogger:
    """
    Multi-channel logger with structured output
    
    Log Files Created:
    1. sprint1_alpaca.log - Main detailed log (existing)
    2. trading_activity.log - Human-readable timeline of trades
    3. debug_detailed.log - Extra verbose debug info
    4. daily_summary.json - Structured data for analysis
    """
    
    def __init__(self, base_logger: logging.Logger):
        self.base_logger = base_logger
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Activity log - human readable timeline
        self.activity_log = self.logs_dir / "trading_activity.log"
        
        # Debug log - extra verbose
        self.debug_log = self.logs_dir / "debug_detailed.log"
        
        # Daily summary - structured JSON
        today = dt.date.today().strftime("%Y%m%d")
        self.summary_log = self.logs_dir / f"daily_summary_{today}.json"
        
        # Initialize summary data
        self.summary_data = {
            "date": str(dt.date.today()),
            "start_time": dt.datetime.now().isoformat(),
            "events": [],
            "positions": {"entered": [], "exited": []},
            "errors": [],
            "performance": {}
        }
        
        # Session tracking
        self.session_start = dt.datetime.now()
        self.last_activity = dt.datetime.now()
        
    def _write_activity(self, message: str, level: str = "INFO"):
        """Write to human-readable activity timeline"""
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.activity_log, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    
    def _write_debug(self, message: str, context: Optional[Dict] = None):
        """Write to verbose debug log"""
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.debug_log, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
            if context:
                f.write(f"    Context: {json.dumps(context, indent=2)}\n")
    
    def _update_summary(self, event_type: str, data: Dict):
        """Update structured summary data"""
        event = {
            "timestamp": dt.datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.summary_data["events"].append(event)
        
        # Save summary after each event
        with open(self.summary_log, 'w') as f:
            json.dump(self.summary_data, f, indent=2)
    
    # ========================================================================
    # PHASE LOGGING - Track bot phase transitions
    # ========================================================================
    
    def log_phase_change(self, old_phase: str, new_phase: str, reason: str = ""):
        """Log when bot changes trading phase"""
        msg = f"📍 PHASE CHANGE: {old_phase} → {new_phase}"
        if reason:
            msg += f" ({reason})"
        
        self.base_logger.info(msg)
        self._write_activity(msg)
        self._update_summary("phase_change", {
            "from": old_phase,
            "to": new_phase,
            "reason": reason
        })
    
    # ========================================================================
    # POSITION LOGGING - Track position lifecycle
    # ========================================================================
    
    def log_position_entry(self, symbol: str, price: float, shares: int, 
                           signal_score: float, reason: str):
        """Log new position entry"""
        value = price * shares
        msg = f"📈 ENTRY: {symbol} | ${price:.2f} × {shares} = ${value:.2f} | Score: {signal_score:.2f} | {reason}"
        
        self.base_logger.info(msg)
        self._write_activity(msg, "ENTRY")
        
        position_data = {
            "symbol": symbol,
            "price": price,
            "shares": shares,
            "value": value,
            "signal_score": signal_score,
            "reason": reason
        }
        self.summary_data["positions"]["entered"].append(position_data)
        self._update_summary("position_entry", position_data)
        
        # Debug details
        self._write_debug(f"Entry details for {symbol}", position_data)
    
    def log_position_exit(self, symbol: str, entry_price: float, exit_price: float,
                          shares: int, pnl: float, reason: str, days_held: int):
        """Log position exit"""
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAK-EVEN"
        
        msg = (f"📉 EXIT: {symbol} | Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f} | "
               f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | {result} | Days: {days_held} | {reason}")
        
        self.base_logger.info(msg)
        self._write_activity(msg, "EXIT")
        
        exit_data = {
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "shares": shares,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "result": result,
            "days_held": days_held,
            "reason": reason
        }
        self.summary_data["positions"]["exited"].append(exit_data)
        self._update_summary("position_exit", exit_data)
        
        # Debug details
        self._write_debug(f"Exit details for {symbol}", exit_data)
    
    def log_position_stuck(self, symbol: str, entry_date: str, exit_date: str,
                           days_overdue: int, reason: str):
        """Log when position fails to exit"""
        msg = f"⚠️ STUCK POSITION: {symbol} | Entry: {entry_date} | Should have exited: {exit_date} | {days_overdue} days overdue | {reason}"
        
        self.base_logger.warning(msg)
        self._write_activity(msg, "WARNING")
        
        stuck_data = {
            "symbol": symbol,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "days_overdue": days_overdue,
            "reason": reason
        }
        self._update_summary("position_stuck", stuck_data)
    
    # ========================================================================
    # SIGNAL LOGGING - Track signal generation
    # ========================================================================
    
    def log_signal_generation(self, phase: str, candidates_in: int, 
                              candidates_out: int, duration_ms: float):
        """Log signal generation performance"""
        msg = f"🔍 SIGNALS ({phase}): {candidates_in} candidates → {candidates_out} signals | {duration_ms:.0f}ms"
        
        self.base_logger.info(msg)
        self._write_activity(msg)
        
        self._update_summary("signal_generation", {
            "phase": phase,
            "candidates_in": candidates_in,
            "signals_out": candidates_out,
            "duration_ms": duration_ms
        })
    
    def log_prefilter_results(self, total: int, passed: int, failed: int, 
                              duration_ms: float, reasons: Dict[str, int]):
        """Log PreFilter screening results"""
        pass_rate = (passed / total * 100) if total > 0 else 0
        msg = f"🧪 PREFILTER: {passed}/{total} passed ({pass_rate:.1f}%) | {duration_ms:.0f}ms"
        
        self.base_logger.info(msg)
        self._write_activity(msg)
        
        # Log rejection reasons
        if reasons:
            reasons_str = ", ".join([f"{k}: {v}" for k, v in reasons.items()])
            self._write_debug(f"PreFilter rejections: {reasons_str}")
        
        self._update_summary("prefilter_results", {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "duration_ms": duration_ms,
            "rejection_reasons": reasons
        })
    
    # ========================================================================
    # ERROR LOGGING - Rich error context
    # ========================================================================
    
    def log_error(self, error: Exception, context: str, details: Optional[Dict] = None):
        """Log error with full context"""
        msg = f"❌ ERROR in {context}: {type(error).__name__}: {str(error)}"
        
        self.base_logger.error(msg, exc_info=True)
        self._write_activity(msg, "ERROR")
        
        error_data = {
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "details": details or {}
        }
        self.summary_data["errors"].append(error_data)
        self._update_summary("error", error_data)
        
        # Write full traceback to debug log
        import traceback
        self._write_debug(
            f"ERROR in {context}: {error}",
            {"traceback": traceback.format_exc(), "details": details}
        )
    
    def log_warning(self, message: str, context: Optional[str] = None, 
                    details: Optional[Dict] = None):
        """Log warning with context"""
        if context:
            msg = f"⚠️ WARNING [{context}]: {message}"
        else:
            msg = f"⚠️ WARNING: {message}"
        
        self.base_logger.warning(msg)
        self._write_activity(msg, "WARNING")
        
        if details:
            self._write_debug(msg, details)
    
    # ========================================================================
    # PERFORMANCE LOGGING - Track system performance
    # ========================================================================
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric"""
        msg = f"📊 PERFORMANCE: {metric_name} = {value:.2f}{unit}"
        self._write_debug(msg)
        
        if "performance" not in self.summary_data:
            self.summary_data["performance"] = {}
        self.summary_data["performance"][metric_name] = {"value": value, "unit": unit}
    
    def log_monitoring_cycle(self, active_positions: int, checks_performed: int,
                             exits_triggered: int, duration_ms: float):
        """Log monitoring cycle performance"""
        msg = f"🔄 MONITORING: {active_positions} positions | {checks_performed} checks | {exits_triggered} exits | {duration_ms:.0f}ms"
        
        self._write_debug(msg)
        self._update_summary("monitoring_cycle", {
            "active_positions": active_positions,
            "checks": checks_performed,
            "exits": exits_triggered,
            "duration_ms": duration_ms
        })
    
    # ========================================================================
    # SESSION LOGGING - Track bot session
    # ========================================================================
    
    def log_session_start(self, portfolio_value: float, active_positions: int,
                          buying_power: float):
        """Log bot session start"""
        msg = f"""
╔══════════════════════════════════════════════════════════════╗
║              BOT SESSION STARTED                              ║
╚══════════════════════════════════════════════════════════════╝
📅 Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💰 Portfolio Value: ${portfolio_value:.2f}
📊 Active Positions: {active_positions}
💵 Buying Power: ${buying_power:.2f}
"""
        
        self.base_logger.info(msg)
        self._write_activity(f"SESSION START | Portfolio: ${portfolio_value:.2f} | Positions: {active_positions}")
        
        self.summary_data["session"] = {
            "start_time": dt.datetime.now().isoformat(),
            "initial_portfolio": portfolio_value,
            "initial_positions": active_positions,
            "initial_buying_power": buying_power
        }
    
    def log_daily_summary(self, entries: int, exits: int, wins: int, losses: int,
                         total_pnl: float, portfolio_value: float):
        """Log end-of-day summary"""
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        msg = f"""
╔══════════════════════════════════════════════════════════════╗
║              DAILY SUMMARY                                    ║
╚══════════════════════════════════════════════════════════════╝
📅 Date: {dt.date.today()}
📈 Entries: {entries}
📉 Exits: {exits}
✅ Wins: {wins} | ❌ Losses: {losses}
📊 Win Rate: {win_rate:.1f}%
💰 Total P&L: ${total_pnl:+.2f}
💵 Portfolio Value: ${portfolio_value:.2f}
⏱️  Session Duration: {(dt.datetime.now() - self.session_start).seconds / 3600:.1f} hours
"""
        
        self.base_logger.info(msg)
        self._write_activity(
            f"DAILY SUMMARY | Entries: {entries} | Exits: {exits} | Win Rate: {win_rate:.1f}% | P&L: ${total_pnl:+.2f}"
        )
        
        self.summary_data["daily_summary"] = {
            "date": str(dt.date.today()),
            "entries": entries,
            "exits": exits,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "final_portfolio": portfolio_value,
            "session_hours": (dt.datetime.now() - self.session_start).seconds / 3600
        }
        
        # Save final summary
        with open(self.summary_log, 'w') as f:
            json.dump(self.summary_data, f, indent=2)
    
    # ========================================================================
    # WATCHDOG LOGGING - Detect issues
    # ========================================================================
    
    def log_inactivity_warning(self, hours_since_last_trade: float):
        """Log warning when no trading activity"""
        msg = f"⚠️ INACTIVITY WARNING: No trades for {hours_since_last_trade:.1f} hours"
        
        self.base_logger.warning(msg)
        self._write_activity(msg, "WARNING")
        self._update_summary("inactivity_warning", {"hours": hours_since_last_trade})
    
    def log_stuck_positions_summary(self, stuck_count: int, total_value: float):
        """Log summary of stuck positions"""
        if stuck_count > 0:
            msg = f"⚠️ STUCK POSITIONS: {stuck_count} positions stuck | ${total_value:.2f} capital locked"
            
            self.base_logger.warning(msg)
            self._write_activity(msg, "WARNING")
            self._update_summary("stuck_positions_summary", {
                "count": stuck_count,
                "total_value": total_value
            })
