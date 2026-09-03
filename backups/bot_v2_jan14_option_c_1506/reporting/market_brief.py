"""
Morning Market Brief Generator
Provides daily market assessment for Gap & Go and Fade/Short opportunities
"""

import datetime as dt
import pytz
from typing import Dict, List, Tuple
import logging


class MarketBrief:
    """Generate morning market brief with setup quality assessment"""
    
    def __init__(self, data_loader, logger=None):
        self.data_loader = data_loader
        self.logger = logger or logging.getLogger(__name__)
        self.tz = pytz.timezone('America/New_York')
    
    def generate_brief(self, universe: List[str]) -> Dict:
        """
        Generate morning market brief
        
        Returns:
            Dict with market conditions, setup quality, and top opportunities
        """
        now = dt.datetime.now(self.tz)
        
        try:
            # Get market data
            spy_change = self._get_spy_change()
            vix_level = self._get_vix_level()
            oversold_count = self._count_oversold_stocks(universe)
            
            # Calculate setup quality (1-5 stars)
            setup_quality = self._calculate_setup_quality(
                oversold_count, len(universe), vix_level, spy_change
            )
            
            # Get premarket gaps
            top_gaps = self._find_premarket_gaps(universe)
            
            # Expected trade count
            expected_trades = self._estimate_trade_count(
                oversold_count, len(universe), setup_quality
            )
            
            brief = {
                'date': now.strftime('%A, %B %d, %Y'),
                'time': now.strftime('%I:%M %p ET'),
                'market': {
                    'spy_change': spy_change,
                    'vix_level': vix_level,
                    'vix_status': self._vix_status(vix_level),
                    'market_bias': self._market_bias(spy_change)
                },
                'setup': {
                    'quality_stars': setup_quality,
                    'oversold_count': oversold_count,
                    'universe_size': len(universe),
                    'oversold_pct': (oversold_count / len(universe) * 100) if universe else 0,
                    'quality_reason': self._quality_reason(setup_quality, oversold_count, vix_level)
                },
                'expectations': {
                    'min_trades': expected_trades[0],
                    'max_trades': expected_trades[1],
                    'confidence': expected_trades[2]
                },
                'top_gaps': top_gaps[:5]  # Top 5 gaps
            }
            
            return brief
            
        except Exception as e:
            self.logger.error(f"Failed to generate market brief: {e}")
            return self._get_fallback_brief(now)
    
    def _get_spy_change(self) -> float:
        """Get SPY overnight change (comparing yesterday close to premarket/open)"""
        try:
            # Get SPY data for last 2 days
            bars = self.data_loader.get_bars(['SPY'], timeframe='1Day', limit=2)
            if 'SPY' in bars and len(bars['SPY']) >= 2:
                yesterday_close = bars['SPY'][-2].close
                today_open = bars['SPY'][-1].open
                return ((today_open - yesterday_close) / yesterday_close) * 100
            return 0.0
        except:
            return 0.0
    
    def _get_vix_level(self) -> float:
        """Get current VIX level"""
        try:
            # Try to get VIX data
            bars = self.data_loader.get_bars(['VIX'], timeframe='1Day', limit=1)
            if 'VIX' in bars and len(bars['VIX']) > 0:
                return bars['VIX'][-1].close
            return 16.0  # Default if unavailable
        except:
            return 16.0  # Default safe value
    
    def _count_oversold_stocks(self, universe: List[str]) -> int:
        """Count how many stocks have RSI < 35"""
        try:
            oversold_count = 0
            
            # Sample 50 stocks for quick assessment (full scan during entry window)
            import random
            sample_size = min(50, len(universe))
            sample = random.sample(universe, sample_size) if len(universe) > sample_size else universe
            
            for symbol in sample:
                try:
                    bars = self.data_loader.get_bars([symbol], timeframe='1Day', limit=15)
                    if symbol not in bars or len(bars[symbol]) < 14:
                        continue
                    
                    # Calculate RSI
                    closes = [b.close for b in bars[symbol]]
                    rsi = self._calculate_rsi(closes, period=14)
                    
                    if rsi and rsi < 35:
                        oversold_count += 1
                        
                except:
                    continue
            
            # Scale up to full universe
            if sample_size > 0:
                oversold_count = int((oversold_count / sample_size) * len(universe))
            
            return oversold_count
            
        except Exception as e:
            self.logger.error(f"Failed to count oversold stocks: {e}")
            return 0
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_setup_quality(self, oversold_count: int, universe_size: int, 
                                  vix: float, spy_change: float) -> int:
        """
        Calculate setup quality (1-5 stars)
        
        Factors:
        - Oversold percentage (most important)
        - VIX level (volatility creates opportunities)
        - Market dip (SPY down = better setups)
        """
        score = 0
        
        # Factor 1: Oversold percentage (0-2 points)
        oversold_pct = (oversold_count / universe_size * 100) if universe_size > 0 else 0
        if oversold_pct >= 10:
            score += 2  # Excellent
        elif oversold_pct >= 7:
            score += 1.5  # Good
        elif oversold_pct >= 5:
            score += 1  # Fair
        elif oversold_pct >= 3:
            score += 0.5  # Poor
        # else: 0 (very poor)
        
        # Factor 2: VIX level (0-1.5 points)
        if 16 <= vix <= 25:
            score += 1.5  # Sweet spot
        elif 12 <= vix < 16 or 25 < vix <= 30:
            score += 1  # Acceptable
        elif vix > 30:
            score += 0.5  # Too volatile
        # else: 0 (too calm)
        
        # Factor 3: Market dip (0-1.5 points)
        if spy_change <= -1.0:
            score += 1.5  # Strong dip
        elif spy_change <= -0.5:
            score += 1  # Moderate dip
        elif spy_change <= 0:
            score += 0.5  # Slight weakness
        # else: 0 (market up = fewer mean reversion setups)
        
        # Convert to 1-5 stars
        if score >= 4.5:
            return 5
        elif score >= 3.5:
            return 4
        elif score >= 2.5:
            return 3
        elif score >= 1.5:
            return 2
        else:
            return 1
    
    def _vix_status(self, vix: float) -> str:
        """Get VIX status description"""
        if vix < 12:
            return "Too calm"
        elif vix < 16:
            return "Low volatility"
        elif vix <= 25:
            return "Good volatility"
        elif vix <= 30:
            return "Elevated"
        else:
            return "High volatility"
    
    def _market_bias(self, spy_change: float) -> str:
        """Get market bias description"""
        if spy_change <= -1.5:
            return "Strong selloff"
        elif spy_change <= -0.8:
            return "Dip-buy opportunity"
        elif spy_change <= -0.3:
            return "Mild weakness"
        elif spy_change <= 0.3:
            return "Flat open"
        else:
            return "Gap up"
    
    def _quality_reason(self, stars: int, oversold_count: int, vix: float) -> str:
        """Generate quality reason text"""
        if stars >= 4:
            return "Strong oversold conditions + good volatility"
        elif stars == 3:
            return "Moderate oversold conditions"
        elif stars == 2:
            return "Limited oversold stocks"
        else:
            return "Few oversold opportunities"
    
    def _estimate_trade_count(self, oversold_count: int, universe_size: int, 
                               quality: int) -> Tuple[int, int, str]:
        """
        Estimate expected trade count (min, max, confidence)
        
        Returns:
            (min_trades, max_trades, confidence_level)
        """
        oversold_pct = (oversold_count / universe_size * 100) if universe_size > 0 else 0
        
        if quality >= 4:
            # Excellent day
            min_trades = max(2, int(oversold_count * 0.15))
            max_trades = max(4, int(oversold_count * 0.30))
            confidence = "High"
        elif quality == 3:
            # Good day
            min_trades = max(1, int(oversold_count * 0.10))
            max_trades = max(3, int(oversold_count * 0.20))
            confidence = "Moderate"
        elif quality == 2:
            # Fair day
            min_trades = 0
            max_trades = max(1, int(oversold_count * 0.15))
            confidence = "Low"
        else:
            # Poor day
            min_trades = 0
            max_trades = 1
            confidence = "Very low"
        
        # Cap at reasonable limits
        max_trades = min(max_trades, 12)  # Max position limit
        
        return (min_trades, max_trades, confidence)
    
    def _find_premarket_gaps(self, universe: List[str]) -> List[Dict]:
        """Find stocks with significant premarket gaps"""
        gaps = []
        
        try:
            # Sample 100 stocks for gap detection
            import random
            sample_size = min(100, len(universe))
            sample = random.sample(universe, sample_size) if len(universe) > sample_size else universe
            
            for symbol in sample:
                try:
                    bars = self.data_loader.get_bars([symbol], timeframe='1Day', limit=15)
                    if symbol not in bars or len(bars[symbol]) < 15:
                        continue
                    
                    yesterday_close = bars[symbol][-2].close
                    today_open = bars[symbol][-1].open
                    gap_pct = ((today_open - yesterday_close) / yesterday_close) * 100
                    
                    # Only gaps down > 2%
                    if gap_pct <= -2.0:
                        # Calculate RSI
                        closes = [b.close for b in bars[symbol]]
                        rsi = self._calculate_rsi(closes, period=14)
                        
                        gaps.append({
                            'symbol': symbol,
                            'gap_pct': gap_pct,
                            'rsi': rsi,
                            'yesterday_close': yesterday_close,
                            'today_open': today_open
                        })
                        
                except:
                    continue
            
            # Sort by gap size (most negative first)
            gaps.sort(key=lambda x: x['gap_pct'])
            
        except Exception as e:
            self.logger.error(f"Failed to find premarket gaps: {e}")
        
        return gaps
    
    def _get_fallback_brief(self, now: dt.datetime) -> Dict:
        """Return fallback brief if data unavailable"""
        return {
            'date': now.strftime('%A, %B %d, %Y'),
            'time': now.strftime('%I:%M %p ET'),
            'market': {
                'spy_change': 0.0,
                'vix_level': 16.0,
                'vix_status': 'Unknown',
                'market_bias': 'Unknown'
            },
            'setup': {
                'quality_stars': 3,
                'oversold_count': 0,
                'universe_size': 280,
                'oversold_pct': 0,
                'quality_reason': 'Data unavailable - will assess at entry window'
            },
            'expectations': {
                'min_trades': 0,
                'max_trades': 3,
                'confidence': 'Unknown'
            },
            'top_gaps': []
        }
    
    def print_brief(self, brief: Dict):
        """Print formatted morning brief to console"""
        print("\n" + "=" * 70)
        print(f"🌅 MORNING MARKET BRIEF - {brief['date']}")
        print("=" * 70)
        
        # Market conditions
        market = brief['market']
        print("\nMARKET CONDITIONS:")
        
        vix_emoji = "✅" if "Good" in market['vix_status'] else "⚠️" if "Low" in market['vix_status'] else "🔴"
        print(f"  • VIX: {market['vix_level']:.1f} ({market['vix_status']}) {vix_emoji}")
        
        spy_emoji = "✅" if market['spy_change'] < 0 else "⚠️"
        print(f"  • SPY: {market['spy_change']:+.1f}% ({market['market_bias']}) {spy_emoji}")
        
        oversold_pct = brief['setup']['oversold_pct']
        oversold_emoji = "✅" if oversold_pct >= 7 else "⚠️" if oversold_pct >= 4 else "🔴"
        print(f"  • Oversold stocks (RSI<35): {brief['setup']['oversold_count']}/{brief['setup']['universe_size']} ({oversold_pct:.1f}%) {oversold_emoji}")
        
        # Setup quality
        print("\nMEAN REVERSION SETUP:")
        stars = "⭐" * brief['setup']['quality_stars'] + "☆" * (5 - brief['setup']['quality_stars'])
        print(f"  • Quality: {stars} ({brief['setup']['quality_stars']}/5 stars)")
        print(f"  • Reason: {brief['setup']['quality_reason']}")
        
        exp = brief['expectations']
        if exp['min_trades'] == exp['max_trades']:
            trade_range = f"{exp['min_trades']}"
        else:
            trade_range = f"{exp['min_trades']}-{exp['max_trades']}"
        print(f"  • Expected trades: {trade_range} positions today")
        print(f"  • Confidence: {exp['confidence']}")
        
        # Top gaps
        if brief['top_gaps']:
            print("\nPREMARKET GAPS (Top 5):")
            for i, gap in enumerate(brief['top_gaps'][:5], 1):
                rsi_emoji = "✅" if gap['rsi'] and gap['rsi'] < 35 else "⚠️" if gap['rsi'] and gap['rsi'] < 40 else "🔴"
                rsi_text = f"RSI: {gap['rsi']:.0f}" if gap['rsi'] else "RSI: N/A"
                print(f"  {i}. {gap['symbol']}: {gap['gap_pct']:.1f}% 📊 {rsi_text} {rsi_emoji}")
        else:
            print("\nPREMARKET GAPS:")
            print("  • No significant gaps detected (checking 100 sample stocks)")
        
        print("\nBOT STATUS: 🟢 Active | Next scan: 9:45 AM")
        print("=" * 70 + "\n")
