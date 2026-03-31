#!/usr/bin/env python3
"""
Comprehensive debugging test for regime-based filter system.
Tests with realistic market data patterns that would trigger breakouts.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_realistic_breakout_data(symbols, days=50):
    """Create realistic market data with actual breakout patterns."""
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for symbol in symbols:
        base_price = np.random.uniform(50, 150)
        base_volume = np.random.uniform(100000, 500000)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            
            # Create realistic price movement with occasional breakouts
            if i == 0:
                close = base_price
                volume = base_volume
            else:
                # 90% normal days, 10% breakout days
                if np.random.random() < 0.1:  # Breakout day
                    # Simulate a real breakout: price jumps 3-8%, volume spikes 2-5x
                    price_jump = np.random.uniform(0.03, 0.08) * np.random.choice([1, -1])
                    close = data[-1]['close'] * (1 + price_jump)
                    volume = base_volume * np.random.uniform(2.0, 5.0)  # Volume spike
                else:
                    # Normal day: small price changes, normal volume
                    daily_change = np.random.normal(0, 0.02)
                    close = data[-1]['close'] * (1 + daily_change)
                    volume = base_volume * np.random.uniform(0.5, 1.5)
            
            # Generate OHLC from close
            daily_range = close * np.random.uniform(0.01, 0.04)
            high = close + np.random.uniform(0, daily_range)
            low = close - np.random.uniform(0, daily_range)
            open_price = low + np.random.uniform(0, high - low)
            
            data.append({
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': int(volume)
            })
    
    return pd.DataFrame(data)

def debug_breakout_calculations(df, symbol='AAPL'):
    """Debug the breakout calculation for a specific symbol."""
    print(f"\n🔍 DEBUGGING BREAKOUT CALCULATIONS FOR {symbol}")
    
    symbol_data = df[df['symbol'] == symbol].copy().sort_values('date')
    if symbol_data.empty:
        print(f"No data for {symbol}")
        return
    
    # Calculate the same way as breakout_filter
    symbol_data['avg_volume_20'] = symbol_data['volume'].rolling(20, min_periods=10).mean()
    symbol_data['volume_spike'] = symbol_data['volume'] / symbol_data['avg_volume_20']
    symbol_data['prior_high_20'] = symbol_data['high'].rolling(20, min_periods=10).max().shift(1)
    symbol_data['price_breakout'] = (symbol_data['close'] - symbol_data['prior_high_20']) / symbol_data['prior_high_20']
    
    # Show last 10 days
    recent = symbol_data.tail(10)
    print("\nLast 10 days:")
    for _, row in recent.iterrows():
        print(f"Date: {row['date']}, Close: ${row['close']:.2f}, "
              f"Volume: {row['volume']:,}, Vol Spike: {row['volume_spike']:.2f}, "
              f"Price Breakout: {row['price_breakout']:.3f}")
    
    # Check latest breakout conditions
    latest = symbol_data.iloc[-1]
    print(f"\n📊 LATEST CONDITIONS FOR {symbol}:")
    print(f"Volume Spike: {latest['volume_spike']:.2f} (need ≥ 2.0)")
    print(f"Price Breakout: {latest['price_breakout']:.3f} (need ≥ 0.030)")
    print(f"Prior High: ${latest['prior_high_20']:.2f}")
    print(f"Current Close: ${latest['close']:.2f}")
    
    # Count how many days would pass breakout
    breakout_days = symbol_data[
        (symbol_data['volume_spike'] >= 2.0) & 
        (symbol_data['price_breakout'] >= 0.03)
    ]
    print(f"Days that would pass breakout filter: {len(breakout_days)}")
    
    return latest['volume_spike'] >= 2.0 and latest['price_breakout'] >= 0.03

def run_comprehensive_debug():
    """Run a comprehensive debugging session."""
    print("🚀 STARTING COMPREHENSIVE REGIME FILTER DEBUG SESSION")
    print("=" * 70)
    
    # Import components
    try:
        from pre_filter import PreFilter
        from regime_filter_adjustment import RegimeBasedFilterAdjustment
        print("✅ Successfully imported components")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
    
    # Create realistic test data with breakout patterns
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
    print(f"\n📊 Creating realistic breakout data for {len(symbols)} symbols...")
    df = create_realistic_breakout_data(symbols, days=50)
    print(f"Created {len(df)} rows of data")
    
    # Debug individual symbol calculations
    print("\n🔍 DEBUGGING INDIVIDUAL SYMBOL BREAKOUT CALCULATIONS")
    print("-" * 60)
    
    breakout_symbols = []
    for symbol in symbols[:3]:  # Check first 3 symbols
        passed = debug_breakout_calculations(df, symbol)
        if passed:
            breakout_symbols.append(symbol)
    
    print(f"\n🎯 Symbols that should pass breakout filter: {breakout_symbols}")
    
    # Initialize components
    print("\n⚙️  INITIALIZING REGIME FILTER SYSTEM")
    print("-" * 50)
    
    prefilter = PreFilter(regime_adjustment=True)
    regime_filter = RegimeBasedFilterAdjustment()
    prefilter.regime_filter = regime_filter
    
    # Test regime detection
    print("\n🌡️  TESTING REGIME DETECTION")
    print("-" * 40)
    
    # Use AAPL as market proxy
    market_data = df[df['symbol'] == 'AAPL'].copy()
    regime_metrics = regime_filter.detect_market_regime(market_data)
    print(f"Detected regime: {regime_metrics.regime.value}")
    print(f"Volatility: {regime_metrics.avg_volatility:.3f}")
    print(f"Momentum: {regime_metrics.momentum_trend:.3f}")
    print(f"Breakout frequency: {regime_metrics.breakout_frequency:.3f}")
    
    # Get regime configuration
    config = regime_filter.get_regime_adjusted_config(regime_metrics.regime)
    print(f"\n🎛️  REGIME CONFIGURATION:")
    print(f"Vol spike min: {config.get('vol_spike_min', 'N/A')}")
    print(f"Breakout min: {config.get('breakout_min', 'N/A')}")
    print(f"Min momentum: {config.get('min_momentum', 'N/A')}")
    
    # Test progressive filter steps
    print("\n🔄 TESTING FILTER PIPELINE WITH DEBUG INFO")
    print("-" * 55)
    
    # Step 1: Data completeness
    d0 = prefilter.data_completeness_filter(df, min_rows=30)
    print(f"After data completeness: {d0['symbol'].nunique()} symbols, {len(d0)} rows")
    
    # Step 2: Liquidity
    d1 = prefilter.liquidity_filter(d0, min_avg_volume=50000, min_dollar_volume=500000)
    print(f"After liquidity: {d1['symbol'].nunique()} symbols, {len(d1)} rows")
    
    # Step 3: Price range
    d2 = prefilter.price_range_filter(d1, min_price=20, max_price=200)
    print(f"After price range: {d2['symbol'].nunique()} symbols, {len(d2)} rows")
    
    # Step 4: Volatility
    d3 = prefilter.volatility_filter(d2, min_volatility=0.03, max_volatility=0.25)
    print(f"After volatility: {d3['symbol'].nunique()} symbols, {len(d3)} rows")
    
    # Step 5: Momentum
    d4 = prefilter.momentum_filter(d3, lookback=5, min_momentum=0.05, max_momentum=0.20)
    print(f"After momentum: {d4['symbol'].nunique()} symbols, {len(d4)} rows")
    
    # Step 6: Breakout (the problematic one)
    print(f"\n🎯 TESTING BREAKOUT FILTER WITH RELAXED THRESHOLDS")
    
    # Try progressively relaxed thresholds
    vol_spike_tests = [2.0, 1.5, 1.2, 1.0]
    breakout_tests = [0.03, 0.02, 0.01, 0.005]
    
    for vol_spike in vol_spike_tests:
        for breakout_min in breakout_tests:
            d5 = prefilter.breakout_filter(
                d4.copy(),
                volume_spike_min=vol_spike,
                price_breakout_min=breakout_min,
                prior_high_window=20,
                avg_volume_window=20,
                min_periods_frac=0.5
            )
            survivors = d5['symbol'].nunique() if not d5.empty else 0
            print(f"  Vol spike {vol_spike}, breakout {breakout_min:.3f}: {survivors} symbols")
            
            if survivors > 0:
                print(f"    SUCCESS! Symbols: {sorted(d5['symbol'].unique().tolist())}")
                
                # Test full adaptive pipeline
                print(f"\n✅ TESTING FULL ADAPTIVE PIPELINE")
                result = prefilter.adaptive_high_return_candidates(df)
                final_symbols = result['symbol'].nunique() if not result.empty else 0
                print(f"Final adaptive result: {final_symbols} symbols")
                if final_symbols > 0:
                    print(f"Final symbols: {sorted(result['symbol'].unique().tolist())}")
                return
    
    print(f"\n❌ NO SYMBOLS PASSED BREAKOUT FILTER WITH ANY THRESHOLD COMBINATION")
    print(f"This indicates the test data may still not be realistic enough,")
    print(f"or the breakout filter logic needs fundamental changes.")

if __name__ == "__main__":
    run_comprehensive_debug()