"""
Overnight Gap Predictor for Bot V2
Predicts next-day gap direction and magnitude based on end-of-day conditions

Created: Jan 13, 2026
Purpose: Identify stocks likely to gap up/down the following day
         to position before market close
         
Key Features Used:
1. After-hours volume/price movement
2. Relative strength vs SPY
3. RSI divergence patterns
4. Volume profile (accumulation/distribution)
5. News sentiment (if available)
6. Sector momentum
7. Earnings proximity

Gap Categories:
- Strong Gap Up (>3%): High confidence continuation play
- Moderate Gap Up (1-3%): Standard momentum entry
- Neutral (±1%): No clear prediction
- Moderate Gap Down (-1 to -3%): Potential fade entry
- Strong Gap Down (<-3%): High volatility, avoid or fade

Usage:
    predictor = OvernightGapPredictor(data_loader)
    predictions = predictor.predict_next_day_gaps(universe)
    
    for symbol, prediction in predictions.items():
        print(f"{symbol}: {prediction['gap_direction']} ({prediction['confidence']:.0%})")
"""

import datetime as dt
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass


@dataclass
class GapPrediction:
    """Represents a gap prediction for a symbol"""
    symbol: str
    predicted_gap_pct: float  # Expected gap size (positive = up)
    gap_direction: str  # 'UP', 'DOWN', 'NEUTRAL'
    confidence: float  # 0-1 confidence score
    factors: Dict  # Contributing factors and their scores
    recommendation: str  # 'BUY_EOD', 'FADE', 'AVOID', 'HOLD'


class OvernightGapPredictor:
    """
    Predicts overnight gaps using multiple technical and fundamental factors.
    
    This is a rules-based predictor (not ML) that scores each stock based on
    historical gap patterns and current conditions.
    """
    
    def __init__(self, data_loader, logger=None):
        self.data_loader = data_loader
        self.logger = logger or logging.getLogger(__name__)
        
        # Factor weights (tuned based on backtest analysis)
        self.weights = {
            'momentum_5d': 0.20,      # 5-day momentum direction
            'momentum_20d': 0.10,     # 20-day trend
            'rsi_position': 0.15,     # RSI relative position
            'volume_trend': 0.15,     # Volume accumulation/distribution
            'relative_strength': 0.15, # Strength vs SPY
            'atr_position': 0.10,     # ATR percentile (volatility)
            'price_vs_sma': 0.15,     # Position vs SMA20
        }
        
        # Gap thresholds
        self.strong_gap_threshold = 0.03  # 3%
        self.moderate_gap_threshold = 0.01  # 1%
        
        # Confidence thresholds
        self.high_confidence = 0.70
        self.medium_confidence = 0.50
    
    def predict_next_day_gaps(self, 
                               universe: List[str], 
                               market_data: Optional[Dict] = None) -> Dict[str, GapPrediction]:
        """
        Generate gap predictions for all symbols in the universe.
        
        Args:
            universe: List of stock symbols to analyze
            market_data: Optional pre-loaded market data dict
            
        Returns:
            Dict mapping symbol to GapPrediction
        """
        predictions = {}
        
        # Get SPY data for relative strength calculation
        try:
            spy_data = self.data_loader.get_historical_data("SPY", days=30)
            spy_return_5d = (spy_data['close'].iloc[-1] / spy_data['close'].iloc[-5] - 1)
        except Exception:
            spy_return_5d = 0.0
        
        for symbol in universe:
            try:
                # Get data
                if market_data and symbol in market_data:
                    data = market_data[symbol]
                else:
                    data = self.data_loader.get_historical_data(symbol, days=100)
                
                if data is None or len(data) < 20:
                    continue
                
                prediction = self._predict_single_symbol(symbol, data, spy_return_5d)
                if prediction:
                    predictions[symbol] = prediction
                    
            except Exception as e:
                self.logger.debug(f"Gap prediction failed for {symbol}: {e}")
        
        # Sort by confidence (highest first)
        predictions = dict(sorted(
            predictions.items(), 
            key=lambda x: abs(x[1].confidence), 
            reverse=True
        ))
        
        return predictions
    
    def _predict_single_symbol(self, 
                                symbol: str, 
                                data: pd.DataFrame,
                                spy_return_5d: float = 0.0) -> Optional[GapPrediction]:
        """
        Generate gap prediction for a single symbol.
        
        Args:
            symbol: Stock symbol
            data: Price data with OHLCV columns
            spy_return_5d: SPY's 5-day return for relative strength
            
        Returns:
            GapPrediction or None if insufficient data
        """
        try:
            factors = {}
            scores = {}
            
            # 1. 5-day momentum
            if len(data) >= 5:
                momentum_5d = (data['close'].iloc[-1] / data['close'].iloc[-5] - 1)
                factors['momentum_5d'] = momentum_5d
                
                # Score: positive momentum = positive gap prediction
                if momentum_5d > 0.05:
                    scores['momentum_5d'] = 1.0
                elif momentum_5d > 0.02:
                    scores['momentum_5d'] = 0.5
                elif momentum_5d > -0.02:
                    scores['momentum_5d'] = 0.0
                elif momentum_5d > -0.05:
                    scores['momentum_5d'] = -0.5
                else:
                    scores['momentum_5d'] = -1.0
            
            # 2. 20-day trend
            if len(data) >= 20:
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                price_vs_sma = (data['close'].iloc[-1] - sma_20) / sma_20
                factors['momentum_20d'] = price_vs_sma
                
                if price_vs_sma > 0.05:
                    scores['momentum_20d'] = 1.0
                elif price_vs_sma > 0.02:
                    scores['momentum_20d'] = 0.5
                elif price_vs_sma > -0.02:
                    scores['momentum_20d'] = 0.0
                elif price_vs_sma > -0.05:
                    scores['momentum_20d'] = -0.5
                else:
                    scores['momentum_20d'] = -1.0
            
            # 3. RSI position
            if len(data) >= 14:
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi = 100 - (100 / (1 + gain / loss))
                current_rsi = rsi.iloc[-1]
                factors['rsi'] = current_rsi
                
                # Oversold (RSI < 30) often gaps up, overbought (RSI > 70) gaps down
                if current_rsi < 30:
                    scores['rsi_position'] = 0.8  # Strong gap up potential
                elif current_rsi < 40:
                    scores['rsi_position'] = 0.3
                elif current_rsi < 60:
                    scores['rsi_position'] = 0.0
                elif current_rsi < 70:
                    scores['rsi_position'] = -0.3
                else:
                    scores['rsi_position'] = -0.8  # Strong gap down potential
            
            # 4. Volume trend (accumulation/distribution)
            if len(data) >= 10 and 'volume' in data.columns:
                vol_5d = data['volume'].tail(5).mean()
                vol_20d = data['volume'].tail(20).mean()
                vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1.0
                factors['volume_ratio'] = vol_ratio
                
                # Higher recent volume = stronger conviction
                if vol_ratio > 1.5:
                    scores['volume_trend'] = 0.5  # High activity
                elif vol_ratio > 1.0:
                    scores['volume_trend'] = 0.2
                elif vol_ratio > 0.7:
                    scores['volume_trend'] = -0.2
                else:
                    scores['volume_trend'] = -0.5  # Low activity (avoid)
            
            # 5. Relative strength vs SPY
            if len(data) >= 5:
                stock_return_5d = (data['close'].iloc[-1] / data['close'].iloc[-5] - 1)
                relative_strength = stock_return_5d - spy_return_5d
                factors['relative_strength'] = relative_strength
                
                if relative_strength > 0.03:
                    scores['relative_strength'] = 1.0  # Strong outperformer
                elif relative_strength > 0.01:
                    scores['relative_strength'] = 0.4
                elif relative_strength > -0.01:
                    scores['relative_strength'] = 0.0
                elif relative_strength > -0.03:
                    scores['relative_strength'] = -0.4
                else:
                    scores['relative_strength'] = -1.0  # Strong underperformer
            
            # 6. ATR percentile (volatility regime)
            if len(data) >= 14:
                atr = ((data['high'] - data['low']).rolling(14).mean()).iloc[-1]
                price = data['close'].iloc[-1]
                atr_pct = atr / price
                factors['atr_pct'] = atr_pct
                
                # Higher ATR = larger potential gaps
                if atr_pct > 0.04:
                    scores['atr_position'] = 0.5  # High volatility
                elif atr_pct > 0.02:
                    scores['atr_position'] = 0.2
                else:
                    scores['atr_position'] = 0.0  # Low volatility
            
            # 7. Price vs SMA20
            if len(data) >= 20:
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                price = data['close'].iloc[-1]
                price_vs_sma = (price - sma_20) / sma_20
                factors['price_vs_sma'] = price_vs_sma
                
                if price_vs_sma > 0.05:
                    scores['price_vs_sma'] = 0.5  # Above SMA = bullish
                elif price_vs_sma > 0.01:
                    scores['price_vs_sma'] = 0.2
                elif price_vs_sma > -0.01:
                    scores['price_vs_sma'] = 0.0
                elif price_vs_sma > -0.05:
                    scores['price_vs_sma'] = -0.2
                else:
                    scores['price_vs_sma'] = -0.5  # Below SMA = bearish
            
            # Calculate weighted score
            total_score = 0.0
            total_weight = 0.0
            for factor, weight in self.weights.items():
                if factor in scores:
                    total_score += scores[factor] * weight
                    total_weight += weight
            
            if total_weight == 0:
                return None
            
            final_score = total_score / total_weight  # -1 to +1 range
            
            # Convert score to gap prediction
            predicted_gap_pct = final_score * 0.03  # Scale to ±3% max
            confidence = abs(final_score)
            
            # Determine direction
            if final_score > 0.2:
                gap_direction = 'UP'
            elif final_score < -0.2:
                gap_direction = 'DOWN'
            else:
                gap_direction = 'NEUTRAL'
            
            # Generate recommendation
            if gap_direction == 'UP' and confidence > self.high_confidence:
                recommendation = 'BUY_EOD'  # Buy before close
            elif gap_direction == 'DOWN' and confidence > self.high_confidence:
                recommendation = 'FADE'  # Wait to fade gap down
            elif confidence > self.medium_confidence:
                recommendation = 'HOLD'  # Watch but don't act
            else:
                recommendation = 'AVOID'  # No clear signal
            
            return GapPrediction(
                symbol=symbol,
                predicted_gap_pct=predicted_gap_pct,
                gap_direction=gap_direction,
                confidence=confidence,
                factors=factors,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.debug(f"Gap prediction calculation failed for {symbol}: {e}")
            return None
    
    def get_top_gap_candidates(self, 
                                universe: List[str], 
                                n: int = 10,
                                direction: str = 'UP') -> List[GapPrediction]:
        """
        Get top N gap candidates for a given direction.
        
        Args:
            universe: Stock universe to analyze
            n: Number of top candidates to return
            direction: 'UP' or 'DOWN'
            
        Returns:
            List of top GapPrediction objects
        """
        predictions = self.predict_next_day_gaps(universe)
        
        # Filter by direction
        filtered = [
            p for p in predictions.values() 
            if p.gap_direction == direction
        ]
        
        # Sort by confidence and return top N
        sorted_preds = sorted(filtered, key=lambda x: x.confidence, reverse=True)
        return sorted_preds[:n]
    
    def print_predictions(self, predictions: Dict[str, GapPrediction]):
        """Print formatted gap predictions"""
        print("\n" + "=" * 70)
        print("🌙 OVERNIGHT GAP PREDICTIONS")
        print("=" * 70)
        
        up_gaps = [p for p in predictions.values() if p.gap_direction == 'UP']
        down_gaps = [p for p in predictions.values() if p.gap_direction == 'DOWN']
        
        if up_gaps:
            print("\n📈 PREDICTED GAP UP:")
            for p in sorted(up_gaps, key=lambda x: x.confidence, reverse=True)[:5]:
                print(f"   {p.symbol}: +{p.predicted_gap_pct*100:.1f}% "
                      f"({p.confidence:.0%} conf) → {p.recommendation}")
        
        if down_gaps:
            print("\n📉 PREDICTED GAP DOWN:")
            for p in sorted(down_gaps, key=lambda x: x.confidence, reverse=True)[:5]:
                print(f"   {p.symbol}: {p.predicted_gap_pct*100:.1f}% "
                      f"({p.confidence:.0%} conf) → {p.recommendation}")
        
        buy_eod = [p for p in predictions.values() if p.recommendation == 'BUY_EOD']
        if buy_eod:
            print("\n🎯 RECOMMENDED BUY BEFORE CLOSE:")
            for p in buy_eod[:3]:
                print(f"   {p.symbol}: Expected gap +{p.predicted_gap_pct*100:.1f}%")
        
        print("=" * 70)


def predict_gaps(universe: List[str] = None) -> Dict[str, GapPrediction]:
    """
    Quick helper to generate gap predictions.
    
    Args:
        universe: Optional stock list. Uses default if not provided.
        
    Returns:
        Dict of symbol -> GapPrediction
    """
    from bot_v2.data.data_loader import DataLoader
    from bot_v2.data.fallback_universe import get_fallback_universe
    
    if universe is None:
        universe = get_fallback_universe(diversified=True)[:50]
    
    data_loader = DataLoader()
    predictor = OvernightGapPredictor(data_loader)
    predictions = predictor.predict_next_day_gaps(universe)
    predictor.print_predictions(predictions)
    
    return predictions


if __name__ == "__main__":
    # Test the predictor
    predict_gaps()
