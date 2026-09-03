#!/usr/bin/env python3
"""
Free Sentiment & News Analysis Module
Leverages free resources for sentiment analysis and premarket validation:
1. Alpaca News API (free with account)
2. Reddit Sentiment (free via PRAW)
3. Yahoo Finance News (free via yfinance)
4. Basic technical sentiment indicators
5. Premarket gap analysis
"""

import logging
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import re
import time
from dataclasses import dataclass
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SentimentScore:
    """Sentiment analysis result"""
    symbol: str
    overall_score: float  # -1.0 to 1.0 (-1 = bearish, 0 = neutral, +1 = bullish)
    confidence: float     # 0.0 to 1.0 confidence in the score
    news_count: int
    key_themes: List[str]
    risk_flags: List[str]
    sources: List[str]


@dataclass
class PremarketSignal:
    """Premarket validation signal"""
    symbol: str
    gap_pct: float           # Gap percentage from previous close
    premarket_volume: float  # Premarket volume vs average
    sentiment_score: float   # Overall sentiment
    news_catalyst: bool      # Major news catalyst present
    recommendation: str      # BUY/HOLD/AVOID
    risk_level: str         # LOW/MEDIUM/HIGH
    reasoning: str


class FreeSentimentAnalyzer:
    """
    Sentiment analysis using completely free resources
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Alpaca news client if available
        try:
            api_key = os.getenv('APCA_API_KEY_ID')
            secret = os.getenv('APCA_API_SECRET_KEY')
            if api_key and secret:
                self.news_client = NewsClient(api_key, secret)
                self.logger.info("✅ Alpaca News API initialized")
            else:
                self.news_client = None
                self.logger.warning("⚠️ No Alpaca API keys - using free sources only")
        except Exception as e:
            self.news_client = None
            self.logger.warning(f"⚠️ Alpaca News API unavailable: {e}")
        
        # Sentiment keywords for basic analysis
        self.bullish_keywords = [
            'bullish', 'positive', 'upgrade', 'beat', 'strong', 'growth', 
            'outperform', 'buy', 'rally', 'surge', 'breakout', 'momentum',
            'earnings beat', 'revenue growth', 'guidance raise', 'innovation',
            'partnership', 'acquisition', 'expansion', 'profit'
        ]
        
        self.bearish_keywords = [
            'bearish', 'negative', 'downgrade', 'miss', 'weak', 'decline',
            'underperform', 'sell', 'drop', 'crash', 'breakdown', 'concern',
            'earnings miss', 'revenue decline', 'guidance cut', 'lawsuit',
            'investigation', 'regulatory', 'competition', 'loss'
        ]
        
        self.risk_flags = [
            'investigation', 'lawsuit', 'sec', 'fda', 'recall', 'hack',
            'data breach', 'scandal', 'fraud', 'bankruptcy', 'delisting',
            'class action', 'regulatory action', 'warning letter'
        ]
        
    def get_yahoo_news_sentiment(self, symbol: str) -> Dict:
        """Get news and sentiment from Yahoo Finance (free)"""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return {'sentiment': 0, 'confidence': 0, 'articles': 0, 'themes': []}
            
            sentiment_scores = []
            themes = []
            
            for article in news[:10]:  # Analyze last 10 articles
                title = article.get('title', '').lower()
                summary = article.get('summary', '').lower()
                text = f"{title} {summary}"
                
                # Basic keyword sentiment analysis
                bullish_count = sum(1 for word in self.bullish_keywords if word in text)
                bearish_count = sum(1 for word in self.bearish_keywords if word in text)
                
                if bullish_count > bearish_count:
                    sentiment_scores.append(1)
                elif bearish_count > bullish_count:
                    sentiment_scores.append(-1)
                else:
                    sentiment_scores.append(0)
                
                # Extract themes
                for word in self.bullish_keywords + self.bearish_keywords:
                    if word in text and word not in themes:
                        themes.append(word)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            confidence = min(1.0, len(sentiment_scores) / 5)  # More articles = higher confidence
            
            return {
                'sentiment': avg_sentiment,
                'confidence': confidence,
                'articles': len(news),
                'themes': themes[:5]  # Top 5 themes
            }
            
        except Exception as e:
            self.logger.error(f"❌ Yahoo news error for {symbol}: {e}")
            return {'sentiment': 0, 'confidence': 0, 'articles': 0, 'themes': []}
    
    def get_alpaca_news_sentiment(self, symbol: str) -> Dict:
        """Get news sentiment from Alpaca (free with account)"""
        if not self.news_client:
            return {'sentiment': 0, 'confidence': 0, 'articles': 0, 'themes': []}
        
        try:
            # Get news from last 24 hours
            start_date = datetime.now() - timedelta(days=1)
            
            request = NewsRequest(
                symbols=symbol,  # Pass string directly, not list
                start=start_date,
                limit=20
            )
            
            news_data = self.news_client.get_news(request)
            
            if not news_data:
                return {'sentiment': 0, 'confidence': 0, 'articles': 0, 'themes': []}
            
            sentiment_scores = []
            themes = []
            
            for article in news_data:
                headline = article.headline.lower() if article.headline else ""
                summary = article.summary.lower() if article.summary else ""
                text = f"{headline} {summary}"
                
                # Analyze sentiment
                bullish_count = sum(1 for word in self.bullish_keywords if word in text)
                bearish_count = sum(1 for word in self.bearish_keywords if word in text)
                
                if bullish_count > bearish_count:
                    sentiment_scores.append(1)
                elif bearish_count > bullish_count:
                    sentiment_scores.append(-1)
                else:
                    sentiment_scores.append(0)
                
                # Extract themes
                for word in self.bullish_keywords + self.bearish_keywords:
                    if word in text and word not in themes:
                        themes.append(word)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            confidence = min(1.0, len(sentiment_scores) / 8)
            
            return {
                'sentiment': avg_sentiment,
                'confidence': confidence,
                'articles': len(news_data),
                'themes': themes[:5]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Alpaca news error for {symbol}: {e}")
            return {'sentiment': 0, 'confidence': 0, 'articles': 0, 'themes': []}
    
    def get_technical_sentiment(self, symbol: str, market_data: pd.DataFrame) -> Dict:
        """Generate sentiment from technical indicators (free)"""
        try:
            if len(market_data) < 20:
                return {'sentiment': 0, 'confidence': 0, 'signals': []}
            
            prices = market_data['close']
            volumes = market_data['volume']
            
            signals = []
            sentiment_components = []
            
            # Price momentum
            returns_5d = (prices.iloc[-1] / prices.iloc[-6] - 1) * 100
            returns_10d = (prices.iloc[-1] / prices.iloc[-11] - 1) * 100
            
            if returns_5d > 2:
                signals.append("Strong 5-day momentum")
                sentiment_components.append(0.3)
            elif returns_5d < -2:
                signals.append("Weak 5-day momentum")
                sentiment_components.append(-0.3)
            
            # Volume analysis
            avg_volume = volumes.iloc[-10:].mean()
            recent_volume = volumes.iloc[-1]
            volume_ratio = recent_volume / avg_volume
            
            if volume_ratio > 1.5:
                signals.append("High volume breakout")
                sentiment_components.append(0.2)
            elif volume_ratio < 0.5:
                signals.append("Low volume concern")
                sentiment_components.append(-0.1)
            
            # Moving average position
            ma_20 = prices.iloc[-20:].mean()
            current_price = prices.iloc[-1]
            ma_position = (current_price / ma_20 - 1) * 100
            
            if ma_position > 5:
                signals.append("Above 20-day MA")
                sentiment_components.append(0.2)
            elif ma_position < -5:
                signals.append("Below 20-day MA")
                sentiment_components.append(-0.2)
            
            overall_sentiment = np.mean(sentiment_components) if sentiment_components else 0
            confidence = min(1.0, len(signals) / 3)
            
            return {
                'sentiment': overall_sentiment,
                'confidence': confidence,
                'signals': signals
            }
            
        except Exception as e:
            self.logger.error(f"❌ Technical sentiment error for {symbol}: {e}")
            return {'sentiment': 0, 'confidence': 0, 'signals': []}
    
    def analyze_symbol_sentiment(self, symbol: str, market_data: pd.DataFrame = None) -> SentimentScore:
        """Comprehensive sentiment analysis for a symbol"""
        self.logger.info(f"🔍 Analyzing sentiment for {symbol}...")
        
        # Get sentiment from different sources
        yahoo_sentiment = self.get_yahoo_news_sentiment(symbol)
        alpaca_sentiment = self.get_alpaca_news_sentiment(symbol)
        
        if market_data is not None:
            technical_sentiment = self.get_technical_sentiment(symbol, market_data)
        else:
            technical_sentiment = {'sentiment': 0, 'confidence': 0, 'signals': []}
        
        # Combine sentiments with weights
        sentiments = []
        weights = []
        
        if yahoo_sentiment['confidence'] > 0:
            sentiments.append(yahoo_sentiment['sentiment'])
            weights.append(yahoo_sentiment['confidence'] * 0.4)  # 40% weight for news
        
        if alpaca_sentiment['confidence'] > 0:
            sentiments.append(alpaca_sentiment['sentiment'])
            weights.append(alpaca_sentiment['confidence'] * 0.4)  # 40% weight for news
        
        if technical_sentiment['confidence'] > 0:
            sentiments.append(technical_sentiment['sentiment'])
            weights.append(technical_sentiment['confidence'] * 0.2)  # 20% weight for technicals
        
        # Calculate weighted average
        if sentiments and weights:
            overall_sentiment = np.average(sentiments, weights=weights)
            overall_confidence = np.mean(weights)
        else:
            overall_sentiment = 0
            overall_confidence = 0
        
        # Combine themes and sources
        all_themes = (yahoo_sentiment.get('themes', []) + 
                     alpaca_sentiment.get('themes', []) + 
                     technical_sentiment.get('signals', []))
        
        # Check for risk flags
        risk_flags = []
        all_text = ' '.join(all_themes).lower()
        for flag in self.risk_flags:
            if flag in all_text:
                risk_flags.append(flag)
        
        sources = []
        if yahoo_sentiment['articles'] > 0:
            sources.append(f"Yahoo Finance ({yahoo_sentiment['articles']} articles)")
        if alpaca_sentiment['articles'] > 0:
            sources.append(f"Alpaca News ({alpaca_sentiment['articles']} articles)")
        if technical_sentiment['confidence'] > 0:
            sources.append("Technical Analysis")
        
        return SentimentScore(
            symbol=symbol,
            overall_score=overall_sentiment,
            confidence=overall_confidence,
            news_count=yahoo_sentiment['articles'] + alpaca_sentiment['articles'],
            key_themes=all_themes[:5],
            risk_flags=risk_flags,
            sources=sources
        )


class PremarketValidator:
    """
    Premarket validation using free data sources
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sentiment_analyzer = FreeSentimentAnalyzer()
    
    def get_premarket_data(self, symbol: str) -> Dict:
        """Get premarket gap and volume data (free via yfinance)"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get regular session data
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                return {}
            
            previous_close = hist['Close'].iloc[-2]
            current_price = hist['Close'].iloc[-1]  # Most recent available
            
            # Calculate gap (approximation - yfinance may not have true premarket)
            gap_pct = (current_price / previous_close - 1) * 100
            
            # Volume analysis
            avg_volume = hist['Volume'].iloc[-5:].mean()
            recent_volume = hist['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume
            
            return {
                'previous_close': previous_close,
                'current_price': current_price,
                'gap_pct': gap_pct,
                'volume_ratio': volume_ratio,
                'avg_volume': avg_volume
            }
            
        except Exception as e:
            self.logger.error(f"❌ Premarket data error for {symbol}: {e}")
            return {}
    
    def validate_premarket_signal(self, symbol: str, market_data: pd.DataFrame = None) -> PremarketSignal:
        """Complete premarket validation for a symbol"""
        self.logger.info(f"🌅 Premarket validation for {symbol}...")
        
        # Get premarket data
        premarket_data = self.get_premarket_data(symbol)
        
        # Get sentiment analysis
        sentiment = self.sentiment_analyzer.analyze_symbol_sentiment(symbol, market_data)
        
        # Determine gap and volume
        gap_pct = premarket_data.get('gap_pct', 0)
        volume_ratio = premarket_data.get('volume_ratio', 1)
        
        # Check for news catalyst
        news_catalyst = sentiment.news_count > 2 or len(sentiment.risk_flags) > 0
        
        # Risk assessment
        risk_level = "LOW"
        if abs(gap_pct) > 5 or len(sentiment.risk_flags) > 0:
            risk_level = "HIGH"
        elif abs(gap_pct) > 2 or sentiment.confidence < 0.3:
            risk_level = "MEDIUM"
        
        # Generate recommendation
        recommendation = "HOLD"
        reasoning_parts = []
        
        if sentiment.overall_score > 0.3 and gap_pct > 1 and volume_ratio > 1.2:
            recommendation = "BUY"
            reasoning_parts.append("Positive sentiment + upward gap + volume")
        elif sentiment.overall_score < -0.3 or len(sentiment.risk_flags) > 0:
            recommendation = "AVOID"
            reasoning_parts.append("Negative sentiment or risk flags")
        elif abs(gap_pct) > 5:
            recommendation = "AVOID"
            reasoning_parts.append("Large gap - wait for stability")
        else:
            reasoning_parts.append("No strong premarket signals")
        
        reasoning = "; ".join(reasoning_parts)
        
        return PremarketSignal(
            symbol=symbol,
            gap_pct=gap_pct,
            premarket_volume=volume_ratio,
            sentiment_score=sentiment.overall_score,
            news_catalyst=news_catalyst,
            recommendation=recommendation,
            risk_level=risk_level,
            reasoning=reasoning
        )
    
    def validate_portfolio_premarket(self, symbols: List[str], market_data: Dict = None) -> Dict[str, PremarketSignal]:
        """Validate entire portfolio for premarket trading"""
        self.logger.info(f"🌅 Premarket validation for {len(symbols)} symbols...")
        
        results = {}
        
        for symbol in symbols:
            symbol_market_data = market_data.get(symbol) if market_data else None
            signal = self.validate_premarket_signal(symbol, symbol_market_data)
            results[symbol] = signal
            
            self.logger.info(f"   {symbol}: {signal.recommendation} | Gap: {signal.gap_pct:+.1f}% | "
                           f"Sentiment: {signal.sentiment_score:+.2f} | Risk: {signal.risk_level}")
        
        # Summary statistics
        buy_signals = sum(1 for s in results.values() if s.recommendation == "BUY")
        avoid_signals = sum(1 for s in results.values() if s.recommendation == "AVOID")
        high_risk = sum(1 for s in results.values() if s.risk_level == "HIGH")
        
        self.logger.info(f"📊 Premarket Summary: {buy_signals} BUY, {avoid_signals} AVOID, {high_risk} HIGH RISK")
        
        return results


def demo_sentiment_analysis():
    """Demonstrate the sentiment analysis capabilities"""
    print("🔍 FREE SENTIMENT ANALYSIS DEMONSTRATION")
    print("=" * 60)
    
    analyzer = FreeSentimentAnalyzer()
    validator = PremarketValidator()
    
    # Test symbols
    test_symbols = ['AAPL', 'TSLA', 'MSFT', 'NVDA']
    
    print("📰 SENTIMENT ANALYSIS:")
    print("-" * 40)
    
    for symbol in test_symbols:
        sentiment = analyzer.analyze_symbol_sentiment(symbol)
        
        print(f"\n{symbol}:")
        print(f"  Sentiment: {sentiment.overall_score:+.2f} (confidence: {sentiment.confidence:.1%})")
        print(f"  News Count: {sentiment.news_count}")
        print(f"  Key Themes: {', '.join(sentiment.key_themes[:3])}")
        if sentiment.risk_flags:
            print(f"  ⚠️ Risk Flags: {', '.join(sentiment.risk_flags)}")
        print(f"  Sources: {', '.join(sentiment.sources)}")
    
    print(f"\n🌅 PREMARKET VALIDATION:")
    print("-" * 40)
    
    premarket_results = validator.validate_portfolio_premarket(test_symbols)
    
    for symbol, signal in premarket_results.items():
        print(f"\n{symbol}: {signal.recommendation}")
        print(f"  Gap: {signal.gap_pct:+.1f}% | Volume: {signal.premarket_volume:.1f}x")
        print(f"  Sentiment: {signal.sentiment_score:+.2f} | Risk: {signal.risk_level}")
        print(f"  Reasoning: {signal.reasoning}")
    
    print(f"\n💡 FREE RESOURCES UTILIZED:")
    print("  ✅ Yahoo Finance News (unlimited)")
    print("  ✅ Alpaca News API (free with account)")
    print("  ✅ Technical sentiment indicators")
    print("  ✅ Gap and volume analysis")
    print("  ✅ Risk flag detection")


if __name__ == "__main__":
    demo_sentiment_analysis()
