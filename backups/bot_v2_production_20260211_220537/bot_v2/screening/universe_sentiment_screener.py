"""
Pre-screen the entire stock universe for bad sentiment
Run once at market open (9:30 AM EST)
This prevents trading stocks with disaster news
"""

import logging
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class UniverseSentimentScreener:
    """
    Screen entire universe for disaster news before trading day starts
    """
    
    def __init__(self, sentiment_analyzer, veto_gate, max_workers: int = 10):
        """
        Args:
            sentiment_analyzer: NewsSentimentAnalyzer instance
            veto_gate: SentimentVetoGate instance
            max_workers: Number of parallel API calls
        """
        self.sentiment_analyzer = sentiment_analyzer
        self.veto_gate = veto_gate
        self.max_workers = max_workers
        self.logger = logger
    
    def screen_universe(self, universe: List[str], 
                       hours_lookback: int = 24) -> Dict[str, List]:
        """
        Pre-screen entire universe for bad sentiment
        
        Args:
            universe: List of stock symbols to screen
            hours_lookback: Hours to look back for news
        
        Returns:
            {
                'safe': [...],  # OK to trade
                'risky': {...}, # Negative sentiment (logged as warning)
                'blocked': [...], # Hard veto (disaster news)
            }
        """
        
        self.logger.info(f"🔍 Screening {len(universe)} stocks for sentiment...")
        
        results = {
            'safe': [],
            'risky': {},
            'blocked': [],
        }
        
        # Handle case where sentiment analyzer is disabled
        if not self.sentiment_analyzer or not self.sentiment_analyzer.client:
            self.logger.warning("⚠️  Sentiment analyzer not available - using all stocks as 'safe'")
            return {'safe': universe, 'risky': {}, 'blocked': []}
        
        # Parallel sentiment fetch
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.sentiment_analyzer.get_sentiment,
                    symbol,
                    hours_lookback=hours_lookback
                ): symbol for symbol in universe
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    sentiment = future.result()
                    
                    # Check hard veto
                    should_veto, reason, severity = self.veto_gate.check_veto(sentiment, symbol)
                    
                    if should_veto:
                        results['blocked'].append((symbol, reason))
                        self.logger.warning(f"🚫 BLOCKED {symbol}: {reason}")
                        continue
                    
                    # Classify as safe/risky
                    if sentiment['signal'] in ['STRONG_BULL', 'BULL']:
                        results['safe'].append(symbol)
                    elif sentiment['signal'] == 'NEUTRAL':
                        results['safe'].append(symbol)
                    elif sentiment['signal'] == 'BEAR':
                        # Risky but tradeable with caution
                        results['risky'][symbol] = {
                            'sentiment': sentiment,
                            'reason': f"BEAR sentiment ({sentiment['article_count']} articles)"
                        }
                        self.logger.warning(f"⚠️  RISKY {symbol}: {sentiment['signal']} sentiment")
                    else:  # STRONG_BEAR (shouldn't happen since we check veto above, but handle it)
                        results['blocked'].append((symbol, f"STRONG_BEAR sentiment"))
                        self.logger.warning(f"🚫 BLOCKED {symbol}: STRONG_BEAR sentiment")
                
                except Exception as e:
                    self.logger.error(f"Error screening {symbol}: {e}")
                    # On error, treat as safe (don't block trading due to API issue)
                    results['safe'].append(symbol)
        
        # Log summary
        self.logger.info(f"✅ Safe: {len(results['safe'])}")
        self.logger.info(f"⚠️  Risky: {len(results['risky'])}")
        self.logger.info(f"🚫 Blocked: {len(results['blocked'])}")
        
        if results['blocked']:
            blocked_symbols = [s[0] for s in results['blocked']]
            if len(blocked_symbols) <= 10:
                self.logger.warning(f"   Blocked stocks: {', '.join(blocked_symbols)}")
            else:
                self.logger.warning(f"   Blocked stocks (first 10): {', '.join(blocked_symbols[:10])}")
        
        return results
    
    def get_safe_universe(self, screened_results: Dict) -> List[str]:
        """Get only safe + slightly risky stocks (for trading)"""
        return screened_results['safe'] + list(screened_results['risky'].keys())
    
    def get_very_safe_universe(self, screened_results: Dict) -> List[str]:
        """Get only safe stocks (exclude even slightly risky)"""
        return screened_results['safe']
    
    def get_blocked_universe(self, screened_results: Dict) -> List[Tuple[str, str]]:
        """Get list of blocked stocks with reasons"""
        return screened_results['blocked']
