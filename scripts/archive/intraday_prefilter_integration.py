#!/usr/bin/env python3
"""
PreFilter Integration for Intraday Analysis
===========================================
Connects IntradayAnalyzer with existing PreFilter system

This module adds intraday momentum and opening range analysis
to the PreFilter scoring WITHOUT breaking existing logic.

Integration Points:
- Called after basic PreFilter screening
- Adds bonus/penalty to pf_score
- Optional - can be disabled via config
- Respects free tier API limits

Author: LiteBotX Team
Version: 1.0
Date: October 15, 2025
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from intraday_analyzer import IntradayAnalyzer, IntradaySignal

logger = logging.getLogger(__name__)


class IntradayPreFilterEnhancer:
    """
    Enhances PreFilter with intraday analysis
    
    Scoring Impact:
    - Strong intraday signals: +20-30% to pf_score
    - Weak intraday signals: -10-20% from pf_score
    - No data available: No change (graceful fallback)
    
    Free Tier Optimization:
    - Only analyzes symbols that pass basic PreFilter
    - Respects 1000 API calls/day limit
    - Caches results for same trading day
    """
    
    def __init__(self, enabled: bool = True, max_analyses_per_day: int = 50):
        """
        Initialize intraday enhancer
        
        Args:
            enabled: Whether to use intraday analysis
            max_analyses_per_day: Limit on symbols to analyze (conserve API calls)
        """
        self.enabled = enabled
        self.max_analyses_per_day = max_analyses_per_day
        self.analyses_today = 0
        self.last_reset_date = datetime.now().date()
        
        # Cache for intraday signals (same trading day)
        self._signal_cache: Dict[str, IntradaySignal] = {}
        
        # Initialize analyzer
        try:
            self.analyzer = IntradayAnalyzer() if enabled else None
            logger.info(f"✅ IntradayPreFilterEnhancer initialized (enabled={enabled})")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize IntradayAnalyzer: {e}")
            self.analyzer = None
            self.enabled = False
    
    def _reset_daily_counter(self):
        """Reset daily analysis counter if new day"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.analyses_today = 0
            self.last_reset_date = today
            self._signal_cache.clear()
            logger.info(f"📅 Daily counter reset - New trading day: {today}")
    
    def _should_analyze(self, symbol: str) -> bool:
        """Check if we should analyze this symbol"""
        if not self.enabled or self.analyzer is None:
            return False
        
        self._reset_daily_counter()
        
        # Check daily limit
        if self.analyses_today >= self.max_analyses_per_day:
            logger.warning(f"⚠️ Daily analysis limit reached ({self.max_analyses_per_day})")
            return False
        
        # Check cache
        if symbol in self._signal_cache:
            return False  # Already analyzed today
        
        return True
    
    def analyze_symbol(self, symbol: str, current_price: float) -> Optional[IntradaySignal]:
        """
        Analyze a symbol's intraday behavior
        
        Args:
            symbol: Stock ticker
            current_price: Current price
            
        Returns:
            IntradaySignal or None
        """
        if not self._should_analyze(symbol):
            # Return cached if available
            return self._signal_cache.get(symbol)
        
        try:
            signal = self.analyzer.generate_intraday_signal(symbol, current_price)
            
            if signal:
                self._signal_cache[symbol] = signal
                self.analyses_today += 1
                logger.info(f"📊 Analyzed {symbol}: Quality={signal.signal_quality:.2f}, Rec={signal.recommendation}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    def enhance_pf_score(
        self,
        symbol: str,
        original_pf_score: float,
        current_price: float
    ) -> Dict:
        """
        Enhance pf_score with intraday analysis
        
        Args:
            symbol: Stock ticker
            original_pf_score: Original PreFilter score
            current_price: Current stock price
            
        Returns:
            Dict with enhanced_score, adjustment, and signal data
        """
        result = {
            'symbol': symbol,
            'original_score': original_pf_score,
            'enhanced_score': original_pf_score,
            'adjustment': 0.0,
            'adjustment_percent': 0.0,
            'signal_quality': None,
            'recommendation': None,
            'reasons': []
        }
        
        if not self.enabled:
            return result
        
        # Get intraday signal
        signal = self.analyze_symbol(symbol, current_price)
        
        if signal is None:
            # No data available - no adjustment
            logger.debug(f"No intraday data for {symbol} - using original score")
            return result
        
        # Calculate adjustment based on signal quality
        adjustment_factor = 0.0
        
        if signal.recommendation == 'BUY':
            # Strong buy signal: +20-30% boost
            adjustment_factor = 0.20 + (signal.signal_quality * 0.10)
        elif signal.recommendation == 'HOLD':
            # Neutral: small boost if quality good
            adjustment_factor = signal.signal_quality * 0.10
        elif signal.recommendation == 'SKIP':
            # Weak signal: penalty
            adjustment_factor = -0.15 * (1 - signal.signal_quality)
        
        # Apply adjustment
        adjustment = original_pf_score * adjustment_factor
        enhanced_score = original_pf_score + adjustment
        
        # Update result
        result.update({
            'enhanced_score': enhanced_score,
            'adjustment': adjustment,
            'adjustment_percent': adjustment_factor * 100,
            'signal_quality': signal.signal_quality,
            'recommendation': signal.recommendation,
            'reasons': signal.reasons
        })
        
        logger.info(
            f"📈 {symbol}: Score {original_pf_score:.2f} → {enhanced_score:.2f} "
            f"({adjustment_factor*100:+.1f}%) | {signal.recommendation}"
        )
        
        return result
    
    def enhance_candidate_list(
        self,
        candidates: List[Dict],
        price_key: str = 'current_price',
        score_key: str = 'pf_score'
    ) -> List[Dict]:
        """
        Enhance a list of PreFilter candidates
        
        Args:
            candidates: List of candidate dicts with symbol, price, score
            price_key: Key for current price in dict
            score_key: Key for pf_score in dict
            
        Returns:
            Enhanced candidate list (sorted by enhanced score)
        """
        if not self.enabled or not candidates:
            return candidates
        
        logger.info(f"🔍 Enhancing {len(candidates)} candidates with intraday analysis...")
        
        enhanced = []
        
        for candidate in candidates:
            symbol = candidate.get('symbol')
            current_price = candidate.get(price_key)
            original_score = candidate.get(score_key, 0)
            
            if not symbol or current_price is None:
                enhanced.append(candidate)
                continue
            
            # Get enhancement
            result = self.enhance_pf_score(symbol, original_score, current_price)
            
            # Update candidate dict
            enhanced_candidate = candidate.copy()
            enhanced_candidate[score_key] = result['enhanced_score']
            enhanced_candidate['intraday_adjustment'] = result['adjustment']
            enhanced_candidate['intraday_quality'] = result['signal_quality']
            enhanced_candidate['intraday_recommendation'] = result['recommendation']
            enhanced_candidate['intraday_reasons'] = result['reasons']
            
            enhanced.append(enhanced_candidate)
        
        # Re-sort by enhanced score
        enhanced.sort(key=lambda x: x.get(score_key, 0), reverse=True)
        
        logger.info(f"✅ Enhanced {len(enhanced)} candidates")
        
        return enhanced
    
    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        api_stats = self.analyzer.get_api_usage_stats() if self.analyzer else {}
        
        return {
            'enabled': self.enabled,
            'analyses_today': self.analyses_today,
            'max_analyses_per_day': self.max_analyses_per_day,
            'remaining_analyses': self.max_analyses_per_day - self.analyses_today,
            'cached_symbols': len(self._signal_cache),
            'api_usage': api_stats
        }


if __name__ == "__main__":
    # Test the enhancer
    print("🧪 Testing IntradayPreFilterEnhancer...")
    
    enhancer = IntradayPreFilterEnhancer(enabled=True, max_analyses_per_day=10)
    
    # Mock candidate data
    candidates = [
        {'symbol': 'AAPL', 'current_price': 178.50, 'pf_score': 15.5},
        {'symbol': 'MSFT', 'current_price': 380.00, 'pf_score': 14.2},
        {'symbol': 'GOOGL', 'current_price': 140.00, 'pf_score': 13.8},
    ]
    
    print(f"\n📊 Original Candidates:")
    for c in candidates:
        print(f"   {c['symbol']}: Score={c['pf_score']:.2f}, Price=${c['current_price']:.2f}")
    
    # Enhance
    enhanced = enhancer.enhance_candidate_list(candidates)
    
    print(f"\n📈 Enhanced Candidates:")
    for c in enhanced:
        print(f"   {c['symbol']}: Score={c['pf_score']:.2f} "
              f"(adj: {c.get('intraday_adjustment', 0):+.2f}) "
              f"- {c.get('intraday_recommendation', 'N/A')}")
    
    # Show stats
    stats = enhancer.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"   Analyses today: {stats['analyses_today']}/{stats['max_analyses_per_day']}")
    print(f"   Cached symbols: {stats['cached_symbols']}")
    print(f"   API calls: {stats['api_usage'].get('calls_today', 0)}")
