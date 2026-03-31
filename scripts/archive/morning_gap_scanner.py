"""
Morning Gap Scanner - Fresh Data at 9 AM
Purpose: Analyze stocks at market open with real-time data to capture gaps
Author: AI Assistant  
Date: October 17, 2025
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MorningGapScanner:
    """
    Scans stocks at 9:00-9:30 AM to identify gap opportunities with fresh data.
    Uses FREE Alpaca API for real-time snapshots.
    """
    
    def __init__(self, data_loader=None):
        """
        Initialize morning gap scanner.
        
        Args:
            data_loader: DataLoader instance for API access
        """
        self.data_loader = data_loader
        logger.info("🌅 MorningGapScanner initialized for fresh 9 AM analysis")
    
    def scan_premarket_gaps(self, candidate_symbols: List[str]) -> Dict[str, Dict]:
        """
        Scan candidates at 9:00-9:30 AM for gap opportunities.
        Uses Alpaca snapshot API (FREE) for real-time data.
        
        Args:
            candidate_symbols: List of symbols from pre-filter
            
        Returns:
            Dict mapping symbol -> gap analysis
        """
        try:
            if not self.data_loader:
                logger.warning("No data loader - cannot scan premarket gaps")
                return {}
            
            logger.info(f"🔍 Scanning {len(candidate_symbols)} stocks for morning gaps...")
            
            gap_analysis = {}
            
            # Get snapshots from Alpaca (FREE API)
            try:
                # Use Alpaca's get_latest_quotes for real-time data
                quotes = self.data_loader.api.get_latest_quotes(candidate_symbols)
                
                for symbol in candidate_symbols:
                    try:
                        if symbol not in quotes:
                            continue
                        
                        quote = quotes[symbol]
                        current_price = float(quote.ap)  # Ask price (current)
                        
                        # Get previous close
                        bars = self.data_loader.api.get_bars(
                            symbol, 
                            '1Day',
                            limit=2
                        ).df
                        
                        if bars.empty or len(bars) < 2:
                            continue
                        
                        prev_close = float(bars.iloc[-2]['close'])
                        
                        # Calculate gap
                        gap_pct = (current_price - prev_close) / prev_close
                        gap_dollars = current_price - prev_close
                        
                        # Get current volume (if available)
                        current_volume = 0
                        try:
                            trades = self.data_loader.api.get_latest_trades([symbol])
                            if symbol in trades:
                                current_volume = trades[symbol].s
                        except:
                            pass
                        
                        # Analyze gap quality
                        gap_quality = self._assess_gap_quality(
                            gap_pct, 
                            current_price, 
                            prev_close,
                            current_volume
                        )
                        
                        gap_analysis[symbol] = {
                            'current_price': current_price,
                            'prev_close': prev_close,
                            'gap_pct': gap_pct,
                            'gap_dollars': gap_dollars,
                            'gap_direction': 'UP' if gap_pct > 0 else 'DOWN',
                            'gap_quality': gap_quality,
                            'timestamp': datetime.now(),
                            'volume': current_volume
                        }
                        
                        if abs(gap_pct) >= 0.01:  # 1%+ gap
                            logger.info(
                                f"🌅 {symbol}: Gap {gap_pct*100:+.1f}% "
                                f"(${prev_close:.2f} → ${current_price:.2f}) "
                                f"Quality: {gap_quality}"
                            )
                    
                    except Exception as e:
                        logger.debug(f"Error analyzing {symbol}: {e}")
                        continue
                
                logger.info(f"✅ Found {len(gap_analysis)} stocks with gap data")
                return gap_analysis
                
            except Exception as e:
                logger.error(f"Error fetching snapshots: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in scan_premarket_gaps: {e}")
            return {}
    
    def _assess_gap_quality(self, gap_pct: float, current: float, 
                           prev_close: float, volume: int) -> str:
        """
        Assess quality of gap for trading.
        
        Returns:
            'EXCELLENT', 'GOOD', 'MODERATE', 'POOR'
        """
        try:
            abs_gap = abs(gap_pct)
            
            # Excellent: 1.5-3% gap (sweet spot for D+1)
            if 0.015 <= abs_gap <= 0.03:
                return 'EXCELLENT'
            
            # Good: 1-1.5% or 3-4%
            elif 0.01 <= abs_gap < 0.015 or 0.03 < abs_gap <= 0.04:
                return 'GOOD'
            
            # Moderate: 0.5-1% or 4-5%
            elif 0.005 <= abs_gap < 0.01 or 0.04 < abs_gap <= 0.05:
                return 'MODERATE'
            
            # Poor: Too small (<0.5%) or too large (>5% = risky)
            else:
                return 'POOR'
                
        except:
            return 'UNKNOWN'
    
    def filter_tradeable_gaps(self, gap_analysis: Dict[str, Dict],
                             max_selections: int = 8) -> List[str]:
        """
        Filter gaps to find best trading candidates.
        
        Args:
            gap_analysis: Gap data from scan_premarket_gaps
            max_selections: Maximum stocks to return
            
        Returns:
            List of symbols sorted by opportunity score
        """
        try:
            candidates = []
            
            for symbol, data in gap_analysis.items():
                gap_pct = data['gap_pct']
                quality = data['gap_quality']
                
                # Skip poor quality gaps
                if quality == 'POOR':
                    continue
                
                # Score the opportunity
                score = 0
                
                # 1. Gap size score (prefer 1.5-3% sweet spot)
                abs_gap = abs(gap_pct)
                if 0.015 <= abs_gap <= 0.03:
                    score += 50
                elif 0.01 <= abs_gap < 0.015:
                    score += 35
                elif 0.03 < abs_gap <= 0.04:
                    score += 30
                else:
                    score += 10
                
                # 2. Direction score (prefer gap ups for long positions)
                if gap_pct > 0:
                    score += 20
                
                # 3. Quality score
                quality_scores = {
                    'EXCELLENT': 30,
                    'GOOD': 20,
                    'MODERATE': 10,
                    'POOR': 0
                }
                score += quality_scores.get(quality, 0)
                
                candidates.append({
                    'symbol': symbol,
                    'score': score,
                    'gap_pct': gap_pct,
                    'quality': quality,
                    'current_price': data['current_price']
                })
            
            # Sort by score
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Take top candidates
            selected = candidates[:max_selections]
            symbols = [c['symbol'] for c in selected]
            
            if selected:
                logger.info(f"🎯 Selected {len(symbols)} gap candidates:")
                for c in selected[:5]:  # Log top 5
                    logger.info(
                        f"   {c['symbol']}: Gap {c['gap_pct']*100:+.1f}% "
                        f"(Score: {c['score']}, Quality: {c['quality']})"
                    )
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error filtering gaps: {e}")
            return []
    
    def get_gap_opportunity_score(self, symbol: str, 
                                  gap_analysis: Dict[str, Dict]) -> float:
        """
        Get opportunity score for a specific symbol.
        
        Returns:
            Score 0-100 (higher = better opportunity)
        """
        try:
            if symbol not in gap_analysis:
                return 0.0
            
            data = gap_analysis[symbol]
            gap_pct = abs(data['gap_pct'])
            quality = data['gap_quality']
            
            # Base score from gap size
            if 0.015 <= gap_pct <= 0.03:
                score = 80
            elif 0.01 <= gap_pct < 0.015:
                score = 65
            elif 0.03 < gap_pct <= 0.04:
                score = 60
            else:
                score = 30
            
            # Adjust for quality
            quality_adj = {
                'EXCELLENT': 1.2,
                'GOOD': 1.0,
                'MODERATE': 0.8,
                'POOR': 0.5
            }
            score *= quality_adj.get(quality, 0.8)
            
            # Cap at 100
            return min(score, 100.0)
            
        except:
            return 0.0


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scanner = MorningGapScanner()
    
    # Simulate gap data
    test_gaps = {
        'AAPL': {
            'current_price': 178.50,
            'prev_close': 175.00,
            'gap_pct': 0.02,  # 2% gap up
            'gap_quality': 'EXCELLENT',
            'volume': 1000000
        },
        'TSLA': {
            'current_price': 255.00,
            'prev_close': 250.00,
            'gap_pct': 0.02,  # 2% gap up
            'gap_quality': 'GOOD',
            'volume': 500000
        }
    }
    
    selected = scanner.filter_tradeable_gaps(test_gaps, max_selections=5)
    print(f"\nSelected symbols: {selected}")
