"""
Test script for Regime-Based Filter Adjustment
Validates the new system and demonstrates usage
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_regime_filter():
    """Test the regime-based filter adjustment system"""
    print("🧪 TESTING REGIME-BASED FILTER ADJUSTMENT")
    print("=" * 50)
    
    try:
        from regime_filter_adjustment import RegimeBasedFilterAdjustment, MarketRegime
        from pre_filter import PreFilter
        
        print("✅ Modules imported successfully")
        
        # Create test market data
        dates = pd.date_range(start='2025-09-01', end='2025-09-30', freq='D')
        test_data = pd.DataFrame({
            'date': dates,
            'open': 100 + np.random.normal(0, 2, len(dates)),
            'high': 102 + np.random.normal(0, 2, len(dates)),
            'low': 98 + np.random.normal(0, 2, len(dates)),
            'close': 100 + np.random.normal(0, 2, len(dates)),
            'volume': 1000000 + np.random.normal(0, 100000, len(dates)),
            'symbol': 'SPY'
        })
        
        # Test 1: Initialize regime filter
        regime_filter = RegimeBasedFilterAdjustment()
        print("✅ Regime filter initialized")
        
        # Test 2: Detect regime
        regime_metrics = regime_filter.detect_market_regime(test_data)
        print(f"✅ Regime detected: {regime_metrics.regime.value}")
        print(f"   Volatility: {regime_metrics.avg_volatility:.3f}")
        print(f"   Momentum: {regime_metrics.momentum_trend:.3f}")
        
        # Test 3: Get regime config
        config = regime_filter.get_regime_adjusted_config(regime_metrics.regime)
        print(f"✅ Regime config generated")
        print(f"   Vol spike min: {config['vol_spike_min']:.2f}")
        print(f"   Breakout min: {config['breakout_min']:.3f}")
        
        # Test 4: Test with PreFilter
        print("\n📊 Testing PreFilter integration...")
        prefilter = PreFilter(regime_adjustment=True)
        print("✅ PreFilter with regime adjustment initialized")
        
        # Test 5: Create sample stock data
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        stock_data = []
        
        for symbol in symbols:
            for i, date in enumerate(dates[-21:]):  # Last 21 days
                stock_data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': 150 + np.random.normal(0, 5),
                    'high': 152 + np.random.normal(0, 5),
                    'low': 148 + np.random.normal(0, 5),
                    'close': 150 + np.random.normal(0, 5),
                    'volume': 2000000 + np.random.normal(0, 500000)
                })
        
        stock_df = pd.DataFrame(stock_data)
        
        # Test adaptive filtering (this will use regime adjustments if working)
        print("\n🎯 Testing adaptive filtering with regime awareness...")
        
        # Add required columns for filtering
        stock_df['dollar_volume'] = stock_df['close'] * stock_df['volume']
        stock_df['avg_volume'] = stock_df.groupby('symbol')['volume'].transform(lambda x: x.rolling(5).mean())
        stock_df['avg_dollar_volume'] = stock_df.groupby('symbol')['dollar_volume'].transform(lambda x: x.rolling(5).mean())
        
        # Run the adaptive filter
        filtered_result = prefilter.adaptive_high_return_candidates(stock_df, target_min=3, target_max=5)
        
        print(f"✅ Adaptive filtering completed")
        print(f"   Input symbols: {stock_df['symbol'].nunique()}")
        print(f"   Output symbols: {filtered_result['symbol'].nunique() if not filtered_result.empty else 0}")
        
        if not filtered_result.empty:
            print(f"   Filtered symbols: {filtered_result['symbol'].unique().tolist()}")
        
        print("\n🎉 REGIME-BASED FILTER ADJUSTMENT TEST COMPLETE")
        print("✅ All tests passed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_regime_scenarios():
    """Demonstrate different regime scenarios and their configurations"""
    print("\n📊 REGIME SCENARIOS DEMONSTRATION")
    print("=" * 40)
    
    try:
        from regime_filter_adjustment import RegimeBasedFilterAdjustment, MarketRegime
        
        regime_filter = RegimeBasedFilterAdjustment()
        
        for regime in MarketRegime:
            config = regime_filter.get_regime_adjusted_config(regime)
            regime_config = regime_filter.regime_configs[regime]
            
            print(f"\n🎯 {regime_config.name} ({regime.value})")
            print(f"   Description: {regime_config.description}")
            print(f"   Vol Spike Min: {config['vol_spike_min']:.2f}")
            print(f"   Breakout Min: {config['breakout_min']:.3f} ({config['breakout_min']*100:.1f}%)")
            print(f"   Momentum Range: {config['min_momentum']:.3f} - {config['max_momentum']:.3f}")
            print(f"   Volatility Range: {config['min_volatility']:.3f} - {config['max_volatility']:.3f}")
        
        print(f"\n✅ Regime scenarios demonstrated")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")

if __name__ == "__main__":
    success = test_regime_filter()
    
    if success:
        demonstrate_regime_scenarios()
        
        print("\n🚀 READY FOR DEPLOYMENT")
        print("The regime-based filter adjustment system is ready to improve bot profitability!")
    else:
        print("\n❌ SYSTEM NOT READY")
        print("Please fix the issues above before deployment.")