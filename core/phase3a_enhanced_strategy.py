"""
Phase 3A Enhanced Momentum Strategy
Integrates Enhanced Regime Detection + Signal Confidence with existing strategy
Maximum sophistication with ML-enhanced decision making
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

# Import existing components
from .enhanced_momentum_strategy import EnhancedMomentumStrategy
from .signal_confidence import SignalConfidenceScorer, SignalFeatures, ConfidenceScore
from .regime_detector import RegimeDetector

logger = logging.getLogger("LiteBot")

class Phase3AEnhancedStrategy(EnhancedMomentumStrategy):
    """
    Phase 3A Strategy with ML-Enhanced Features:
    - Enhanced Regime Detection
    - Signal Confidence Scoring
    - Multi-factor Decision Making
    - Risk-Adjusted Position Sizing
    """
    
    def __init__(self, alpha_vantage_key: str, 
                 momentum_short: int = 21, 
                 momentum_long: int = 42,
                 sector_lookback: int = 21,
                 min_confidence: float = 0.6,
                 enable_regime_filtering: bool = True):
        """Initialize Phase 3A enhanced strategy"""
        
        super().__init__(alpha_vantage_key, momentum_short, momentum_long, sector_lookback)
        
        # Phase 3A ML Components
        self.confidence_scorer = SignalConfidenceScorer()
        self.regime_detector = RegimeDetector()
        
        # Phase 3A Parameters
        self.min_confidence = min_confidence
        self.enable_regime_filtering = enable_regime_filtering
        
        # Enhanced weights with confidence factors
        self.enhanced_weights = {
            'base_momentum': 0.25,      # Base momentum signal
            'sector_momentum': 0.20,    # Sector momentum
            'confidence_score': 0.30,   # ML confidence scoring
            'regime_alignment': 0.15,   # Regime detection
            'risk_adjustment': 0.10     # Risk-based adjustment
        }
        
        # Performance tracking
        self.phase3a_signals = []
        self.confidence_history = []
        self.regime_history = []
        
        logger.info("🚀 Phase 3A Enhanced Strategy initialized with ML components")
    
    def generate_phase3a_signals(self, market_data: Dict[str, pd.DataFrame], 
                                portfolio_value: float, 
                                max_positions: int = 10) -> List[Dict]:
        """
        Generate enhanced signals using Phase 3A ML components
        """
        enhanced_signals = []
        
        logger.info(f"🔍 Generating Phase 3A signals for {len(market_data)} symbols")
        
        for symbol, stock_data in market_data.items():
            try:
                if len(stock_data) < 50:  # Need sufficient data
                    continue
                
                # Step 1: Enhanced Regime Detection
                regime_analysis = self._analyze_regime(symbol, stock_data)
                
                # Step 2: Signal Confidence Scoring
                confidence_analysis = self._analyze_confidence(symbol, stock_data, regime_analysis)
                
                # Step 3: Enhanced Signal Generation
                enhanced_signal = self._generate_enhanced_signal(
                    symbol, stock_data, regime_analysis, confidence_analysis, portfolio_value
                )
                
                if enhanced_signal and enhanced_signal['confidence'] >= self.min_confidence:
                    enhanced_signals.append(enhanced_signal)
                    
                    # Track for analysis
                    self.phase3a_signals.append({
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'signal': enhanced_signal
                    })
                
            except Exception as e:
                logger.error(f"Phase 3A signal generation failed for {symbol}: {e}")
                continue
        
        # Sort by enhanced score (confidence * momentum * regime alignment)
        enhanced_signals.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        # Limit positions
        final_signals = enhanced_signals[:max_positions]
        
        logger.info(f"✅ Generated {len(final_signals)} Phase 3A enhanced signals")
        return final_signals
    
    def _analyze_regime(self, symbol: str, stock_data: pd.DataFrame) -> Dict:
        """Analyze market regime for symbol"""
        try:
            regime = self.regime_detector.detect_regime(stock_data)
            
            # Calculate regime score for confidence system
            regime_scores = {
                'bullish': 0.8,
                'volatile': 0.7,
                'bearish': 0.3,
                'sideways': 0.5
            }
            regime_score = regime_scores.get(regime, 0.5)
            
            # Additional regime metrics
            volatility = stock_data['close'].pct_change().std() * np.sqrt(252)
            trend_strength = self._calculate_trend_strength(stock_data)
            
            analysis = {
                'regime': regime,
                'regime_score': regime_score,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'regime_confidence': 0.8 if regime in ['bullish', 'bearish'] else 0.6
            }
            
            # Store for history
            self.regime_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'analysis': analysis
            })
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Regime analysis failed for {symbol}: {e}")
            return {
                'regime': 'sideways',
                'regime_score': 0.5,
                'volatility': 0.25,
                'trend_strength': 0.0,
                'regime_confidence': 0.5
            }
    
    def _analyze_confidence(self, symbol: str, stock_data: pd.DataFrame, 
                          regime_analysis: Dict) -> Dict:
        """Analyze signal confidence using ML scorer"""
        try:
            # Get sector momentum (simplified for now)
            sector_momentum = self._estimate_sector_momentum(stock_data)
            
            # Extract features
            features = self.confidence_scorer.extract_features(
                stock_data, 
                sector_momentum, 
                regime_analysis['regime_score']
            )
            
            # Calculate confidence
            confidence = self.confidence_scorer.calculate_confidence(features)
            
            analysis = {
                'features': features,
                'confidence': confidence,
                'overall_confidence': confidence.overall_confidence,
                'recommendation': confidence.recommendation
            }
            
            # Store for history
            self.confidence_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'analysis': analysis
            })
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Confidence analysis failed for {symbol}: {e}")
            return {
                'overall_confidence': 0.5,
                'recommendation': 'HOLD'
            }
    
    def _generate_enhanced_signal(self, symbol: str, stock_data: pd.DataFrame,
                                regime_analysis: Dict, confidence_analysis: Dict,
                                portfolio_value: float) -> Optional[Dict]:
        """Generate enhanced signal with all Phase 3A factors"""
        
        try:
            current_price = stock_data['close'].iloc[-1]
            
            # Base momentum calculation
            momentum_21d = (current_price / stock_data['close'].iloc[-22] - 1) if len(stock_data) >= 22 else 0
            momentum_42d = (current_price / stock_data['close'].iloc[-43] - 1) if len(stock_data) >= 43 else 0
            
            # Enhanced scoring components
            base_momentum_score = (momentum_21d + momentum_42d) / 2
            regime_score = regime_analysis['regime_score']
            confidence_score = confidence_analysis['overall_confidence']
            
            # Risk adjustment based on volatility and regime
            volatility_penalty = min(0.2, regime_analysis['volatility'] * 0.5)
            risk_adjusted_score = confidence_score * (1 - volatility_penalty)
            
            # Calculate enhanced score (0-1 scale)
            enhanced_score = (
                self.enhanced_weights['base_momentum'] * abs(base_momentum_score) +
                self.enhanced_weights['sector_momentum'] * 0.5 +  # Placeholder
                self.enhanced_weights['confidence_score'] * confidence_score +
                self.enhanced_weights['regime_alignment'] * regime_score +
                self.enhanced_weights['risk_adjustment'] * risk_adjusted_score
            )
            
            # Position sizing based on confidence and volatility
            base_position_size = 0.1  # 10% base position
            confidence_multiplier = confidence_score
            volatility_divisor = max(1.0, regime_analysis['volatility'] * 2)
            
            position_size = base_position_size * confidence_multiplier / volatility_divisor
            position_size = np.clip(position_size, 0.02, 0.15)  # 2-15% position limits
            
            # Only generate signal if meets minimum thresholds
            if (enhanced_score >= 0.6 and 
                confidence_score >= self.min_confidence and
                momentum_21d > 0.01):  # Positive momentum required
                
                signal = {
                    'symbol': symbol,
                    'action': 'BUY',
                    'current_price': current_price,
                    'position_size': position_size,
                    'confidence': confidence_score,
                    'enhanced_score': enhanced_score,
                    'regime': regime_analysis['regime'],
                    'regime_score': regime_score,
                    'momentum_21d': momentum_21d,
                    'momentum_42d': momentum_42d,
                    'volatility': regime_analysis['volatility'],
                    'recommendation': confidence_analysis['recommendation'],
                    'timestamp': datetime.now(),
                    
                    # Phase 3A specific metrics
                    'phase3a_components': {
                        'base_momentum': base_momentum_score,
                        'regime_alignment': regime_score,
                        'ml_confidence': confidence_score,
                        'risk_adjustment': risk_adjusted_score,
                        'enhanced_score': enhanced_score
                    }
                }
                
                logger.info(f"📈 {symbol}: Enhanced signal generated - "
                           f"Score={enhanced_score:.3f}, Confidence={confidence_score:.3f}, "
                           f"Regime={regime_analysis['regime']}")
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Enhanced signal generation failed for {symbol}: {e}")
            return None
    
    def _calculate_trend_strength(self, stock_data: pd.DataFrame) -> float:
        """Calculate trend strength indicator"""
        try:
            if len(stock_data) < 20:
                return 0.0
            
            # Simple trend strength based on price vs moving averages
            current_price = stock_data['close'].iloc[-1]
            sma_20 = stock_data['close'].rolling(20).mean().iloc[-1]
            sma_50 = stock_data['close'].rolling(50).mean().iloc[-1] if len(stock_data) >= 50 else sma_20
            
            trend_20 = (current_price / sma_20 - 1) if sma_20 > 0 else 0
            trend_50 = (current_price / sma_50 - 1) if sma_50 > 0 else 0
            
            return (trend_20 + trend_50) / 2
            
        except:
            return 0.0
    
    def _estimate_sector_momentum(self, stock_data: pd.DataFrame) -> float:
        """Estimate sector momentum (placeholder - can be enhanced with actual sector data)"""
        try:
            # Simple momentum estimate based on stock's own performance
            # In production, this would use actual sector ETF data
            if len(stock_data) < 22:
                return 0.0
            
            sector_proxy = stock_data['close'].rolling(22).mean().pct_change().iloc[-1]
            return sector_proxy if not pd.isna(sector_proxy) else 0.0
            
        except:
            return 0.0
    
    def get_phase3a_performance_summary(self) -> Dict:
        """Get performance summary of Phase 3A enhancements"""
        
        if not self.phase3a_signals:
            return {'status': 'No signals generated yet'}
        
        # Calculate performance metrics
        total_signals = len(self.phase3a_signals)
        avg_confidence = np.mean([s['signal']['confidence'] for s in self.phase3a_signals])
        avg_enhanced_score = np.mean([s['signal']['enhanced_score'] for s in self.phase3a_signals])
        
        # Regime distribution
        regimes = [s['signal']['regime'] for s in self.phase3a_signals]
        regime_counts = pd.Series(regimes).value_counts().to_dict()
        
        # Confidence distribution
        confidence_levels = [s['signal']['confidence'] for s in self.phase3a_signals]
        high_confidence = sum(1 for c in confidence_levels if c >= 0.8)
        medium_confidence = sum(1 for c in confidence_levels if 0.6 <= c < 0.8)
        
        return {
            'total_signals': total_signals,
            'avg_confidence': avg_confidence,
            'avg_enhanced_score': avg_enhanced_score,
            'regime_distribution': regime_counts,
            'confidence_distribution': {
                'high_confidence_signals': high_confidence,
                'medium_confidence_signals': medium_confidence,
                'high_confidence_rate': high_confidence / total_signals if total_signals > 0 else 0
            },
            'latest_signal_time': self.phase3a_signals[-1]['timestamp'] if self.phase3a_signals else None
        }

if __name__ == "__main__":
    print("Phase 3A Enhanced Strategy ready!")
    print("Features: Enhanced Regime Detection + ML Signal Confidence")
    print("Ready for integration with live trading system")
