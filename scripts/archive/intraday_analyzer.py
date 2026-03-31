#!/usr/bin/env python3
"""
Intraday Data Analyzer for LiteBotX
====================================
FREE TIER optimization using Alpaca's free 5-minute bars

Features:
- Opening range breakout detection (9:30-10:00 AM)
- Intraday momentum scoring (last hour)
- Volume surge detection
- Multi-timeframe validation

Free Tier Limits:
- Alpaca: 1000 API calls/day
- 5-minute bars: Last 15 days available
- Rate limit: 200 requests/minute

Author: LiteBotX Team
Version: 1.0 (Free Tier Optimized)
Date: October 15, 2025
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Alpaca SDK imports
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logging.warning("⚠️ Alpaca SDK not available - intraday analysis disabled")

from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OpeningRangeData:
    """Opening range breakout data (9:30-10:00 AM)"""
    symbol: str
    date: datetime
    range_high: float
    range_low: float
    range_size: float
    range_size_percent: float
    opening_price: float
    current_price: float
    breakout_high: bool = False
    breakout_low: bool = False
    breakout_significance: float = 0.0
    volume_in_range: int = 0
    
    def __post_init__(self):
        """Calculate breakout status"""
        if self.current_price > self.range_high:
            self.breakout_high = True
            self.breakout_significance = (self.current_price - self.range_high) / self.range_size if self.range_size > 0 else 0
        elif self.current_price < self.range_low:
            self.breakout_low = True
            self.breakout_significance = (self.range_low - self.current_price) / self.range_size if self.range_size > 0 else 0

@dataclass
class IntradayMomentum:
    """Intraday momentum analysis"""
    symbol: str
    timestamp: datetime
    momentum_5min: float  # Last 5 minutes
    momentum_15min: float  # Last 15 minutes
    momentum_1hr: float  # Last 1 hour
    momentum_score: float  # Weighted composite
    volume_surge: float  # Current vs average volume
    price_velocity: float  # Rate of price change
    trend_strength: float  # Consistency of direction
    
@dataclass
class IntradaySignal:
    """Combined intraday signal"""
    symbol: str
    timestamp: datetime
    opening_range: Optional[OpeningRangeData]
    momentum: Optional[IntradayMomentum]
    signal_quality: float  # 0-1 score
    recommendation: str  # BUY, SELL, HOLD, SKIP
    reasons: List[str]


class IntradayAnalyzer:
    """
    Analyzes intraday data using Alpaca's FREE tier
    
    Rate Limits (Free Tier):
    - 200 requests/minute
    - 1000 requests/day
    - 5-minute bars: Last 15 days
    """
    
    def __init__(self):
        """Initialize with Alpaca credentials"""
        load_dotenv()
        
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError("❌ Alpaca API credentials not found in .env file")
        
        if not ALPACA_AVAILABLE:
            raise ImportError("❌ Alpaca SDK not installed. Run: pip install alpaca-py")
        
        # Initialize Alpaca data client
        self.data_client = StockHistoricalDataClient(
            self.api_key,
            self.secret_key
        )
        
        # Rate limiting
        self.api_calls_today = 0
        self.last_api_call = None
        self.max_calls_per_day = 1000  # Conservative limit
        self.min_seconds_between_calls = 0.3  # 200/min = 3.3/sec, use 0.3s buffer
        
        logger.info("✅ IntradayAnalyzer initialized with Alpaca free tier")
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make another API call"""
        if self.api_calls_today >= self.max_calls_per_day:
            logger.warning(f"⚠️ Daily API limit reached ({self.max_calls_per_day} calls)")
            return False
        
        if self.last_api_call:
            elapsed = (datetime.now() - self.last_api_call).total_seconds()
            if elapsed < self.min_seconds_between_calls:
                import time
                time.sleep(self.min_seconds_between_calls - elapsed)
        
        return True
    
    def _record_api_call(self):
        """Record an API call for rate limiting"""
        self.api_calls_today += 1
        self.last_api_call = datetime.now()
    
    def get_5min_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Fetch 5-minute bars from Alpaca (FREE tier)
        
        Args:
            symbol: Stock ticker
            start: Start datetime (Eastern Time)
            end: End datetime (Eastern Time)
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        if not self._check_rate_limit():
            return None
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(5, TimeFrameUnit.Minute),
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request_params)
            self._record_api_call()
            
            if not bars or symbol not in bars:
                logger.warning(f"⚠️ No 5-minute data for {symbol}")
                return None
            
            # Convert to DataFrame
            df = bars[symbol].df
            df.reset_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching 5-min bars for {symbol}: {e}")
            return None
    
    def analyze_opening_range(
        self,
        symbol: str,
        current_price: float,
        date: Optional[datetime] = None
    ) -> Optional[OpeningRangeData]:
        """
        Analyze opening range breakout (9:30-10:00 AM ET)
        
        Opening Range Rules:
        - First 30 minutes of trading (9:30-10:00 AM ET)
        - Track high/low of this range
        - Breakout = price moves outside range
        - Significance = distance from range / range size
        
        Args:
            symbol: Stock ticker
            current_price: Current stock price
            date: Date to analyze (default: today)
            
        Returns:
            OpeningRangeData or None if error
        """
        if date is None:
            date = datetime.now()
        
        # Define opening range window (9:30-10:00 AM ET)
        market_open = date.replace(hour=9, minute=30, second=0, microsecond=0)
        range_end = date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Fetch 5-minute bars for opening range
        df = self.get_5min_bars(symbol, market_open, range_end)
        
        if df is None or df.empty:
            return None
        
        try:
            # Calculate opening range
            range_high = df['high'].max()
            range_low = df['low'].min()
            opening_price = df.iloc[0]['open']
            total_volume = df['volume'].sum()
            
            range_size = range_high - range_low
            range_size_percent = (range_size / opening_price) * 100 if opening_price > 0 else 0
            
            return OpeningRangeData(
                symbol=symbol,
                date=date,
                range_high=range_high,
                range_low=range_low,
                range_size=range_size,
                range_size_percent=range_size_percent,
                opening_price=opening_price,
                current_price=current_price,
                volume_in_range=int(total_volume)
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing opening range for {symbol}: {e}")
            return None
    
    def analyze_intraday_momentum(
        self,
        symbol: str,
        lookback_minutes: int = 60
    ) -> Optional[IntradayMomentum]:
        """
        Analyze intraday momentum using 5-minute bars
        
        Momentum Analysis:
        - 5-min: Very short-term (last 5 minutes)
        - 15-min: Short-term (last 15 minutes)
        - 1-hour: Medium-term (last 60 minutes)
        - Composite: Weighted average favoring recent data
        
        Args:
            symbol: Stock ticker
            lookback_minutes: How far back to analyze (default: 60 min)
            
        Returns:
            IntradayMomentum or None if error
        """
        now = datetime.now()
        start = now - timedelta(minutes=lookback_minutes)
        
        # Fetch 5-minute bars
        df = self.get_5min_bars(symbol, start, now)
        
        if df is None or df.empty or len(df) < 3:
            return None
        
        try:
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            # Calculate momentum at different timeframes
            current_price = df.iloc[-1]['close']
            
            # 5-minute momentum (last bar vs 1 bar ago)
            if len(df) >= 2:
                price_5min_ago = df.iloc[-2]['close']
                momentum_5min = (current_price - price_5min_ago) / price_5min_ago
            else:
                momentum_5min = 0.0
            
            # 15-minute momentum (last bar vs 3 bars ago)
            if len(df) >= 4:
                price_15min_ago = df.iloc[-4]['close']
                momentum_15min = (current_price - price_15min_ago) / price_15min_ago
            else:
                momentum_15min = momentum_5min
            
            # 1-hour momentum (last bar vs 12 bars ago)
            if len(df) >= 13:
                price_1hr_ago = df.iloc[-13]['close']
                momentum_1hr = (current_price - price_1hr_ago) / price_1hr_ago
            else:
                momentum_1hr = momentum_15min
            
            # Weighted composite (favor recent momentum)
            momentum_score = (
                0.5 * momentum_5min +
                0.3 * momentum_15min +
                0.2 * momentum_1hr
            )
            
            # Volume surge (current vs average)
            current_volume = df.iloc[-1]['volume']
            avg_volume = df['volume'].mean()
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price velocity (average momentum per bar)
            price_changes = df['close'].pct_change().dropna()
            price_velocity = price_changes.mean() if not price_changes.empty else 0.0
            
            # Trend strength (consistency of direction)
            positive_moves = (price_changes > 0).sum()
            total_moves = len(price_changes)
            trend_strength = abs((positive_moves / total_moves) - 0.5) * 2 if total_moves > 0 else 0.0
            
            return IntradayMomentum(
                symbol=symbol,
                timestamp=now,
                momentum_5min=momentum_5min,
                momentum_15min=momentum_15min,
                momentum_1hr=momentum_1hr,
                momentum_score=momentum_score,
                volume_surge=volume_surge,
                price_velocity=price_velocity,
                trend_strength=trend_strength
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing momentum for {symbol}: {e}")
            return None
    
    def generate_intraday_signal(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[IntradaySignal]:
        """
        Generate combined intraday trading signal
        
        Signal Quality Calculation:
        - Opening range breakout: +30 points
        - Strong momentum (>0.5%): +25 points
        - Volume surge (>2x): +20 points
        - Trend strength (>0.6): +15 points
        - Price velocity positive: +10 points
        
        Total: 0-100 points, normalized to 0-1
        
        Args:
            symbol: Stock ticker
            current_price: Current price
            
        Returns:
            IntradaySignal with recommendation
        """
        opening_range = self.analyze_opening_range(symbol, current_price)
        momentum = self.analyze_intraday_momentum(symbol)
        
        if opening_range is None and momentum is None:
            logger.warning(f"⚠️ No intraday data available for {symbol}")
            return None
        
        # Calculate signal quality score
        score = 0.0
        reasons = []
        
        # Opening range breakout (30 points)
        if opening_range and opening_range.breakout_high:
            breakout_strength = min(opening_range.breakout_significance, 1.0)
            score += 30 * breakout_strength
            reasons.append(f"Opening range breakout HIGH ({opening_range.breakout_significance:.2f}x range)")
        elif opening_range and opening_range.breakout_low:
            reasons.append(f"Opening range breakout LOW - BEARISH")
            score -= 10  # Penalty for downside breakout
        
        # Momentum scoring (25 points)
        if momentum:
            if momentum.momentum_score > 0.005:  # >0.5% momentum
                momentum_strength = min(abs(momentum.momentum_score) / 0.02, 1.0)  # Cap at 2%
                score += 25 * momentum_strength
                reasons.append(f"Strong momentum: {momentum.momentum_score*100:.2f}%")
            elif momentum.momentum_score < -0.005:
                reasons.append(f"Negative momentum: {momentum.momentum_score*100:.2f}%")
                score -= 15
        
        # Volume surge (20 points)
        if momentum and momentum.volume_surge > 2.0:
            surge_strength = min((momentum.volume_surge - 1) / 3, 1.0)  # Cap at 4x
            score += 20 * surge_strength
            reasons.append(f"Volume surge: {momentum.volume_surge:.2f}x average")
        
        # Trend strength (15 points)
        if momentum and momentum.trend_strength > 0.6:
            score += 15 * momentum.trend_strength
            reasons.append(f"Strong trend consistency: {momentum.trend_strength:.2f}")
        
        # Price velocity (10 points)
        if momentum and momentum.price_velocity > 0:
            score += 10 * min(abs(momentum.price_velocity) / 0.01, 1.0)
            reasons.append(f"Positive price velocity: {momentum.price_velocity*100:.2f}%")
        
        # Normalize score to 0-1
        signal_quality = max(0.0, min(score / 100, 1.0))
        
        # Generate recommendation
        if signal_quality >= 0.7:
            recommendation = "BUY"
        elif signal_quality >= 0.5:
            recommendation = "HOLD"
        elif signal_quality <= 0.3:
            recommendation = "SKIP"
        else:
            recommendation = "HOLD"
        
        return IntradaySignal(
            symbol=symbol,
            timestamp=datetime.now(),
            opening_range=opening_range,
            momentum=momentum,
            signal_quality=signal_quality,
            recommendation=recommendation,
            reasons=reasons
        )
    
    def get_api_usage_stats(self) -> Dict:
        """Get current API usage statistics"""
        return {
            'calls_today': self.api_calls_today,
            'max_calls_per_day': self.max_calls_per_day,
            'remaining_calls': self.max_calls_per_day - self.api_calls_today,
            'usage_percent': (self.api_calls_today / self.max_calls_per_day) * 100
        }


if __name__ == "__main__":
    # Test the analyzer
    print("🧪 Testing IntradayAnalyzer...")
    
    try:
        analyzer = IntradayAnalyzer()
        print("✅ Analyzer initialized")
        
        # Test with a symbol
        test_symbol = "AAPL"
        test_price = 178.50
        
        print(f"\n📊 Analyzing {test_symbol} at ${test_price}...")
        
        signal = analyzer.generate_intraday_signal(test_symbol, test_price)
        
        if signal:
            print(f"\n✅ Signal Generated:")
            print(f"   Quality Score: {signal.signal_quality:.2f}")
            print(f"   Recommendation: {signal.recommendation}")
            print(f"   Reasons:")
            for reason in signal.reasons:
                print(f"     - {reason}")
            
            if signal.opening_range:
                or_data = signal.opening_range
                print(f"\n📈 Opening Range:")
                print(f"   Range: ${or_data.range_low:.2f} - ${or_data.range_high:.2f}")
                print(f"   Size: ${or_data.range_size:.2f} ({or_data.range_size_percent:.2f}%)")
                print(f"   Breakout High: {or_data.breakout_high}")
                print(f"   Breakout Low: {or_data.breakout_low}")
            
            if signal.momentum:
                mom = signal.momentum
                print(f"\n⚡ Momentum:")
                print(f"   5-min: {mom.momentum_5min*100:.2f}%")
                print(f"   15-min: {mom.momentum_15min*100:.2f}%")
                print(f"   1-hour: {mom.momentum_1hr*100:.2f}%")
                print(f"   Volume Surge: {mom.volume_surge:.2f}x")
                print(f"   Trend Strength: {mom.trend_strength:.2f}")
        
        # Show API usage
        stats = analyzer.get_api_usage_stats()
        print(f"\n📊 API Usage:")
        print(f"   Calls Today: {stats['calls_today']}/{stats['max_calls_per_day']}")
        print(f"   Remaining: {stats['remaining_calls']}")
        print(f"   Usage: {stats['usage_percent']:.1f}%")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
