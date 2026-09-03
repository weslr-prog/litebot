"""
AI-powered market regime detection for strategy adaptation
Extracted from traders/short_cycle_trader.py
"""

import logging
import pandas as pd
from typing import Dict, Any

from bot_v2.config.trading_config import ShortCycleConfig


class AIMarketRegimeDetector:
    """AI-powered market regime detection for strategy adaptation"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIMarketRegimeDetector")
        
        # Import existing regime detector
        try:
            from regime_detector import RegimeDetector
            self.regime_detector = RegimeDetector()
        except ImportError:
            self.regime_detector = None
            self.logger.warning("RegimeDetector not available, using simple regime detection")
    
    def get_current_regime(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get current market regime and suggested adjustments"""
        try:
            if self.regime_detector:
                # Use existing regime detector
                spy_data = market_data.get("SPY")
                if spy_data is not None:
                    regime = self.regime_detector.detect_regime(spy_data)
                else:
                    regime = "NEUTRAL"
            else:
                # Simple regime detection for Sprint 0
                regime = self._simple_regime_detection(market_data)
            
            # Map regime to short-cycle adjustments
            regime_adjustments = self._get_regime_adjustments(regime)
            
            return {
                "regime": regime,
                "adjustments": regime_adjustments,
                "confidence_adjustment": regime_adjustments.get("confidence_threshold", 0.0),
                "position_adjustment": regime_adjustments.get("max_positions_multiplier", 1.0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return {
                "regime": "NEUTRAL",
                "adjustments": {},
                "confidence_adjustment": 0.0,
                "position_adjustment": 1.0
            }
    
    def _simple_regime_detection(self, market_data: Dict[str, pd.DataFrame]) -> str:
        """Simple regime detection based on SPY momentum"""
        spy_data = market_data.get("SPY")
        if spy_data is None or len(spy_data) < 20:
            return "NEUTRAL"
        
        # Simple momentum-based regime
        returns_5d = spy_data['close'].pct_change(5).iloc[-1]
        returns_20d = spy_data['close'].pct_change(20).iloc[-1]
        
        if returns_5d > 0.02 and returns_20d > 0.05:
            return "BULL"
        elif returns_5d < -0.02 and returns_20d < -0.05:
            return "BEAR"
        else:
            return "NEUTRAL"
    
    def _get_regime_adjustments(self, regime: str) -> Dict[str, Any]:
        """Get position and risk adjustments for regime"""
        adjustments = {
            "BULL": {
                "max_positions_multiplier": 1.2,
                "confidence_threshold": -0.05,  # Lower threshold
                "risk_multiplier": 1.1
            },
            "BEAR": {
                "max_positions_multiplier": 0.5,
                "confidence_threshold": 0.1,  # Higher threshold
                "risk_multiplier": 0.8
            },
            "NEUTRAL": {
                "max_positions_multiplier": 1.0,
                "confidence_threshold": 0.0,
                "risk_multiplier": 1.0
            }
        }
        
        return adjustments.get(regime, adjustments["NEUTRAL"])
