"""
Gap-Prone Stock Detector
Purpose: Identify stocks that frequently gap overnight - perfect for D+1 strategy
Author: AI Assistant
Date: October 17, 2025
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GapProneDetector:
    """
    Detects stocks that frequently experience profitable overnight gaps.
    Perfect for buy-today-sell-tomorrow (D+1) strategies.
    """
    
    def __init__(self, 
                 min_gap_frequency: float = 0.30,  # 30% of days must have 1%+ gap
                 min_avg_gap_size: float = 0.015,   # 1.5% average gap
                 min_directional_bias: float = 0.2,  # 20% directional consistency
                 lookback_days: int = 60):           # Analyze last 60 days
        """
        Initialize gap-prone detector.
        
        Args:
            min_gap_frequency: Minimum % of days with significant gaps (1%+)
            min_avg_gap_size: Minimum average gap size (as decimal)
            min_directional_bias: Minimum directional consistency (-1 to 1)
            lookback_days: Number of days to analyze
        """
        self.min_gap_frequency = min_gap_frequency
        self.min_avg_gap_size = min_avg_gap_size
        self.min_directional_bias = min_directional_bias
        self.lookback_days = lookback_days
        
        logger.info(
            f"🌅 GapProneDetector initialized | "
            f"Min freq: {min_gap_frequency*100:.0f}% | "
            f"Min gap: {min_avg_gap_size*100:.1f}% | "
            f"Min bias: {min_directional_bias*100:.0f}%"
        )
    
    def calculate_gap_metrics(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """
        Calculate gap statistics for a single stock.
        
        Args:
            df: DataFrame with OHLC data (must have 'open', 'close' columns)
            
        Returns:
            Dict with gap metrics or None if insufficient data
        """
        try:
            if df.empty or len(df) < 10:
                return None
            
            # Ensure data is sorted by date
            if 'date' in df.columns:
                df = df.sort_values('date').copy()
            
            # Calculate overnight gaps (today's open vs yesterday's close)
            df['prev_close'] = df['close'].shift(1)
            df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
            
            # Remove first row (NaN gap)
            gaps = df['gap'].dropna()
            
            if len(gaps) < 5:
                return None
            
            # Calculate metrics
            abs_gaps = gaps.abs()
            
            # Gap frequency: % of days with 1%+ gap
            significant_gaps = abs_gaps >= 0.01
            gap_frequency = significant_gaps.sum() / len(gaps)
            
            # Average gap size (absolute)
            avg_gap_size = abs_gaps.mean()
            
            # Directional bias: positive = tends to gap up, negative = gap down
            directional_bias = gaps.sum() / abs_gaps.sum() if abs_gaps.sum() > 0 else 0
            
            # Gap consistency: std deviation (lower = more predictable)
            gap_std = abs_gaps.std()
            
            # Recent trend: last 10 days vs overall
            recent_avg = abs_gaps.tail(10).mean() if len(abs_gaps) >= 10 else avg_gap_size
            trend_ratio = recent_avg / avg_gap_size if avg_gap_size > 0 else 1.0
            
            # Max gap in period (risk assessment)
            max_gap = abs_gaps.max()
            
            # Profitable gap rate (gaps that held by close)
            df['gap_profitable'] = (
                ((df['gap'] > 0.01) & (df['close'] > df['open'])) |  # Gap up and close higher
                ((df['gap'] < -0.01) & (df['close'] < df['open']))    # Gap down and close lower
            )
            profitable_gap_rate = df['gap_profitable'].sum() / significant_gaps.sum() if significant_gaps.sum() > 0 else 0
            
            return {
                'gap_frequency': gap_frequency,
                'avg_gap_size': avg_gap_size,
                'directional_bias': directional_bias,
                'gap_std': gap_std,
                'trend_ratio': trend_ratio,
                'max_gap': max_gap,
                'profitable_gap_rate': profitable_gap_rate,
                'sample_size': len(gaps)
            }
            
        except Exception as e:
            logger.error(f"Error calculating gap metrics: {e}")
            return None
    
    def is_gap_prone(self, df: pd.DataFrame, symbol: str = "") -> Tuple[bool, Dict[str, float]]:
        """
        Determine if a stock is gap-prone based on criteria.
        
        Args:
            df: DataFrame with OHLC data
            symbol: Stock symbol (for logging)
            
        Returns:
            Tuple of (is_gap_prone: bool, metrics: dict)
        """
        metrics = self.calculate_gap_metrics(df)
        
        if metrics is None:
            return False, {}
        
        # Check all criteria
        freq_ok = metrics['gap_frequency'] >= self.min_gap_frequency
        size_ok = metrics['avg_gap_size'] >= self.min_avg_gap_size
        bias_ok = abs(metrics['directional_bias']) >= self.min_directional_bias
        
        is_gap_prone = freq_ok and size_ok and bias_ok
        
        if symbol and is_gap_prone:
            logger.debug(
                f"✅ {symbol}: Gap-prone detected | "
                f"Freq: {metrics['gap_frequency']*100:.0f}% | "
                f"Avg: {metrics['avg_gap_size']*100:.1f}% | "
                f"Bias: {metrics['directional_bias']:+.2f}"
            )
        
        return is_gap_prone, metrics
    
    def filter_gap_prone_stocks(self, 
                                data_by_symbol: Dict[str, pd.DataFrame],
                                min_stocks: int = 10,
                                max_stocks: int = 50) -> List[str]:
        """
        Filter stocks to find the most gap-prone candidates.
        
        Args:
            data_by_symbol: Dict mapping symbol -> DataFrame with OHLC data
            min_stocks: Minimum number of stocks to return
            max_stocks: Maximum number of stocks to return
            
        Returns:
            List of symbols sorted by gap-prone score
        """
        try:
            gap_prone_stocks = []
            
            logger.info(f"🌅 Analyzing {len(data_by_symbol)} stocks for gap behavior...")
            
            for symbol, df in data_by_symbol.items():
                is_prone, metrics = self.is_gap_prone(df, symbol)
                
                if is_prone and metrics:
                    # Calculate composite score (higher = better for D+1)
                    score = (
                        metrics['gap_frequency'] * 0.30 +          # 30% weight: frequency
                        metrics['avg_gap_size'] * 10 * 0.25 +      # 25% weight: size
                        abs(metrics['directional_bias']) * 0.20 +  # 20% weight: consistency
                        metrics['profitable_gap_rate'] * 0.25      # 25% weight: profitability
                    )
                    
                    gap_prone_stocks.append({
                        'symbol': symbol,
                        'score': score,
                        **metrics
                    })
            
            if not gap_prone_stocks:
                logger.warning("⚠️ No gap-prone stocks found in universe")
                return []
            
            # Sort by score
            gap_prone_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            # Take top stocks
            selected = gap_prone_stocks[:max_stocks]
            symbols = [s['symbol'] for s in selected]
            
            # Log summary
            if selected:
                top = selected[0]
                logger.info(
                    f"🌅 Found {len(selected)} gap-prone stocks | "
                    f"Top: {top['symbol']} (score: {top['score']:.3f}, "
                    f"freq: {top['gap_frequency']*100:.0f}%, "
                    f"avg: {top['avg_gap_size']*100:.1f}%)"
                )
            
            # Ensure minimum
            if len(symbols) < min_stocks:
                logger.warning(
                    f"⚠️ Only found {len(symbols)} gap-prone stocks "
                    f"(min: {min_stocks}) - relaxing criteria"
                )
                # Return all we found
                return symbols
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error filtering gap-prone stocks: {e}")
            return []
    
    def analyze_gap_opportunity(self, df: pd.DataFrame, symbol: str) -> Dict[str, any]:
        """
        Analyze if current conditions suggest a gap opportunity for tomorrow.
        
        Args:
            df: Recent OHLC data (at least 10 days)
            symbol: Stock symbol
            
        Returns:
            Dict with gap opportunity assessment
        """
        try:
            metrics = self.calculate_gap_metrics(df)
            if not metrics:
                return {'has_opportunity': False, 'reason': 'Insufficient data'}
            
            # Get latest data
            latest = df.iloc[-1] if not df.empty else None
            if latest is None:
                return {'has_opportunity': False, 'reason': 'No latest data'}
            
            # Check for gap setup indicators
            # 1. Recent volume spike (suggests momentum)
            recent_volume = df['volume'].tail(3).mean() if 'volume' in df.columns else 0
            avg_volume = df['volume'].mean() if 'volume' in df.columns else 1
            volume_surge = recent_volume / avg_volume if avg_volume > 0 else 0
            
            # 2. Recent price momentum
            if 'close' in df.columns and len(df) >= 5:
                recent_return = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            else:
                recent_return = 0
            
            # 3. Stock tends to gap in current direction
            positive_bias = metrics['directional_bias'] > 0
            momentum_aligned = (recent_return > 0 and positive_bias) or (recent_return < 0 and not positive_bias)
            
            # Gap opportunity criteria
            has_opportunity = (
                volume_surge >= 1.3 and           # Volume surge
                abs(recent_return) >= 0.02 and    # At least 2% recent move
                metrics['gap_frequency'] >= 0.30 and  # Historically gaps often
                momentum_aligned                   # Momentum aligns with gap bias
            )
            
            opportunity_score = 0
            if has_opportunity:
                opportunity_score = (
                    min(volume_surge / 1.5, 1.0) * 0.30 +
                    min(abs(recent_return) / 0.05, 1.0) * 0.30 +
                    metrics['gap_frequency'] * 0.25 +
                    metrics['profitable_gap_rate'] * 0.15
                )
            
            return {
                'has_opportunity': has_opportunity,
                'opportunity_score': opportunity_score,
                'volume_surge': volume_surge,
                'recent_return': recent_return,
                'gap_frequency': metrics['gap_frequency'],
                'directional_bias': metrics['directional_bias'],
                'profitable_gap_rate': metrics['profitable_gap_rate'],
                'expected_gap_direction': 'UP' if positive_bias else 'DOWN',
                'confidence': 'HIGH' if opportunity_score > 0.7 else 'MEDIUM' if opportunity_score > 0.5 else 'LOW'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing gap opportunity for {symbol}: {e}")
            return {'has_opportunity': False, 'reason': f'Error: {e}'}


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    dates = pd.date_range('2025-08-01', '2025-10-17', freq='D')
    np.random.seed(42)
    
    # Simulate gap-prone stock
    data = {
        'date': dates,
        'open': 100 + np.cumsum(np.random.randn(len(dates)) * 2),
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 2)
    }
    df = pd.DataFrame(data)
    
    # Add some gaps
    for i in range(10, len(df), 7):  # Gap every week
        df.loc[i, 'open'] = df.loc[i-1, 'close'] * 1.02  # 2% gap up
    
    detector = GapProneDetector()
    is_prone, metrics = detector.is_gap_prone(df, "TEST")
    
    print(f"\nTest Stock Analysis:")
    print(f"Is gap-prone: {is_prone}")
    print(f"Metrics: {metrics}")
    
    # Test opportunity
    opportunity = detector.analyze_gap_opportunity(df, "TEST")
    print(f"\nGap Opportunity: {opportunity}")
