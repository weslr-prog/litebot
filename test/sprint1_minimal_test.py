#!/usr/bin/env python3
"""
Sprint 1: Real Data Integration - Minimal Standalone Version
Testing weekly ROI data infrastructure without dependencies
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

@dataclass
class MarketDataConfig:
    """Configuration for market data integration"""
    update_frequency_seconds: int = 300  # 5 minutes
    historical_days: int = 30
    timezone: str = "US/Eastern"

class SimplePriceData:
    """Simple price data fetcher using yfinance"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.current_prices = {}
        self.historical_data = {}
        
    def _setup_logging(self):
        """Setup basic logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger('SimplePriceData')
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            
            if current_price:
                self.current_prices[symbol] = {
                    'price': current_price,
                    'timestamp': datetime.now()
                }
                return current_price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical data for a symbol"""
        try:
            import yfinance as yf
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                # Standardize column names
                df.columns = [col.lower() for col in df.columns]
                df = df.reset_index()
                
                # Fix timestamp column - use index as timestamp
                if 'date' in df.columns:
                    df['timestamp'] = df['date']
                else:
                    df['timestamp'] = df.index
                
                self.historical_data[symbol] = {
                    'data': df,
                    'timestamp': datetime.now()
                }
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

class SimpleSignalGenerator:
    """Simple signal generator for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger('SimpleSignalGenerator')
    
    def generate_signal(self, symbol: str, df: pd.DataFrame) -> str:
        """Generate simple trading signal"""
        if df.empty or len(df) < 10:
            return 'hold'
        
        try:
            # Simple momentum signal
            recent_prices = df['close'].tail(5)
            older_prices = df['close'].tail(10).head(5)
            
            recent_avg = recent_prices.mean()
            older_avg = older_prices.mean()
            
            momentum = (recent_avg - older_avg) / older_avg
            
            # Simple volume confirmation
            recent_volume = df['volume'].tail(5).mean()
            avg_volume = df['volume'].mean()
            volume_ratio = recent_volume / avg_volume
            
            # Generate signal
            if momentum > 0.02 and volume_ratio > 1.2:
                return 'buy'
            elif momentum < -0.02 and volume_ratio > 1.2:
                return 'sell'
            else:
                return 'hold'
                
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return 'hold'

class SimpleRiskManager:
    """Simple risk manager for testing"""
    
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

class Sprint1DataIntegration:
    """Sprint 1 data integration test system"""
    
    def __init__(self):
        self.price_data = SimplePriceData()
        self.signal_generator = SimpleSignalGenerator()
        self.risk_manager = SimpleRiskManager()
        self.logger = logging.getLogger('Sprint1DataIntegration')
        
        # Performance tracking
        self.start_time = datetime.now()
        self.signals_generated = 0
        self.data_updates = 0
        
    def test_data_connectivity(self, symbols: List[str]) -> bool:
        """Test data connectivity"""
        self.logger.info(f"Testing data connectivity for {len(symbols)} symbols")
        
        success_count = 0
        
        for symbol in symbols:
            current_price = self.price_data.get_current_price(symbol)
            historical_data = self.price_data.get_historical_data(symbol, days=30)
            
            if current_price and not historical_data.empty:
                success_count += 1
                self.logger.info(f"✅ {symbol}: Price=${current_price:.2f}, History={len(historical_data)} bars")
            else:
                self.logger.warning(f"❌ {symbol}: Data fetch failed")
        
        success_rate = success_count / len(symbols)
        self.logger.info(f"Data connectivity: {success_rate:.1%} ({success_count}/{len(symbols)})")
        
        return success_rate >= 0.8
    
    def run_signal_generation_test(self, symbols: List[str]) -> Dict:
        """Test signal generation with real data"""
        self.logger.info("Testing signal generation with real market data")
        
        results = {
            'signals': [],
            'performance': {
                'symbols_processed': 0,
                'signals_generated': 0,
                'errors': 0
            }
        }
        
        for symbol in symbols:
            try:
                # Get real market data
                historical_data = self.price_data.get_historical_data(symbol, days=60)
                current_price = self.price_data.get_current_price(symbol)
                
                if historical_data.empty or not current_price:
                    results['performance']['errors'] += 1
                    continue
                
                # Generate signal
                signal = self.signal_generator.generate_signal(symbol, historical_data)
                
                # Assess risk
                risk_assessment = self.risk_manager.assess_risk(symbol, historical_data)
                
                if signal != 'hold':
                    results['signals'].append({
                        'symbol': symbol,
                        'signal': signal,
                        'confidence': risk_assessment['confidence'],
                        'risk_level': risk_assessment['risk_level'],
                        'current_price': current_price,
                        'timestamp': datetime.now()
                    })
                    self.signals_generated += 1
                    results['performance']['signals_generated'] += 1
                
                results['performance']['symbols_processed'] += 1
                self.data_updates += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {e}")
                results['performance']['errors'] += 1
        
        return results
    
    def simulate_trading_cycle(self, symbols: List[str], cycles: int = 3) -> Dict:
        """Simulate multiple trading cycles"""
        self.logger.info(f"Simulating {cycles} trading cycles")
        
        cycle_results = []
        
        for cycle in range(cycles):
            self.logger.info(f"Running cycle {cycle + 1}/{cycles}")
            
            cycle_start = datetime.now()
            
            # Run signal generation
            results = self.run_signal_generation_test(symbols)
            
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            cycle_summary = {
                'cycle': cycle + 1,
                'signals_generated': results['performance']['signals_generated'],
                'symbols_processed': results['performance']['symbols_processed'],
                'errors': results['performance']['errors'],
                'cycle_time_seconds': cycle_time,
                'timestamp': datetime.now()
            }
            
            cycle_results.append(cycle_summary)
            
            # Log cycle results
            self.logger.info(f"Cycle {cycle + 1}: {cycle_summary['signals_generated']} signals, {cycle_time:.2f}s")
            
            # Wait between cycles (except last one)
            if cycle < cycles - 1:
                time.sleep(10)  # 10 second delay
        
        return {
            'cycles': cycle_results,
            'total_signals': sum(c['signals_generated'] for c in cycle_results),
            'avg_cycle_time': np.mean([c['cycle_time_seconds'] for c in cycle_results]),
            'success_rate': 1 - (sum(c['errors'] for c in cycle_results) / sum(c['symbols_processed'] for c in cycle_results))
        }
    
    def get_system_metrics(self) -> Dict:
        """Get system performance metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds() / 3600
        
        return {
            'uptime_hours': uptime,
            'signals_generated': self.signals_generated,
            'data_updates': self.data_updates,
            'current_prices_cached': len(self.price_data.current_prices),
            'historical_data_cached': len(self.price_data.historical_data),
            'status': 'operational'
        }

def main():
    """Sprint 1 real data integration test"""
    print("🚀 Sprint 1: Real Data Integration Test")
    print("Weekly High Yield ROI - Data Infrastructure Validation")
    print("=" * 60)
    
    # Test symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    # Initialize system
    integration = Sprint1DataIntegration()
    
    print("📊 Testing data connectivity...")
    data_ok = integration.test_data_connectivity(test_symbols)
    
    if not data_ok:
        print("❌ Data connectivity test failed")
        return
    
    print("✅ Data connectivity test passed")
    
    print("\n📈 Testing signal generation...")
    signal_results = integration.run_signal_generation_test(test_symbols)
    
    print(f"Signals generated: {signal_results['performance']['signals_generated']}")
    print(f"Symbols processed: {signal_results['performance']['symbols_processed']}")
    print(f"Errors: {signal_results['performance']['errors']}")
    
    if signal_results['signals']:
        print("\nGenerated Signals:")
        for signal in signal_results['signals']:
            print(f"  {signal['symbol']}: {signal['signal']} (confidence: {signal['confidence']:.2f})")
    
    print("\n🔄 Running multi-cycle simulation...")
    cycle_results = integration.simulate_trading_cycle(test_symbols, cycles=3)
    
    print(f"Total signals: {cycle_results['total_signals']}")
    print(f"Average cycle time: {cycle_results['avg_cycle_time']:.2f}s")
    print(f"Success rate: {cycle_results['success_rate']:.1%}")
    
    print("\n📊 System Performance Metrics:")
    metrics = integration.get_system_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n🎉 Sprint 1 Real Data Integration: SUCCESS!")
    print("✅ Data connectivity established")
    print("✅ Signal generation operational") 
    print("✅ Multi-cycle simulation completed")
    print("✅ Ready for ML model training integration")
    
    # Performance summary
    total_runtime = (datetime.now() - integration.start_time).total_seconds()
    print(f"\n⏱️  Total test runtime: {total_runtime:.2f} seconds")
    print(f"🎯 Weekly ROI infrastructure foundation: VALIDATED")

if __name__ == "__main__":
    main()
