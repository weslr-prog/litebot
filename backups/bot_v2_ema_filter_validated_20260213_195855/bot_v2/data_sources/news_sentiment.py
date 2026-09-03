"""
Alpaca News Sentiment Analysis
Uses free Alpaca News API to enhance signal confidence
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

logger = logging.getLogger(__name__)


class NewsSentimentAnalyzer:
    """Analyze news sentiment using Alpaca News API (free)"""
    
    def __init__(self):
        """Initialize news client"""
        try:
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                logger.warning("⚠️  Alpaca credentials not found - sentiment disabled")
                self.client = None
                return
            
            self.client = NewsClient(api_key, api_secret)
            # Logging handled by parent signal_generator
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize news client: {e}")
            self.client = None
    
    def get_sentiment(self, symbol: str, hours_lookback: int = 24) -> Dict:
        """
        Get news sentiment for a symbol with data quality assessment
        
        Args:
            symbol: Stock symbol
            hours_lookback: How many hours to look back (default: 24)
            
        Returns:
            {
                'sentiment_score': 0.73,  # -1 to +1
                'article_count': 5,
                'confidence': 'high',  # low/medium/high
                'data_quality': 'high',  # missing/low/medium/high
                'quality_confidence': 0.9,  # 0-1, how much to trust this data
                'latest_article_age_hours': 2.5,  # How old is newest article
                'stale_penalty': -0.05,  # Penalty for old data
                'signal': 'BULLISH',  # STRONG_BULL/BULL/NEUTRAL/BEAR/STRONG_BEAR
                'confidence_adjustment': 0.10,  # Adjustment to signal confidence
                'headlines': [...]
            }
        """
        if not self.client:
            return self._neutral_response()
        
        try:
            # Fetch news from last N hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_lookback)
            
            request = NewsRequest(
                symbols=symbol,
                start=start_time,
                end=end_time,
                limit=50
            )
            
            news = self.client.get_news(request)
            
            # NEW: Assess data quality
            article_count = len(news.data) if news and news.data else 0
            
            # Data quality classification
            if article_count == 0:
                data_quality = 'missing'
            elif article_count == 1:
                data_quality = 'low'  # Single data point is unreliable
            elif article_count <= 3:
                data_quality = 'medium'
            else:
                data_quality = 'high'  # 4+ articles = reliable
            
            # If no articles, return neutral with missing flag
            if not news or len(news.data) == 0:
                logger.debug(f"{symbol}: No news articles found")
                return {
                    'sentiment_score': 0.0,
                    'article_count': 0,
                    'confidence': 'low',
                    'data_quality': 'missing',
                    'quality_confidence': 0.0,
                    'latest_article_age_hours': None,
                    'stale_penalty': 0.0,
                    'signal': 'NEUTRAL',
                    'confidence_adjustment': 0.0,
                    'headlines': []
                }
            
            # Calculate sentiment
            articles = news.data
            sentiments = []
            headlines = []
            article_times = []
            
            for article in articles:
                # Alpaca news has sentiment field (-1 to +1)
                if hasattr(article, 'sentiment') and article.sentiment is not None:
                    sentiments.append(article.sentiment)
                    headlines.append({
                        'headline': article.headline,
                        'sentiment': article.sentiment,
                        'url': article.url if hasattr(article, 'url') else '',
                        'created_at': str(article.created_at) if hasattr(article, 'created_at') else ''
                    })
                    if hasattr(article, 'created_at'):
                        article_times.append(article.created_at)
            
            if not sentiments:
                return self._neutral_response()
            
            # Calculate aggregate sentiment
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            # NEW: Check article staleness
            if article_times:
                latest_article_time = max(article_times)
                # Handle both naive and timezone-aware datetimes
                if latest_article_time.tzinfo is None:
                    now = datetime.now()
                else:
                    now = datetime.now(latest_article_time.tzinfo)
                age_hours = (now - latest_article_time).total_seconds() / 3600
            else:
                age_hours = float('inf')
            
            # Penalty for stale news
            if age_hours > 24:
                stale_penalty = -0.15  # Very stale, not current
            elif age_hours > 12:
                stale_penalty = -0.10  # Getting stale
            elif age_hours > 6:
                stale_penalty = -0.05  # Slightly stale
            else:
                stale_penalty = 0.0  # Current
            
            # Classify sentiment
            if avg_sentiment > 0.6:
                signal = 'STRONG_BULL'
                confidence_adjustment = 0.15
                confidence = 'high'
            elif avg_sentiment > 0.3:
                signal = 'BULL'
                confidence_adjustment = 0.10
                confidence = 'medium'
            elif avg_sentiment < -0.6:
                signal = 'STRONG_BEAR'
                confidence_adjustment = -1.0  # Skip trade
                confidence = 'high'
            elif avg_sentiment < -0.3:
                signal = 'BEAR'
                confidence_adjustment = -0.5  # Significantly reduce confidence
                confidence = 'medium'
            else:
                signal = 'NEUTRAL'
                confidence_adjustment = 0.0
                confidence = 'low'
            
            # Apply stale penalty to adjustment
            final_adjustment = confidence_adjustment + stale_penalty
            
            # NEW: Quality confidence - how much should we trust this sentiment?
            # High quality + current = 1.0
            # Low quality + stale = 0.3
            if data_quality == 'high' and age_hours < 6:
                quality_confidence = 1.0
            elif data_quality == 'high' and age_hours < 12:
                quality_confidence = 0.9
            elif data_quality == 'medium' and age_hours < 12:
                quality_confidence = 0.7
            elif data_quality == 'medium' and age_hours < 24:
                quality_confidence = 0.5
            elif data_quality == 'low':
                quality_confidence = 0.4
            else:
                quality_confidence = 0.3
            
            logger.debug(f"{symbol} News: {article_count} articles, sentiment={avg_sentiment:.2f}, "
                        f"signal={signal}, data_quality={data_quality}, age={age_hours:.1f}h")
            
            return {
                'sentiment_score': avg_sentiment,
                'article_count': article_count,
                'confidence': confidence,
                'data_quality': data_quality,
                'quality_confidence': quality_confidence,
                'latest_article_age_hours': age_hours,
                'stale_penalty': stale_penalty,
                'signal': signal,
                'confidence_adjustment': final_adjustment,
                'headlines': headlines[:min(5, len(headlines))]  # Top 5 headlines
            }
            
        except Exception as e:
            logger.debug(f"{symbol}: Error fetching news sentiment: {e}")
            return self._neutral_response()
    
    def _neutral_response(self) -> Dict:
        """Return neutral sentiment when no data available"""
        return {
            'sentiment_score': 0.0,
            'article_count': 0,
            'confidence': 'low',
            'data_quality': 'missing',
            'quality_confidence': 0.0,
            'latest_article_age_hours': None,
            'stale_penalty': 0.0,
            'signal': 'NEUTRAL',
            'confidence_adjustment': 0.0,
            'headlines': []
        }
    
    def should_skip_trade(self, sentiment: Dict, strategy: str = 'momentum') -> bool:
        """
        Check if trade should be skipped based on sentiment
        
        Args:
            sentiment: Sentiment dict from get_sentiment()
            strategy: 'momentum' or 'mean_reversion' - changes logic
            
        Returns:
            True if trade should be skipped
        """
        if strategy == 'mean_reversion':
            # For mean reversion: skip if TOO bullish (stock already rallying, not oversold)
            # Mildly bearish is actually GOOD (oversold condition)
            # Only skip on STRONG_BEAR (disaster news like fraud, bankruptcy)
            return sentiment['signal'] == 'STRONG_BEAR'
        else:
            # For momentum: skip on any bearish sentiment
            return sentiment['signal'] in ['STRONG_BEAR', 'BEAR']
    
    def get_sentiment_adjustment(self, sentiment: Dict, strategy: str = 'gap_go',
                                has_dark_pool_buying: bool = False) -> float:
        """
        Get confidence adjustment based on sentiment and strategy type
        
        Args:
            sentiment: Sentiment dict from get_sentiment()
            strategy: 'gap_go' | 'fade_short' | 'mean_reversion'
            has_dark_pool_buying: If dark pool shows accumulation
        
        Returns:
            Confidence adjustment (-1.0 to +0.25)
        """
        signal = sentiment['signal']
        
        # ===== GAP & GO STRATEGY =====
        if strategy == 'gap_go':
            # Need momentum + bullish sentiment
            if signal == 'STRONG_BEAR':
                return -1.0  # Hard skip - fight momentum
            if signal == 'BEAR':
                return -0.25  # Bad news kills momentum
            if signal == 'NEUTRAL':
                return 0.0  # No signal, no penalty
            if signal == 'BULL':
                return 0.10  # Good - supports momentum
            if signal == 'STRONG_BULL':
                return 0.20  # Perfect - strong bullish signal
        
        # ===== FADE/SHORT STRATEGY =====
        elif strategy == 'fade_short':
            # Betting on reversal from extended move
            if signal == 'STRONG_BEAR':
                return -1.0  # Skip - avoid free fall shorts
            if signal == 'BEAR':
                return 0.0   # Neutral - actually supportive (stock weak)
            if signal == 'NEUTRAL':
                return 0.0
            if signal == 'BULL':
                return -0.10  # Bad - rally strengthening
            if signal == 'STRONG_BULL':
                return -0.25  # Very bad - avoid shorting into strength
        
        # ===== MEAN REVERSION STRATEGY =====
        elif strategy == 'mean_reversion':
            # Smart money buying the dip
            if signal == 'STRONG_BEAR':
                return -1.0  # Skip - too much risk
            if signal == 'BEAR':
                # Oversold - mean reversion setup
                if has_dark_pool_buying:
                    return 0.20  # Smart money buying dip = high confidence
                else:
                    return -0.05  # Risky without institutional support
            if signal == 'NEUTRAL':
                return 0.0
            if signal == 'BULL':
                return -0.10  # Already recovering, less reversal potential
            if signal == 'STRONG_BULL':
                return -0.15  # Too strong to mean revert
        
        # Default fallback
        return 0.0
    
    def get_contrarian_adjustment(self, sentiment: Dict, has_dark_pool_buying: bool = False) -> float:
        """
        DEPRECATED: Use get_sentiment_adjustment() instead
        
        This method is kept for backward compatibility.
        Defaults to mean_reversion strategy for legacy code.
        """
        return self.get_sentiment_adjustment(sentiment, strategy='mean_reversion',
                                             has_dark_pool_buying=has_dark_pool_buying)
    
    def format_sentiment_log(self, symbol: str, sentiment: Dict) -> str:
        """Format sentiment for logging"""
        if sentiment['article_count'] == 0:
            return f"{symbol}: No recent news"
        
        signal_emoji = {
            'STRONG_BULL': '🚀',
            'BULL': '📈',
            'NEUTRAL': '➡️',
            'BEAR': '📉',
            'STRONG_BEAR': '💀'
        }
        
        emoji = signal_emoji.get(sentiment['signal'], '❓')
        score = sentiment['sentiment_score']
        count = sentiment['article_count']
        adj = sentiment['confidence_adjustment']
        
        msg = f"{symbol}: {emoji} {sentiment['signal']} (score={score:.2f}, {count} articles"
        if adj != 0:
            msg += f", confidence {adj:+.0%}"
        msg += ")"
        
        return msg
