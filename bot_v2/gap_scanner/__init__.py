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
        
        NOTE: This feature is currently disabled as it requires real-time market data API.
        Will be implemented in future enhancement phase.
        
        Args:
            candidate_symbols: List of symbols from pre-filter
            
        Returns:
            Dict mapping symbol -> gap analysis (currently returns empty dict)
        """
        try:
            if not self.data_loader:
                logger.debug("No data loader - cannot scan premarket gaps")
                return {}
            
            # Check if data loader has API access
            if not hasattr(self.data_loader, '_alpaca_client') or not self.data_loader._alpaca_client:
                logger.debug("Alpaca API not available - skipping gap scan")
                return {}
            
            # For now, skip live gap scanning since it requires market hours and proper API setup
            # This feature can be enhanced later with proper quote API during market hours
            logger.debug("📊 Gap scanning requires market hours - feature disabled for now")
            return {}
            
        except Exception as e:
            logger.debug(f"Gap scan error (non-critical): {e}")
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
