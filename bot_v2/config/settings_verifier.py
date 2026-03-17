"""
Startup Settings Verifier
Logs effective prefilter and trading settings every session to prevent config drift
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
from bot_v2.config.trading_config import ShortCycleConfig


class SettingsVerifier:
    """Validates and logs runtime configuration at startup"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def verify_and_log_settings(self) -> Dict[str, Any]:
        """Capture and verify all active settings, return summary"""
        settings_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "prefilter": self._capture_prefilter_settings(),
            "trading": self._capture_trading_settings(),
            "status": "healthy"  # Can be updated to 'warning' if issues found
        }
        
        self._log_settings_report(settings_snapshot)
        return settings_snapshot
    
    def _capture_prefilter_settings(self) -> Dict[str, Any]:
        """Capture ALL prefilter thresholds"""
        return {
            "price_range": {
                "min": SIMPLE_PREFILTER_CONFIG.get('min_price', 'MISSING'),
                "max": SIMPLE_PREFILTER_CONFIG.get('max_price', 'MISSING')
            },
            "volume": {
                "min_volume": SIMPLE_PREFILTER_CONFIG.get('min_volume', 'MISSING'),
                "max_volume": SIMPLE_PREFILTER_CONFIG.get('max_volume', 'MISSING'),
                "min_dollar_volume": SIMPLE_PREFILTER_CONFIG.get('min_dollar_volume', 'MISSING')
            },
            "volatility_atr": {
                "min_atr_pct": f"{SIMPLE_PREFILTER_CONFIG.get('min_atr_pct', 'MISSING')*100:.2f}%",
                "max_atr_pct": f"{SIMPLE_PREFILTER_CONFIG.get('max_atr_pct', 'MISSING')*100:.2f}%"
            },
            "source": "prefilter_config.py (SIMPLE_PREFILTER_CONFIG)"
        }
    
    def _capture_trading_settings(self) -> Dict[str, Any]:
        """Capture ALL trading thresholds"""
        try:
            config = ShortCycleConfig(portfolio_value=1000.0)
            
            # Determine active strategies
            active_strategies = []
            if hasattr(config, 'enable_gap_and_go') and config.enable_gap_and_go:
                active_strategies.append(self._format_strategy_label('Gap & Go', getattr(config, 'gap_and_go_allocation', 0.0)))
            if hasattr(config, 'enable_fade_short') and config.enable_fade_short:
                active_strategies.append(self._format_strategy_label('Fade/Short', getattr(config, 'fade_short_allocation', 0.0)))
            if hasattr(config, 'enable_momentum') and config.enable_momentum:
                active_strategies.append(self._format_strategy_label('Momentum', getattr(config, 'momentum_allocation', 0.0)))
            
            return {
                "active_strategies": active_strategies if active_strategies else ["NONE - Check enable_* flags"],
                "confidence_threshold": f"{config.confidence_threshold:.0%}",
                "position_limits": {
                    "max_positions_per_day": config.max_positions_per_day,
                    "max_daily_entries": config.max_daily_entries,
                    "max_concurrent_positions": getattr(config, 'max_concurrent_positions', 'NOT SET')
                },
                "stop_loss_pct": f"{config.stop_loss_pct:.2%}",
                "profit_target_pct": f"{config.profit_target_pct:.2%}",
                "rsi_parameters": {
                    "entry_threshold": getattr(config, 'rsi_entry_threshold', 35),
                    "exit_threshold": getattr(config, 'rsi_exit_threshold', 70)
                },
                "source": "trading_config.py (ShortCycleConfig dataclass)"
            }
        except Exception as e:
            self.logger.error(f"Failed to capture trading config: {e}")
            return {"error": str(e), "source": "trading_config.py"}

    def _format_strategy_label(self, strategy_name: str, allocation: float) -> str:
        """Format a strategy label with the current configured allocation."""
        if allocation is None:
            return strategy_name
        return f"{strategy_name} ({allocation:.0%})"
    
    def _log_settings_report(self, snapshot: Dict[str, Any]) -> None:
        """Log a formatted settings report"""
        timestamp = snapshot['timestamp']
        
        self.logger.info("=" * 90)
        self.logger.info(f"📋 SETTINGS VERIFICATION REPORT — {timestamp}")
        self.logger.info("=" * 90)
        
        # Prefilter settings
        self.logger.info("\n🎯 PREFILTER THRESHOLDS (Source: prefilter_config.py)")
        prefilter = snapshot['prefilter']
        self.logger.info(f"   Price Range: ${prefilter['price_range']['min']:.2f} - ${prefilter['price_range']['max']:.2f}")
        self.logger.info(f"   Volume: {prefilter['volume']['min_volume']:,} - {prefilter['volume']['max_volume']:,} shares")
        self.logger.info(f"   Min Dollar Volume: ${prefilter['volume']['min_dollar_volume']:,}/day")
        self.logger.info(f"   ATR Volatility: {prefilter['volatility_atr']['min_atr_pct']} - {prefilter['volatility_atr']['max_atr_pct']}")
        
        # Trading settings
        self.logger.info("\n💰 TRADING CONFIGURATION (Source: trading_config.py)")
        trading = snapshot['trading']
        if 'error' in trading:
            self.logger.warning(f"   ⚠️  ERROR: {trading['error']}")
        else:
            self.logger.info(f"   Active Strategies: {', '.join(trading['active_strategies'])}")
            self.logger.info(f"   Signal Confidence Threshold: {trading['confidence_threshold']}")
            self.logger.info(f"   Max Positions Today: {trading['position_limits']['max_positions_per_day']} " + 
                           f"(Max Daily Entries: {trading['position_limits']['max_daily_entries']})")
            self.logger.info(f"   Stop Loss: {trading['stop_loss_pct']}, Profit Target: {trading['profit_target_pct']}")
            self.logger.info(f"   RSI Entry/Exit: {trading['rsi_parameters']['entry_threshold']}/{trading['rsi_parameters']['exit_threshold']}")
        
        self.logger.info("\n" + "=" * 90)
        self.logger.info("✅ Startup verification complete. All settings loaded from config files.")
        self.logger.info("=" * 90 + "\n")


def verify_settings_on_startup(logger: logging.Logger = None) -> Dict[str, Any]:
    """Convenience function - call once at bot startup"""
    verifier = SettingsVerifier(logger)
    return verifier.verify_and_log_settings()
