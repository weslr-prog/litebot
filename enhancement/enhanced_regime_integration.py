"""
Enhanced Regime Integration Manager - LiteBotX
Purpose: Comprehensive regime-based position sizing, exposure control, and momentum optimization
Integration: Fully connects RegimeDetector to all trading parameters
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import yfinance as yf

logger = logging.getLogger("LiteBot")

# Import existing components (with error handling for standalone testing)
try:
    from regime_detector import RegimeDetector
    REGIME_DETECTOR_AVAILABLE = True
except ImportError:
    REGIME_DETECTOR_AVAILABLE = False
    logger.warning("RegimeDetector not available - using fallback")

try:
    from enhanced_regime_detector import EnhancedRegimeDetector, RegimeClassification
    ENHANCED_REGIME_AVAILABLE = True
except ImportError:
    ENHANCED_REGIME_AVAILABLE = False
    logger.warning("EnhancedRegimeDetector not available - using fallback")

try:
    from risk_per_trade_sizer import RiskPerTradeSizer, RiskPerTradeConfig
    RISK_SIZER_AVAILABLE = True
except ImportError:
    RISK_SIZER_AVAILABLE = False
    logger.warning("RiskPerTradeSizer not available - using fallback")

@dataclass
class RegimeParameters:
    """Comprehensive regime-specific trading parameters"""
    # Capital deployment
    max_exposure_pct: float          # Maximum capital deployment (0.0-1.0)
    
    # Position sizing adjustments
    position_size_multiplier: float  # Multiply base position sizes (0.5-2.0)
    risk_per_trade_multiplier: float # Multiply risk per trade (0.5-2.0)
    
    # Stop-loss adjustments
    stop_loss_multiplier: float      # Multiply stop distances (0.5-3.0)
    
    # Momentum parameters
    momentum_lookback_multiplier: float  # Multiply lookback periods (0.5-2.5)
    momentum_threshold_multiplier: float # Multiply momentum thresholds (0.5-2.0)
    
    # Signal filtering
    min_signal_confidence: float     # Minimum signal confidence (0.0-1.0)
    max_positions: int              # Maximum concurrent positions
    
    # Regime-specific behavior
    allow_new_positions: bool       # Whether to enter new positions
    force_position_reduction: bool  # Whether to reduce existing positions
    enable_short_setups: bool       # Whether to enable short selling

@dataclass
class RegimeShiftEvent:
    """Track regime transitions and their impact"""
    timestamp: datetime
    from_regime: str
    to_regime: str
    confidence: float
    portfolio_adjustment: str  # Description of required adjustment

class EnhancedRegimeIntegrationManager:
    """
    Comprehensive regime integration that optimizes all trading parameters
    based on detected market conditions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize regime detection components (with fallbacks)
        if REGIME_DETECTOR_AVAILABLE:
            self.regime_detector = RegimeDetector()
        else:
            self.regime_detector = None
            
        if ENHANCED_REGIME_AVAILABLE:
            self.enhanced_regime_detector = EnhancedRegimeDetector()
        else:
            self.enhanced_regime_detector = None
        
        # Current regime state
        self.current_regime = "sideways"
        self.regime_confidence = 0.5
        self.regime_classification = None
        self.last_regime_update = None
        
        # Regime transition tracking
        self.regime_history = []
        self.regime_shifts = []
        
        # Initialize regime parameters according to user requirements
        self.regime_parameters = self._initialize_regime_parameters()
        
        logger.info("🌐 Enhanced Regime Integration Manager initialized")
        
    def _initialize_regime_parameters(self) -> Dict[str, RegimeParameters]:
        """Initialize regime-specific parameters based on user requirements"""
        return {
            # BULLISH REGIMES - Deploy ~95% of capital
            "bull": RegimeParameters(
                max_exposure_pct=0.95,           # 95% capital deployment
                position_size_multiplier=1.0,    # Full position sizes
                risk_per_trade_multiplier=1.0,   # Full risk per trade
                stop_loss_multiplier=1.0,        # Normal stop distances
                momentum_lookback_multiplier=0.8, # Shorter lookbacks (faster signals)
                momentum_threshold_multiplier=0.9, # Lower thresholds (easier entry)
                min_signal_confidence=0.4,       # Lower confidence bar
                max_positions=5,                 # Full position count
                allow_new_positions=True,
                force_position_reduction=False,
                enable_short_setups=False
            ),
            
            "UP_LOWVOL": RegimeParameters(
                max_exposure_pct=0.95,           # 95% deployment in stable bull
                position_size_multiplier=1.2,    # Larger positions in stable bull
                risk_per_trade_multiplier=1.1,   # Slightly higher risk tolerance
                stop_loss_multiplier=0.8,        # Tighter stops in stable trend
                momentum_lookback_multiplier=0.7, # Shorter lookbacks for speed
                momentum_threshold_multiplier=0.8, # Easier entry criteria
                min_signal_confidence=0.3,       # Low confidence bar
                max_positions=5,
                allow_new_positions=True,
                force_position_reduction=False,
                enable_short_setups=False
            ),
            
            "UP_HIGHVOL": RegimeParameters(
                max_exposure_pct=0.85,           # Slightly reduced in volatile bull
                position_size_multiplier=0.9,    # Smaller positions due to volatility
                risk_per_trade_multiplier=0.9,   # Reduced risk in volatility
                stop_loss_multiplier=1.2,        # Wider stops for volatility
                momentum_lookback_multiplier=1.0, # Normal lookbacks
                momentum_threshold_multiplier=1.1, # Higher thresholds for quality
                min_signal_confidence=0.5,       # Higher confidence required
                max_positions=4,
                allow_new_positions=True,
                force_position_reduction=False,
                enable_short_setups=False
            ),
            
            # SIDEWAYS REGIMES - Deploy ~50% of capital, widen stops
            "sideways": RegimeParameters(
                max_exposure_pct=0.50,           # 50% capital deployment
                position_size_multiplier=0.6,    # Smaller positions
                risk_per_trade_multiplier=0.7,   # Reduced risk per trade
                stop_loss_multiplier=1.5,        # WIDENED stops per user requirement
                momentum_lookback_multiplier=1.5, # Longer lookbacks for stability
                momentum_threshold_multiplier=1.3, # Higher thresholds
                min_signal_confidence=0.6,       # Higher confidence required
                max_positions=3,                 # Fewer positions
                allow_new_positions=True,
                force_position_reduction=False,
                enable_short_setups=False
            ),
            
            "rangebound": RegimeParameters(
                max_exposure_pct=0.45,           # Reduced exposure in range
                position_size_multiplier=0.5,    # Smaller positions
                risk_per_trade_multiplier=0.6,   # Lower risk
                stop_loss_multiplier=1.8,        # WIDER stops for chop
                momentum_lookback_multiplier=2.0, # Much longer lookbacks
                momentum_threshold_multiplier=1.5, # Much higher thresholds
                min_signal_confidence=0.7,       # High confidence only
                max_positions=2,
                allow_new_positions=True,
                force_position_reduction=False,
                enable_short_setups=False
            ),
            
            # HIGH VOLATILITY - Defensive positioning
            "volatile": RegimeParameters(
                max_exposure_pct=0.30,           # Defensive exposure
                position_size_multiplier=0.4,    # Small positions
                risk_per_trade_multiplier=0.5,   # Half risk
                stop_loss_multiplier=2.0,        # Wide stops for volatility
                momentum_lookback_multiplier=1.8, # Longer lookbacks
                momentum_threshold_multiplier=1.6, # Higher thresholds
                min_signal_confidence=0.8,       # Very high confidence
                max_positions=2,
                allow_new_positions=False,       # Defensive: no new positions
                force_position_reduction=True,   # Reduce existing positions
                enable_short_setups=False
            ),
            
            # BEARISH REGIMES - Deploy 0% (move to cash) or switch to short setups
            "bear": RegimeParameters(
                max_exposure_pct=0.00,           # 0% deployment per user requirement
                position_size_multiplier=0.0,    # No long positions
                risk_per_trade_multiplier=0.0,   # No long risk
                stop_loss_multiplier=1.0,        # N/A for cash
                momentum_lookback_multiplier=2.0, # Long lookbacks if any analysis
                momentum_threshold_multiplier=2.0, # Very high thresholds
                min_signal_confidence=0.95,      # Essentially no trading
                max_positions=0,                 # Cash mode
                allow_new_positions=False,       # No new long positions
                force_position_reduction=True,   # Exit all positions
                enable_short_setups=True         # Enable short setups
            ),
            
            "DOWN_LOWVOL": RegimeParameters(
                max_exposure_pct=0.00,           # Cash mode
                position_size_multiplier=0.0,
                risk_per_trade_multiplier=0.0,
                stop_loss_multiplier=1.0,
                momentum_lookback_multiplier=2.0,
                momentum_threshold_multiplier=2.0,
                min_signal_confidence=0.95,
                max_positions=0,
                allow_new_positions=False,
                force_position_reduction=True,
                enable_short_setups=True
            ),
            
            "DOWN_HIGHVOL": RegimeParameters(
                max_exposure_pct=0.00,           # Full cash in volatile decline
                position_size_multiplier=0.0,
                risk_per_trade_multiplier=0.0,
                stop_loss_multiplier=1.0,
                momentum_lookback_multiplier=3.0,
                momentum_threshold_multiplier=3.0,
                min_signal_confidence=0.99,      # Essentially no trading
                max_positions=0,
                allow_new_positions=False,
                force_position_reduction=True,   # Immediate exit
                enable_short_setups=True
            )
        }
    
    def update_regime_detection(self, market_data: Dict[str, pd.DataFrame]) -> Tuple[str, float]:
        """
        Update regime detection using both simple and enhanced detectors
        Returns (regime, confidence)
        """
        try:
            # Get SPY data for regime analysis
            spy_data = market_data.get('SPY', market_data.get('spy', pd.DataFrame()))
            if spy_data.empty:
                logger.warning("No SPY data for regime detection")
                return self.current_regime, self.regime_confidence
            
            # Simple regime detection
            if self.regime_detector:
                simple_regime = self.regime_detector.detect_regime(spy_data.copy())
            else:
                # Fallback simple regime detection
                simple_regime = self._simple_regime_fallback(spy_data)
            
            # Enhanced regime detection (if enough data)
            enhanced_classification = None
            if len(spy_data) >= 50 and self.enhanced_regime_detector:
                try:
                    enhanced_classification = self.enhanced_regime_detector.classify_market_regime(spy_data.copy())
                    enhanced_regime = enhanced_classification.primary_regime.lower()
                except Exception as e:
                    logger.warning(f"Enhanced regime detection failed: {e}")
                    enhanced_regime = simple_regime
            else:
                enhanced_regime = simple_regime
            
            # Combine regime signals (prefer enhanced if available)
            final_regime = enhanced_regime if enhanced_classification else simple_regime
            
            # Calculate confidence based on consistency and enhanced features
            if enhanced_classification:
                regime_confidence = enhanced_classification.confidence
                self.regime_classification = enhanced_classification
            else:
                # Simple confidence based on regime consistency
                regime_confidence = self._calculate_simple_confidence(spy_data, final_regime)
            
            # Check for regime changes
            if final_regime != self.current_regime:
                self._handle_regime_change(self.current_regime, final_regime, regime_confidence)
            
            # Update current state
            self.current_regime = final_regime
            self.regime_confidence = regime_confidence
            self.last_regime_update = datetime.now()
            
            # Log regime status
            logger.info(f"🌐 Market Regime: {final_regime.upper()} (confidence: {regime_confidence:.1%})")
            if enhanced_classification:
                logger.info(f"   📊 Trend Strength: {enhanced_classification.trend_strength:.2f}")
                logger.info(f"   📈 Volatility: {enhanced_classification.volatility_regime}")
                logger.info(f"   🎯 Market Stress: {enhanced_classification.market_stress:.2f}")
            
            return final_regime, regime_confidence
            
        except Exception as e:
            logger.error(f"Error updating regime detection: {e}")
            return self.current_regime, self.regime_confidence
    
    def _simple_regime_fallback(self, spy_data: pd.DataFrame) -> str:
        """Simple fallback regime detection when main detectors unavailable"""
        try:
            prices = spy_data['close']
            
            # Calculate simple indicators
            sma_20 = prices.rolling(20).mean().iloc[-1]
            sma_50 = prices.rolling(50).mean().iloc[-1] if len(prices) >= 50 else sma_20
            current_price = prices.iloc[-1]
            
            # Recent volatility
            returns = prices.pct_change().dropna()
            recent_vol = returns.tail(20).std() if len(returns) >= 20 else 0.02
            
            # Simple classification
            if current_price > sma_20 > sma_50 and recent_vol < 0.025:
                return "bull"
            elif current_price < sma_20 < sma_50 and recent_vol < 0.025:
                return "bear"
            elif recent_vol > 0.04:
                return "volatile"
            else:
                return "sideways"
                
        except Exception:
            return "sideways"
    
    def _calculate_simple_confidence(self, spy_data: pd.DataFrame, regime: str) -> float:
        """Calculate confidence for simple regime detection"""
        try:
            # Base confidence on price action consistency
            prices = spy_data['close']
            returns = prices.pct_change().dropna()
            
            # Trend consistency
            recent_returns = returns.tail(10)
            trend_consistency = 1.0 - (recent_returns.std() / 0.02)  # Normalize by 2% daily volatility
            trend_consistency = max(0.0, min(1.0, trend_consistency))
            
            # Volume confirmation
            if 'volume' in spy_data.columns:
                volumes = spy_data['volume']
                volume_trend = volumes.rolling(5).mean().iloc[-1] / volumes.rolling(20).mean().iloc[-1]
                volume_confirmation = min(1.0, volume_trend) if volume_trend > 1.0 else max(0.3, volume_trend)
            else:
                volume_confirmation = 0.5
            
            # Combine factors
            confidence = (trend_consistency * 0.7 + volume_confirmation * 0.3)
            return max(0.3, min(0.9, confidence))
            
        except Exception:
            return 0.5
    
    def _handle_regime_change(self, from_regime: str, to_regime: str, confidence: float):
        """Handle regime transition events"""
        shift_event = RegimeShiftEvent(
            timestamp=datetime.now(),
            from_regime=from_regime,
            to_regime=to_regime,
            confidence=confidence,
            portfolio_adjustment=self._get_portfolio_adjustment_description(from_regime, to_regime)
        )
        
        self.regime_shifts.append(shift_event)
        
        logger.warning(f"🔄 REGIME CHANGE: {from_regime.upper()} → {to_regime.upper()}")
        logger.warning(f"   📋 Required Action: {shift_event.portfolio_adjustment}")
        
        # Keep only last 50 regime shifts
        if len(self.regime_shifts) > 50:
            self.regime_shifts = self.regime_shifts[-50:]
    
    def _get_portfolio_adjustment_description(self, from_regime: str, to_regime: str) -> str:
        """Generate description of required portfolio adjustments"""
        from_params = self.regime_parameters.get(from_regime, self.regime_parameters['sideways'])
        to_params = self.regime_parameters.get(to_regime, self.regime_parameters['sideways'])
        
        adjustments = []
        
        # Exposure changes
        exposure_change = to_params.max_exposure_pct - from_params.max_exposure_pct
        if exposure_change > 0.1:
            adjustments.append(f"INCREASE exposure to {to_params.max_exposure_pct:.0%}")
        elif exposure_change < -0.1:
            adjustments.append(f"REDUCE exposure to {to_params.max_exposure_pct:.0%}")
        
        # Position sizing changes
        if to_params.position_size_multiplier < 0.5:
            adjustments.append("REDUCE all position sizes")
        elif to_params.position_size_multiplier > 1.2:
            adjustments.append("INCREASE position sizes")
        
        # Stop-loss changes
        if to_params.stop_loss_multiplier > 1.3:
            adjustments.append("WIDEN stop-losses")
        elif to_params.stop_loss_multiplier < 0.8:
            adjustments.append("TIGHTEN stop-losses")
        
        # Position limits
        if to_params.max_positions < from_params.max_positions:
            adjustments.append(f"REDUCE to {to_params.max_positions} max positions")
        
        # Special actions
        if to_params.force_position_reduction:
            adjustments.append("FORCE position reduction")
        if to_params.enable_short_setups and not from_params.enable_short_setups:
            adjustments.append("ENABLE short setups")
        if not to_params.allow_new_positions:
            adjustments.append("BLOCK new long positions")
        
        return "; ".join(adjustments) if adjustments else "No major adjustments needed"
    
    def get_regime_adjusted_risk_config(self, base_config) -> Dict:
        """Adjust risk-per-trade configuration based on current regime"""
        if self.current_regime not in self.regime_parameters:
            return base_config
        
        regime_params = self.regime_parameters[self.current_regime]
        
        # Handle both RiskPerTradeConfig objects and dictionaries
        if hasattr(base_config, 'risk_per_trade_pct'):
            # RiskPerTradeConfig object
            if RISK_SIZER_AVAILABLE:
                from risk_per_trade_sizer import RiskPerTradeConfig
                adjusted_config = RiskPerTradeConfig(
                    risk_per_trade_pct=base_config.risk_per_trade_pct * regime_params.risk_per_trade_multiplier,
                    max_position_pct=min(base_config.max_position_pct * regime_params.position_size_multiplier, 
                                        regime_params.max_exposure_pct / max(1, regime_params.max_positions)),
                    min_position_pct=base_config.min_position_pct,
                    max_position_value=base_config.max_position_value,
                    min_position_value=base_config.min_position_value,
                    max_stop_loss_pct=base_config.max_stop_loss_pct * regime_params.stop_loss_multiplier,
                    min_stop_loss_pct=base_config.min_stop_loss_pct
                )
            else:
                # Fallback dictionary
                adjusted_config = {
                    'risk_per_trade_pct': base_config.risk_per_trade_pct * regime_params.risk_per_trade_multiplier,
                    'max_position_pct': min(base_config.max_position_pct * regime_params.position_size_multiplier, 
                                          regime_params.max_exposure_pct / max(1, regime_params.max_positions)),
                    'max_stop_loss_pct': base_config.max_stop_loss_pct * regime_params.stop_loss_multiplier
                }
        else:
            # Dictionary config
            adjusted_config = {
                'risk_per_trade_pct': base_config.get('risk_per_trade_pct', 0.02) * regime_params.risk_per_trade_multiplier,
                'max_position_pct': min(base_config.get('max_position_pct', 0.2) * regime_params.position_size_multiplier, 
                                      regime_params.max_exposure_pct / max(1, regime_params.max_positions)),
                'max_stop_loss_pct': base_config.get('max_stop_loss_pct', 0.1) * regime_params.stop_loss_multiplier
            }
        
        logger.info(f"📊 Regime-adjusted risk config:")
        risk_orig = base_config.risk_per_trade_pct if hasattr(base_config, 'risk_per_trade_pct') else base_config.get('risk_per_trade_pct', 0.02)
        risk_adj = adjusted_config.risk_per_trade_pct if hasattr(adjusted_config, 'risk_per_trade_pct') else adjusted_config['risk_per_trade_pct']
        logger.info(f"   Risk per trade: {risk_orig:.1%} → {risk_adj:.1%}")
        
        return adjusted_config
    
    def get_regime_momentum_parameters(self, base_lookback: int, base_threshold: float) -> Tuple[int, float]:
        """Get regime-adjusted momentum parameters"""
        if self.current_regime not in self.regime_parameters:
            return base_lookback, base_threshold
        
        regime_params = self.regime_parameters[self.current_regime]
        
        adjusted_lookback = int(base_lookback * regime_params.momentum_lookback_multiplier)
        adjusted_threshold = base_threshold * regime_params.momentum_threshold_multiplier
        
        logger.info(f"📈 Regime-adjusted momentum:")
        logger.info(f"   Lookback: {base_lookback}d → {adjusted_lookback}d")
        logger.info(f"   Threshold: {base_threshold:.2f} → {adjusted_threshold:.2f}")
        
        return adjusted_lookback, adjusted_threshold
    
    def get_maximum_exposure(self, portfolio_value: float) -> float:
        """Get maximum portfolio exposure for current regime"""
        if self.current_regime not in self.regime_parameters:
            return portfolio_value * 0.5  # Default to 50%
        
        max_exposure_pct = self.regime_parameters[self.current_regime].max_exposure_pct
        max_exposure_value = portfolio_value * max_exposure_pct
        
        logger.info(f"💰 Max exposure: {max_exposure_pct:.0%} = ${max_exposure_value:,.0f}")
        return max_exposure_value
    
    def should_allow_new_positions(self) -> bool:
        """Check if new positions should be allowed in current regime"""
        if self.current_regime not in self.regime_parameters:
            return True
        
        allow = self.regime_parameters[self.current_regime].allow_new_positions
        if not allow:
            logger.warning("🛑 New positions BLOCKED by regime")
        return allow
    
    def should_reduce_positions(self) -> bool:
        """Check if existing positions should be reduced in current regime"""
        if self.current_regime not in self.regime_parameters:
            return False
        
        reduce = self.regime_parameters[self.current_regime].force_position_reduction
        if reduce:
            logger.warning("⚠️ Position reduction REQUIRED by regime")
        return reduce
    
    def should_enable_short_setups(self) -> bool:
        """Check if short setups should be enabled in current regime"""
        if self.current_regime not in self.regime_parameters:
            return False
        
        enable_shorts = self.regime_parameters[self.current_regime].enable_short_setups
        if enable_shorts:
            logger.info("📉 Short setups ENABLED by regime")
        return enable_shorts
    
    def filter_signals_by_regime(self, signals: List[Dict]) -> List[Dict]:
        """Filter trading signals based on regime requirements"""
        if not signals:
            return signals
        
        if self.current_regime not in self.regime_parameters:
            return signals
        
        regime_params = self.regime_parameters[self.current_regime]
        
        # Block new positions if regime doesn't allow
        if not regime_params.allow_new_positions:
            logger.warning("🛑 All signals blocked - regime doesn't allow new positions")
            return []
        
        # Filter by minimum confidence
        min_confidence = regime_params.min_signal_confidence
        high_confidence_signals = [
            signal for signal in signals 
            if signal.get('confidence', 0) >= min_confidence
        ]
        
        # Limit to maximum positions
        max_positions = regime_params.max_positions
        if max_positions == 0:
            logger.warning("🛑 All signals blocked - regime max positions = 0")
            return []
        
        # Sort by confidence and take top signals
        high_confidence_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        filtered_signals = high_confidence_signals[:max_positions]
        
        logger.info(f"🔍 Regime signal filter: {len(signals)} → {len(filtered_signals)} signals")
        logger.info(f"   Min confidence: {min_confidence:.1%}, Max positions: {max_positions}")
        
        return filtered_signals
    
    def get_regime_summary(self) -> Dict:
        """Get comprehensive regime status summary"""
        if self.current_regime not in self.regime_parameters:
            regime_params = self.regime_parameters['sideways']
        else:
            regime_params = self.regime_parameters[self.current_regime]
        
        summary = {
            'current_regime': self.current_regime,
            'confidence': self.regime_confidence,
            'last_update': self.last_regime_update,
            'max_exposure_pct': regime_params.max_exposure_pct,
            'position_size_multiplier': regime_params.position_size_multiplier,
            'risk_multiplier': regime_params.risk_per_trade_multiplier,
            'stop_loss_multiplier': regime_params.stop_loss_multiplier,
            'momentum_lookback_multiplier': regime_params.momentum_lookback_multiplier,
            'min_signal_confidence': regime_params.min_signal_confidence,
            'max_positions': regime_params.max_positions,
            'allow_new_positions': regime_params.allow_new_positions,
            'force_position_reduction': regime_params.force_position_reduction,
            'enable_short_setups': regime_params.enable_short_setups,
            'regime_shifts_today': len([s for s in self.regime_shifts 
                                      if s.timestamp.date() == datetime.now().date()])
        }
        
        # Add enhanced regime details if available
        if self.regime_classification:
            summary.update({
                'trend_strength': self.regime_classification.trend_strength,
                'volatility_regime': self.regime_classification.volatility_regime,
                'market_stress': self.regime_classification.market_stress,
                'regime_stability': self.regime_classification.regime_stability
            })
        
        return summary


def test_regime_integration():
    """Test the regime integration system"""
    print("🧪 Testing Enhanced Regime Integration Manager...")
    
    # Initialize manager
    manager = EnhancedRegimeIntegrationManager()
    
    # Test with mock SPY data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    spy_data = pd.DataFrame({
        'close': 450 + np.cumsum(np.random.normal(0, 10, len(dates))),
        'volume': 50000000 + np.random.normal(0, 5000000, len(dates)),
        'high': 450 + np.cumsum(np.random.normal(0, 10, len(dates))) + 5,
        'low': 450 + np.cumsum(np.random.normal(0, 10, len(dates))) - 5,
        'open': 450 + np.cumsum(np.random.normal(0, 10, len(dates)))
    }, index=dates)
    
    # Test regime detection
    regime, confidence = manager.update_regime_detection({'SPY': spy_data})
    print(f"✅ Detected regime: {regime} (confidence: {confidence:.1%})")
    
    # Test regime parameters
    base_config = {
        'risk_per_trade_pct': 0.02,
        'max_position_pct': 0.2,
        'max_stop_loss_pct': 0.1
    }
    adjusted_config = manager.get_regime_adjusted_risk_config(base_config)
    print(f"✅ Risk config adjusted: {base_config['risk_per_trade_pct']:.1%} → {adjusted_config['risk_per_trade_pct']:.1%}")
    
    # Test momentum parameters
    base_lookback, base_threshold = 20, 0.15
    adj_lookback, adj_threshold = manager.get_regime_momentum_parameters(base_lookback, base_threshold)
    print(f"✅ Momentum adjusted: {base_lookback}d → {adj_lookback}d, {base_threshold:.2f} → {adj_threshold:.2f}")
    
    # Test exposure calculation
    portfolio_value = 1000000
    max_exposure = manager.get_maximum_exposure(portfolio_value)
    print(f"✅ Max exposure: ${max_exposure:,.0f} ({max_exposure/portfolio_value:.0%})")
    
    # Test signal filtering
    mock_signals = [
        {'symbol': 'AAPL', 'confidence': 0.8},
        {'symbol': 'TSLA', 'confidence': 0.6},
        {'symbol': 'NVDA', 'confidence': 0.4},
        {'symbol': 'AMZN', 'confidence': 0.7}
    ]
    filtered_signals = manager.filter_signals_by_regime(mock_signals)
    print(f"✅ Signal filtering: {len(mock_signals)} → {len(filtered_signals)} signals")
    
    # Test regime summary
    summary = manager.get_regime_summary()
    print(f"✅ Regime summary generated with {len(summary)} parameters")
    
    print("🎯 Enhanced Regime Integration Manager test complete!")


if __name__ == "__main__":
    test_regime_integration()
