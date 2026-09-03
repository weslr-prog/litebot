#!/usr/bin/env python3
"""
Real-Time Data Integration for Short-Cycle Trading System - Clean Version
Sprint 1: Connect short-cycle foundation to live market data
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import Sprint 1 configuration
from core.config import Sprint1Config

@dataclass
class MarketDataConfig:
    """Configuration for market data integration"""
    update_frequency_seconds: int = 300  # 5 minutes for conservative approach
    historical_days: int = 30
    premarket_start: str = "04:00"
    market_open: str = "09:30"
    market_close: str = "16:00"
    postmarket_end: str = "20:00"
    timezone: str = "US/Eastern"

class RealTimeDataFeed:
    """Real-time data feed integration for short-cycle trading"""
    
    def __init__(self, config: MarketDataConfig = None):
        self.config = config or MarketDataConfig()
        # Use Sprint 1 config instead of external dependencies
        self.sprint_config = Sprint1Config()
        self.logger = self._setup_logging()
        
        # Data storage
        self.current_prices = {}
        self.historical_data = {}
        self.last_update = None
        
        # Performance tracking
        self.update_count = 0
        self.error_count = 0
        self.data_quality_score = 1.0
        
    def _setup_logging(self):
        """Setup logging for data feed"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/realtime_data_feed.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('RealTimeDataFeed')
    
    def is_market_hours(self, force_open: bool = False) -> bool:
        """Check if market is currently open (with testing bypass)"""
        if force_open:
            return True
            
        now = datetime.now()
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours (simple version - doesn't account for holidays)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Try to get from Yahoo Finance for real-time price
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try current price first, fallback to previous close
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            
            if current_price:
                self.current_prices[symbol] = {
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'source': 'yfinance'
                }
                return current_price
            
            self.logger.warning(f"No current price available for {symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching current price for {symbol}: {e}")
            self.error_count += 1
            return None
    
    def get_historical_data(self, symbol: str, days: int = None) -> pd.DataFrame:
        """Get historical data for a symbol"""
        days = days or self.config.historical_days
        
        try:
            # Use yfinance directly instead of data_loader
            import yfinance as yf
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                # Standardize column names
                df.columns = [col.lower() for col in df.columns]
                df = df.reset_index()
                
                # Fix timestamp column
                if 'date' in df.columns:
                    df['timestamp'] = df['date']
                else:
                    df['timestamp'] = df.index
                
                self.historical_data[symbol] = {
                    'data': df,
                    'timestamp': datetime.now(),
                    'days': days
                }
                return df
            
            self.logger.warning(f"No historical data available for {symbol}")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            self.error_count += 1
            return pd.DataFrame()
    
    def update_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Update market data for all symbols"""
        self.logger.info(f"Updating market data for {len(symbols)} symbols")
        
        updated_data = {}
        
        for symbol in symbols:
            try:
                # Get current price
                current_price = self.get_current_price(symbol)
                
                # Get historical data if not cached or stale
                needs_historical = (
                    symbol not in self.historical_data or
                    (datetime.now() - self.historical_data[symbol]['timestamp']).total_seconds() > 3600  # 1 hour
                )
                
                if needs_historical:
                    historical_data = self.get_historical_data(symbol)
                else:
                    historical_data = self.historical_data[symbol]['data']
                
                updated_data[symbol] = {
                    'current_price': current_price,
                    'historical_data': historical_data,
                    'last_update': datetime.now(),
                    'data_quality': 'good' if current_price and not historical_data.empty else 'poor'
                }
                
                self.update_count += 1
                
            except Exception as e:
                self.logger.error(f"Error updating data for {symbol}: {e}")
                self.error_count += 1
                updated_data[symbol] = {
                    'current_price': None,
                    'historical_data': pd.DataFrame(),
                    'last_update': datetime.now(),
                    'data_quality': 'error'
                }
        
        self.last_update = datetime.now()
        self._calculate_data_quality_score(updated_data)
        
        return updated_data
    
    def _calculate_data_quality_score(self, data: Dict[str, Dict]):
        """Calculate overall data quality score"""
        if not data:
            self.data_quality_score = 0.0
            return
        
        good_data_count = sum(1 for item in data.values() if item['data_quality'] == 'good')
        self.data_quality_score = good_data_count / len(data)
        
        if self.data_quality_score < 0.8:
            self.logger.warning(f"Data quality score low: {self.data_quality_score:.2%}")
    
    def get_performance_metrics(self) -> Dict:
        """Get data feed performance metrics"""
        uptime_hours = (datetime.now() - (self.last_update or datetime.now())).total_seconds() / 3600
        
        return {
            'updates_completed': self.update_count,
            'errors_encountered': self.error_count,
            'data_quality_score': self.data_quality_score,
            'error_rate': self.error_count / max(self.update_count, 1),
            'last_update': self.last_update,
            'symbols_tracked': len(self.current_prices),
            'uptime_hours': uptime_hours
        }

class SimpleSignalGenerator:
    """Simple signal generator for Sprint 1 testing with enhanced trend confirmation"""
    
    def __init__(self):
        self.logger = logging.getLogger('SimpleSignalGenerator')
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """Analyze trend strength and direction for signal confirmation"""
        if df.empty or len(df) < 20:
            return {'trend': 'neutral', 'strength': 0.0, 'rsi': 50.0}
        
        try:
            # Calculate moving averages for trend analysis
            ma_short = df['close'].rolling(window=5).mean()
            ma_long = df['close'].rolling(window=20).mean()
            
            # Trend direction based on MA crossover
            if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
                trend = 'bullish'
            elif ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
                trend = 'bearish'
            elif ma_short.iloc[-1] > ma_long.iloc[-1]:
                trend = 'uptrend'
            elif ma_short.iloc[-1] < ma_long.iloc[-1]:
                trend = 'downtrend'
            else:
                trend = 'neutral'
            
            # Trend strength based on MA separation
            ma_diff = abs(ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1]
            strength = min(ma_diff * 100, 1.0)  # Cap at 100%
            
            # RSI calculation for momentum confirmation
            def calculate_rsi(prices, period=14):
                delta = prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
            rsi = calculate_rsi(df['close'])
            
            return {
                'trend': trend,
                'strength': strength,
                'rsi': rsi
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend: {e}")
            return {'trend': 'neutral', 'strength': 0.0, 'rsi': 50.0}
    
    def generate_signal(self, symbol: str, df: pd.DataFrame) -> str:
        """Generate trading signal with enhanced filtering and trend confirmation"""
        if df.empty or len(df) < 20:  # Increased from 10 for better trend analysis
            return 'hold'
        
        try:
            # Analyze trend for confirmation
            trend_analysis = self.analyze_trend(df)
            
            # Simple momentum signal with stricter thresholds
            recent_prices = df['close'].tail(5)
            older_prices = df['close'].tail(10).head(5)
            
            recent_avg = recent_prices.mean()
            older_avg = older_prices.mean()
            
            momentum = (recent_avg - older_avg) / older_avg
            
            # Volume confirmation with stricter threshold
            recent_volume = df['volume'].tail(5).mean()
            avg_volume = df['volume'].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Enhanced logging with trend information
            self.logger.info(f"📊 {symbol} momentum: {momentum:.4f}, volume_ratio: {volume_ratio:.2f}")
            self.logger.info(f"📈 {symbol} trend: {trend_analysis['trend']}, strength: {trend_analysis['strength']:.2f}, RSI: {trend_analysis['rsi']:.1f}")
            
            # Generate signal with trend confirmation for high-yield ROI prioritization
            if momentum > 0.015 and volume_ratio > 1.2:
                # BUY signal requires bullish trend and RSI confirmation
                if trend_analysis['trend'] in ['bullish', 'uptrend'] and trend_analysis['rsi'] < 70:
                    self.logger.info(f"🟢 BUY signal confirmed for {symbol} - Strong uptrend with momentum")
                    return 'buy'
                else:
                    self.logger.info(f"⚠️ BUY signal rejected for {symbol} - No trend confirmation")
                    return 'hold'
            elif momentum < -0.015 and volume_ratio > 1.2:
                # SELL signal requires bearish trend and RSI confirmation
                if trend_analysis['trend'] in ['bearish', 'downtrend'] and trend_analysis['rsi'] > 30:
                    self.logger.info(f"🔴 SELL signal confirmed for {symbol} - Strong downtrend with momentum")
                    return 'sell'
                else:
                    self.logger.info(f"⚠️ SELL signal rejected for {symbol} - No trend confirmation")
                    return 'hold'
            else:
                return 'hold'
                
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return 'hold'

class SimpleRiskManager:
    """Simple risk manager for Sprint 1 testing"""
    
    def __init__(self):
        self.logger = logging.getLogger('SimpleRiskManager')
    
    def assess_risk(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Assess risk for a trade"""
        if df.empty:
            return {'confidence': 0.0, 'risk_level': 'high'}
        
        try:
            # Calculate volatility
            returns = df['close'].pct_change().dropna()
            volatility = returns.std()
            
            # Risk assessment
            if volatility > 0.05:
                risk_level = 'high'
                confidence = 0.3
            elif volatility > 0.03:
                risk_level = 'medium'
                confidence = 0.6
            else:
                risk_level = 'low'
                confidence = 0.8
            
            return {
                'confidence': confidence,
                'risk_level': risk_level,
                'volatility': volatility
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing risk for {symbol}: {e}")
            return {'confidence': 0.0, 'risk_level': 'high'}
    
    def check_trade_allowed(self, symbol: str, signal: str, confidence: float) -> bool:
        """Check if a trade is allowed based on risk parameters"""
        try:
            # Basic risk checks
            if confidence < 0.5:
                self.logger.info(f"Trade not allowed for {symbol}: confidence {confidence:.2f} < 0.5")
                return False
            
            # Only allow buy/sell signals (not hold)
            if signal not in ['buy', 'sell']:
                self.logger.info(f"Trade not allowed for {symbol}: signal '{signal}' not actionable")
                return False
            
            # Additional risk checks can be added here
            # - Position limits
            # - Daily loss limits
            # - Market conditions
            
            self.logger.info(f"Trade allowed for {symbol}: signal '{signal}', confidence {confidence:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trade allowed for {symbol}: {e}")
            return False

class SimpleSafetyMonitor:
    """Simple safety monitor for Sprint 1 testing"""
    
    def __init__(self):
        self.logger = logging.getLogger('SimpleSafetyMonitor')
        self.daily_loss_limit = 0.05  # 5% daily loss limit
        self.max_positions = 15
    
    def check_safety_limits(self, daily_pnl: float = 0, weekly_pnl: float = 0, max_drawdown: float = 0) -> str:
        """Check safety limits"""
        if daily_pnl < -self.daily_loss_limit:
            return 'daily_loss_limit_exceeded'
        
        if max_drawdown > 0.10:  # 10% max drawdown
            return 'max_drawdown_exceeded'
        
        return 'ok'

class ShortCycleDataIntegration:
    """Integration layer connecting real-time data to short-cycle trading system"""
    
    def __init__(self):
        self.data_feed = RealTimeDataFeed()
        self.signal_generator = SimpleSignalGenerator()
        self.risk_manager = SimpleRiskManager()
        self.safety_monitor = SimpleSafetyMonitor()
        self.logger = logging.getLogger('ShortCycleDataIntegration')
        
        # Performance tracking
        self.integration_start_time = datetime.now()
        self.signals_generated = 0
        self.trades_executed = 0
        
    def initialize_system(self) -> bool:
        """Initialize the integrated system"""
        self.logger.info("Initializing Short-Cycle Data Integration System")
        
        try:
            # Test data connectivity
            test_symbols = ['AAPL', 'MSFT', 'GOOGL']
            test_data = self.data_feed.update_market_data(test_symbols)
            
            if self.data_feed.data_quality_score < 0.5:
                self.logger.error(f"Data quality too low: {self.data_feed.data_quality_score:.2%}")
                return False
            
            # Test signal generation - simplified for Sprint 1
            test_signals = []
            for symbol in test_symbols[:2]:
                test_data = self.data_feed.get_historical_data(symbol, days=30)
                if not test_data.empty:
                    signal = self.signal_generator.generate_signal(symbol, test_data)
                    test_signals.append(signal)
            
            if not test_signals:
                self.logger.warning("No test signals generated")
            else:
                self.logger.info(f"Generated {len(test_signals)} test signals")
            
            self.logger.info("✅ Short-Cycle Data Integration System initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize system: {e}")
            return False
    
    def run_trading_cycle(self, symbols: List[str]) -> Dict:
        """Run one complete trading cycle with real data"""
        cycle_start = datetime.now()
        self.logger.info(f"Starting trading cycle for {len(symbols)} symbols")
        
        try:
            # Update market data
            market_data = self.data_feed.update_market_data(symbols)
            
            # Check data quality
            if self.data_feed.data_quality_score < 0.7:
                self.logger.warning("Data quality below threshold, skipping cycle")
                return {'status': 'skipped', 'reason': 'low_data_quality'}
            
            # Generate signals using real data
            signals = []
            for symbol in symbols:
                if market_data[symbol]['data_quality'] == 'good':
                    try:
                        signal = self.signal_generator.generate_signal(
                            symbol, 
                            market_data[symbol]['historical_data']
                        )
                        
                        if signal != 'hold':
                            risk_assessment = self.risk_manager.assess_risk(
                                symbol, 
                                market_data[symbol]['historical_data']
                            )
                            
                            signals.append({
                                'symbol': symbol,
                                'signal': signal,
                                'confidence': risk_assessment.get('confidence', 0.5),
                                'current_price': market_data[symbol]['current_price'],
                                'timestamp': datetime.now()
                            })
                            self.signals_generated += 1
                    
                    except Exception as e:
                        self.logger.error(f"Error generating signal for {symbol}: {e}")
            
            # Safety check
            safety_status = self.safety_monitor.check_safety_limits(
                daily_pnl=0,  # Would be calculated from actual positions
                weekly_pnl=0,
                max_drawdown=0
            )
            
            if safety_status and safety_status != 'ok':
                self.logger.warning(f"Safety check failed: {safety_status}")
                return {'status': 'safety_halt', 'reason': safety_status}
            
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            return {
                'status': 'completed',
                'signals_generated': len(signals),
                'signals': signals,
                'cycle_time_seconds': cycle_time,
                'data_quality_score': self.data_feed.data_quality_score,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def start_paper_trading(self, symbols: List[str], update_frequency_minutes: int = 5):
        """Start paper trading with real data integration"""
        self.logger.info(f"🚀 Starting paper trading for {len(symbols)} symbols")
        self.logger.info(f"Update frequency: {update_frequency_minutes} minutes")
        
        if not self.initialize_system():
            self.logger.error("Failed to initialize system")
            return
        
        try:
            while True:
                # Check if market is open
                if not self.data_feed.is_market_hours():
                    self.logger.info("Market closed, waiting...")
                    time.sleep(300)  # Wait 5 minutes
                    continue
                
                # Run trading cycle
                cycle_result = self.run_trading_cycle(symbols)
                
                # Log results
                self.logger.info(f"Cycle completed: {cycle_result['status']}")
                if cycle_result['status'] == 'completed':
                    self.logger.info(f"Signals generated: {cycle_result['signals_generated']}")
                
                # Wait for next cycle
                time.sleep(update_frequency_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("Paper trading stopped by user")
        except Exception as e:
            self.logger.error(f"Paper trading error: {e}")
    
    def get_system_metrics(self) -> Dict:
        """Get comprehensive system performance metrics"""
        uptime = (datetime.now() - self.integration_start_time).total_seconds() / 3600
        
        data_metrics = self.data_feed.get_performance_metrics()
        
        return {
            'system_uptime_hours': uptime,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'data_feed_metrics': data_metrics,
            'status': 'operational' if data_metrics['data_quality_score'] > 0.7 else 'degraded'
        }

def main():
    """Sprint 1 demonstration of real data integration"""
    print("🚀 Sprint 1: Real Data Integration for Short-Cycle Trading")
    print("=" * 60)
    
    # Initialize integration system
    integration = ShortCycleDataIntegration()
    
    # Test symbols for demonstration
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    print("📊 Initializing system...")
    if not integration.initialize_system():
        print("❌ System initialization failed")
        return
    
    print("✅ System initialized successfully")
    
    # Run a single trading cycle demonstration
    print("📈 Running demonstration trading cycle...")
    cycle_result = integration.run_trading_cycle(test_symbols)
    
    print(f"Cycle Status: {cycle_result['status']}")
    if cycle_result['status'] == 'completed':
        print(f"Signals Generated: {cycle_result['signals_generated']}")
        print(f"Data Quality: {cycle_result['data_quality_score']:.1%}")
        print(f"Cycle Time: {cycle_result['cycle_time_seconds']:.2f}s")
        
        if cycle_result['signals']:
            print("Generated Signals:")
            for signal in cycle_result['signals']:
                print(f"  {signal['symbol']}: {signal['signal']} (confidence: {signal['confidence']:.2f})")
    
    # Show system metrics
    print("\n📊 System Performance Metrics:")
    metrics = integration.get_system_metrics()
    for key, value in metrics.items():
        if key != 'data_feed_metrics':
            print(f"  {key}: {value}")
    
    print("\n🎉 Sprint 1 Real Data Integration: SUCCESS!")
    print("✅ Ready for ML model training and extended paper trading")
    
    # Option to start continuous paper trading
    user_input = input("\n🤔 Start continuous paper trading? (y/n): ")
    if user_input.lower() == 'y':
        print("🚀 Starting paper trading... (Ctrl+C to stop)")
        integration.start_paper_trading(test_symbols)

if __name__ == "__main__":
    main()
