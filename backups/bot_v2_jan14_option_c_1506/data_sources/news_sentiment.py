"""
Alpaca News Sentiment Analysis
Uses free Alpaca News API to enhance signal confidence
"""

import os
import logging
from typing import Dict, List, Optional
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
        Get news sentiment for a symbol
        
        Args:
            symbol: Stock symbol
            hours_lookback: How many hours to look back (default: 24)
            
        Returns:
            {
                'sentiment_score': 0.73,  # -1 to +1
                'article_count': 5,
                'confidence': 'high',  # low/medium/high
                'signal': 'BULLISH',  # STRONG_BULL/BULL/NEUTRAL/BEAR/STRONG_BEAR
                'confidence_adjustment': 0.10,  # Adjustment to signal confidence
                'headlines': [...]
            }
        """
        if not self.client:
            return self._neutral_response()
        
        try:
            # Fetch news from last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_lookback)
            
            request = NewsRequest(
                symbols=symbol,
                start=start_time,
                end=end_time,
                limit=50
            )
            
            news = self.client.get_news(request)
            
            if not news or len(news.data) == 0:
                logger.debug(f"{symbol}: No news articles found")
                return self._neutral_response()
            
            # Calculate sentiment
            articles = news.data
            sentiments = []
            headlines = []
            
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
            
            if not sentiments:
                return self._neutral_response()
            
            # Calculate aggregate sentiment
            avg_sentiment = sum(sentiments) / len(sentiments)
            article_count = len(articles)
            
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
            
            logger.debug(f"{symbol} News: {article_count} articles, sentiment={avg_sentiment:.2f}, signal={signal}")
            
            return {
                'sentiment_score': avg_sentiment,
                'article_count': article_count,
                'confidence': confidence,
                'signal': signal,
                'confidence_adjustment': confidence_adjustment,
                'headlines': headlines[:min(5, len(headlines))]  # Top 5 headlines (safe slicing)
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
    
    def get_contrarian_adjustment(self, sentiment: Dict, has_dark_pool_buying: bool = False) -> float:
        """
        Get confidence adjustment for mean reversion (contrarian) strategy
        
        For mean reversion, the ideal setup is:
        - Mildly negative sentiment (retail selling, creating oversold)
        - Dark pool accumulation (smart money buying the dip)
        
        Args:
            sentiment: Sentiment dict from get_sentiment()
            has_dark_pool_buying: Whether dark pool shows institutional buying
            
        Returns:
            Confidence adjustment (-1.0 to +0.20)
        """
        signal = sentiment['signal']
        
        # STRONG_BEAR: Skip completely (disaster news)
        if signal == 'STRONG_BEAR':
            return -1.0
        
        # BEAR + Dark Pool: IDEAL contrarian setup! Smart money buying the dip
        if signal == 'BEAR' and has_dark_pool_buying:
            return 0.20  # Strong boost
        
        # BEAR alone: Risky, slight negative
        if signal == 'BEAR':
            return -0.05
        
        # NEUTRAL: No adjustment
        if signal == 'NEUTRAL':
            return 0.0
        
        # BULL: Stock already recovering, less mean reversion potential
        if signal == 'BULL':
            return -0.05  # Slight penalty
        
        # STRONG_BULL: Stock is rallying, NOT oversold - bad for mean reversion
        if signal == 'STRONG_BULL':
            return -0.15  # Significant penalty
        
        return 0.0
    
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
