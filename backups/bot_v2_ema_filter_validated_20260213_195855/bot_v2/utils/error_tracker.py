"""
Error Tracker - Centralized error tracking and analysis for silent failures
"""
import logging
import datetime as dt
from typing import Dict, Optional, Any, List
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json
import os


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Recoverable, data available from fallback
    MEDIUM = "medium"     # Partial data loss, may affect decisions
    HIGH = "high"         # Significant data loss, could miss trades
    CRITICAL = "critical" # System-level failure


@dataclass
class TrackedError:
    """Individual tracked error"""
    timestamp: dt.datetime
    module: str
    function: str
    symbol: Optional[str]
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = False
    fallback_used: Optional[str] = None


class ErrorTracker:
    """
    Centralized error tracking with aggregation and analysis.
    
    Tracks silent failures across data loading, signal generation,
    and execution modules to provide visibility into issues.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.errors: List[TrackedError] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.symbol_failures: Dict[str, int] = defaultdict(int)
        self.module_failures: Dict[str, int] = defaultdict(int)
        self._session_start = dt.datetime.now()
        self._error_log_file = "error_tracker.json"
    
    def track_error(
        self,
        module: str,
        function: str,
        error: Exception,
        symbol: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovered: bool = False,
        fallback_used: Optional[str] = None
    ) -> None:
        """
        Track an error occurrence.
        
        Args:
            module: Module where error occurred (e.g., 'data_loader')
            function: Function name where error occurred
            error: The exception that was caught
            symbol: Symbol being processed (if applicable)
            severity: Error severity level
            context: Additional context (parameters, state, etc.)
            recovered: Whether fallback recovered the operation
            fallback_used: Description of fallback used (if any)
        """
        tracked = TrackedError(
            timestamp=dt.datetime.now(),
            module=module,
            function=function,
            symbol=symbol,
            error_type=type(error).__name__,
            error_message=str(error)[:500],  # Truncate long messages
            severity=severity,
            context=context or {},
            recovered=recovered,
            fallback_used=fallback_used
        )
        
        self.errors.append(tracked)
        
        # Update counts
        error_key = f"{module}.{function}.{type(error).__name__}"
        self.error_counts[error_key] += 1
        self.module_failures[module] += 1
        
        if symbol:
            self.symbol_failures[symbol] += 1
        
        # Log based on severity
        log_msg = (
            f"[{severity.value.upper()}] {module}.{function}: "
            f"{type(error).__name__}: {str(error)[:100]}"
        )
        if symbol:
            log_msg = f"[{symbol}] " + log_msg
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.error(f"🚨 {log_msg}")
        elif severity == ErrorSeverity.HIGH:
            self.logger.warning(f"⚠️ {log_msg}")
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.info(f"📋 {log_msg}")
        else:
            self.logger.debug(f"📝 {log_msg}")
        
        if recovered:
            self.logger.info(f"   ↳ Recovered via: {fallback_used}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of errors in current session."""
        session_duration = (dt.datetime.now() - self._session_start).total_seconds() / 3600
        
        severity_counts = defaultdict(int)
        for error in self.errors:
            severity_counts[error.severity.value] += 1
        
        recovery_rate = 0.0
        if self.errors:
            recovered_count = sum(1 for e in self.errors if e.recovered)
            recovery_rate = recovered_count / len(self.errors)
        
        return {
            "session_duration_hours": round(session_duration, 2),
            "total_errors": len(self.errors),
            "by_severity": dict(severity_counts),
            "by_module": dict(self.module_failures),
            "top_failing_symbols": dict(
                sorted(self.symbol_failures.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "top_error_types": dict(
                sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "recovery_rate": round(recovery_rate * 100, 1)
        }
    
    def log_session_summary(self) -> None:
        """Log a summary of errors in the current session."""
        summary = self.get_session_summary()
        
        if summary["total_errors"] == 0:
            self.logger.info("✅ Error Tracker: No errors recorded this session")
            return
        
        self.logger.info("=" * 60)
        self.logger.info("📊 ERROR TRACKER SESSION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Duration: {summary['session_duration_hours']} hours")
        self.logger.info(f"Total Errors: {summary['total_errors']}")
        self.logger.info(f"Recovery Rate: {summary['recovery_rate']}%")
        
        self.logger.info("\n📈 By Severity:")
        for severity, count in summary["by_severity"].items():
            self.logger.info(f"  {severity}: {count}")
        
        self.logger.info("\n📦 By Module:")
        for module, count in summary["by_module"].items():
            self.logger.info(f"  {module}: {count}")
        
        if summary["top_failing_symbols"]:
            self.logger.info("\n⚠️ Top Failing Symbols:")
            for symbol, count in list(summary["top_failing_symbols"].items())[:5]:
                self.logger.info(f"  {symbol}: {count} failures")
        
        self.logger.info("=" * 60)
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def get_symbol_failures(self, symbol: str) -> List[TrackedError]:
        """Get all failures for a specific symbol."""
        return [e for e in self.errors if e.symbol == symbol]
    
    def should_skip_symbol(self, symbol: str, threshold: int = 5) -> bool:
        """Check if a symbol has too many failures and should be skipped."""
        return self.symbol_failures.get(symbol, 0) >= threshold
    
    def get_problematic_symbols(self, threshold: int = 3) -> List[str]:
        """Get list of symbols with repeated failures."""
        return [s for s, count in self.symbol_failures.items() if count >= threshold]
    
    def save_to_file(self) -> None:
        """Save error data to JSON file for analysis."""
        try:
            data = {
                "session_start": self._session_start.isoformat(),
                "session_end": dt.datetime.now().isoformat(),
                "summary": self.get_session_summary(),
                "errors": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "module": e.module,
                        "function": e.function,
                        "symbol": e.symbol,
                        "error_type": e.error_type,
                        "error_message": e.error_message,
                        "severity": e.severity.value,
                        "recovered": e.recovered,
                        "fallback_used": e.fallback_used
                    }
                    for e in self.errors[-100:]  # Keep last 100 errors
                ]
            }
            
            with open(self._error_log_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save error tracker data: {e}")
    
    def clear_session(self) -> None:
        """Clear all errors for a new session."""
        self.errors.clear()
        self.error_counts.clear()
        self.symbol_failures.clear()
        self.module_failures.clear()
        self._session_start = dt.datetime.now()


# Global error tracker instance (can be overridden)
_global_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get or create global error tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ErrorTracker()
    return _global_tracker


def track_error(
    module: str,
    function: str,
    error: Exception,
    symbol: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None,
    recovered: bool = False,
    fallback_used: Optional[str] = None
) -> None:
    """Convenience function to track error using global tracker."""
    get_error_tracker().track_error(
        module=module,
        function=function,
        error=error,
        symbol=symbol,
        severity=severity,
        context=context,
        recovered=recovered,
        fallback_used=fallback_used
    )
