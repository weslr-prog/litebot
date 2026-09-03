"""
Dark Pool Activity Detection
Uses Alpaca IEX feed to detect institutional accumulation
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockTradesRequest
from alpaca.data.timeframe import TimeFrame

logger = logging.getLogger(__name__)


class DarkPoolDetector:
    """Detect dark pool and institutional activity using Alpaca IEX"""
    
    def __init__(self):
        """Initialize IEX data client"""
        try:
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                logger.warning("⚠️  Alpaca credentials not found - dark pool detection disabled")
                self.client = None
                return
            
            self.client = StockHistoricalDataClient(api_key, api_secret)
            # Logging handled by parent signal_generator
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize dark pool detector: {e}")
            self.client = None
    
    def detect_institutional_activity(self, symbol: str, hours_lookback: int = 4) -> Dict:
        """
        Detect institutional activity in a symbol
        
        Args:
            symbol: Stock symbol
            hours_lookback: How many hours to analyze (default: 4)
            
        Returns:
            {
                'block_trades': 15,  # Number of 10K+ share trades
                'dark_pool_pct': 42.5,  # Percentage of volume in dark pools
                'avg_block_size': 25000,  # Average block trade size
                'institutional_signal': 'STRONG_ACCUMULATION',
                'confidence_boost': 0.08,
                'is_active': True
            }
        """
        if not self.client:
            return self._neutral_response()
        
        try:
            # Fetch recent trades
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_lookback)
            
            request = StockTradesRequest(
                symbol_or_symbols=symbol,
                start=start_time,
                end=end_time,
                limit=10000  # Get recent trades
            )
            
            trades = self.client.get_stock_trades(request)
            
            if not trades or symbol not in trades:
                logger.debug(f"{symbol}: No trade data available")
                return self._neutral_response()
            
            trade_list = trades[symbol]
            
            if len(trade_list) == 0:
                return self._neutral_response()
            
            # Analyze trades
            block_threshold = 10000  # 10K+ shares = block trade
            block_trades = []
            total_volume = 0
            dark_pool_volume = 0
            
            for trade in trade_list:
                total_volume += trade.size
                
                # Detect block trades
                if trade.size >= block_threshold:
                    block_trades.append(trade)
                
                # Detect dark pool (trades with specific conditions)
                # IEX provides condition codes, 'D' typically indicates dark pool
                if hasattr(trade, 'conditions') and trade.conditions:
                    if 'D' in trade.conditions or 'I' in trade.conditions:
                        dark_pool_volume += trade.size
            
            # Calculate metrics
            block_count = len(block_trades)
            avg_block_size = sum(t.size for t in block_trades) / block_count if block_count > 0 else 0
            dark_pool_pct = (dark_pool_volume / total_volume * 100) if total_volume > 0 else 0
            
            # Average dark pool percentage is ~28%, anything >35% is significant
            avg_dark_pool_pct = 28.0
            
            # Classify institutional activity
            if dark_pool_pct > 40 and block_count > 10:
                signal = 'STRONG_ACCUMULATION'
                confidence_boost = 0.12
                is_active = True
            elif dark_pool_pct > 35 and block_count > 7:
                signal = 'ACCUMULATION'
                confidence_boost = 0.08
                is_active = True
            elif dark_pool_pct < 20 and block_count < 3:
                signal = 'DISTRIBUTION'
                confidence_boost = -0.05
                is_active = False
            else:
                signal = 'NEUTRAL'
                confidence_boost = 0.0
                is_active = False
            
            logger.debug(
                f"{symbol} Dark Pool: {block_count} blocks, "
                f"{dark_pool_pct:.1f}% dark volume, signal={signal}"
            )
            
            return {
                'block_trades': block_count,
                'dark_pool_pct': dark_pool_pct,
                'avg_block_size': int(avg_block_size),
                'institutional_signal': signal,
                'confidence_boost': confidence_boost,
                'is_active': is_active,
                'total_volume': total_volume
            }
            
        except Exception as e:
            logger.debug(f"{symbol}: Error detecting dark pool activity: {e}")
            return self._neutral_response()
    
    def _neutral_response(self) -> Dict:
        """Return neutral response when no data available"""
        return {
            'block_trades': 0,
            'dark_pool_pct': 0.0,
            'avg_block_size': 0,
            'institutional_signal': 'NEUTRAL',
            'confidence_boost': 0.0,
            'is_active': False,
            'total_volume': 0
        }
    
    def format_dark_pool_log(self, symbol: str, activity: Dict) -> str:
        """Format dark pool activity for logging"""
        if not activity['is_active']:
            return f"{symbol}: No significant institutional activity"
        
        signal_emoji = {
            'STRONG_ACCUMULATION': '💰',
            'ACCUMULATION': '📊',
            'DISTRIBUTION': '📉',
            'NEUTRAL': '➡️'
        }
        
        emoji = signal_emoji.get(activity['institutional_signal'], '❓')
        blocks = activity['block_trades']
        dark_pct = activity['dark_pool_pct']
        boost = activity['confidence_boost']
        
        msg = f"{symbol}: {emoji} {activity['institutional_signal']} "
        msg += f"({blocks} blocks, {dark_pct:.1f}% dark pool"
        if boost != 0:
            msg += f", confidence {boost:+.0%}"
        msg += ")"
        
        return msg
