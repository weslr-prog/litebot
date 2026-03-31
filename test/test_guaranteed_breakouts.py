#!/usr/bin/env python3
"""
Create test data with guaranteed breakout conditions on the final day.
This will ensure symbols pass the breakout filter for proper testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_breakout_test_data():
    """Create data where some symbols are guaranteed to be breaking out TODAY."""
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
    data = []
    base_date = datetime.now() - timedelta(days=50)
    
    for i, symbol in enumerate(symbols):
        base_price = 100 + i * 10  # Different base prices
        base_volume = 200000 + i * 50000
        
        # Generate 49 days of normal data
        prices = [base_price]
        volumes = [base_volume]
        
        for day in range(49):
            # Normal price movement: small daily changes
            daily_change = np.random.normal(0, 0.015)  # 1.5% daily volatility
            new_price = prices[-1] * (1 + daily_change)
            prices.append(new_price)
            
            # Normal volume: some variation
            volume_multiplier = np.random.uniform(0.7, 1.3)
            new_volume = int(base_volume * volume_multiplier)
            volumes.append(new_volume)
        
        # Force breakout conditions on the FINAL day for some symbols
        if i < 4:  # First 4 symbols will be breaking out
            # Ensure a price breakout: current price > max of last 20 days by 4%
            last_20_high = max(prices[-20:])
            breakout_price = last_20_high * 1.04  # 4% above 20-day high
            prices[-1] = breakout_price
            
            # Ensure volume spike: 3x average of last 20 days
            avg_20_volume = sum(volumes[-20:]) / 20
            breakout_volume = int(avg_20_volume * 3.0)
            volumes[-1] = breakout_volume
            
            print(f"🎯 {symbol} set up for GUARANTEED breakout:")
            print(f"   20-day high: ${last_20_high:.2f}")
            print(f"   Breakout price: ${breakout_price:.2f} (+{((breakout_price/last_20_high)-1)*100:.1f}%)")
            print(f"   20-day avg volume: {avg_20_volume:,.0f}")
            print(f"   Breakout volume: {breakout_volume:,} ({breakout_volume/avg_20_volume:.1f}x)")
        
        # Generate OHLC for each day
        for day in range(50):
            date = base_date + timedelta(days=day)
            close = prices[day]
            volume = volumes[day]
            
            # Generate realistic OHLC from close price
            daily_range = close * 0.025  # 2.5% daily range
            high = close + np.random.uniform(0, daily_range * 0.6)
            low = close - np.random.uniform(0, daily_range * 0.4)
            open_price = low + np.random.uniform(0, high - low)
            
            data.append({
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
    
    return pd.DataFrame(data)

def test_breakout_conditions():
    """Test the guaranteed breakout conditions."""
    print("🚀 TESTING GUARANTEED BREAKOUT CONDITIONS")
    print("=" * 60)
    
    # Create guaranteed breakout data
    df = create_breakout_test_data()
    print(f"\nCreated {len(df)} rows for {df['symbol'].nunique()} symbols")
    
    # Import and test
    from pre_filter import PreFilter
    
    prefilter = PreFilter(regime_adjustment=False)  # Disable regime for pure test
    
    # Test each filter step
    print(f"\n🔄 TESTING FILTER PIPELINE")
    print("-" * 40)
    
    # Basic filters
    d0 = prefilter.data_completeness_filter(df, min_rows=30)
    d1 = prefilter.liquidity_filter(d0, min_avg_volume=50000, min_dollar_volume=500000)
    d2 = prefilter.price_range_filter(d1, min_price=20, max_price=200)
    d3 = prefilter.volatility_filter(d2, min_volatility=0.01, max_volatility=0.50)  # Very relaxed
    d4 = prefilter.momentum_filter(d3, lookback=5, min_momentum=0.01, max_momentum=0.50)  # Very relaxed
    
    print(f"Before breakout filter: {d4['symbol'].nunique()} symbols")
    print(f"Symbols: {sorted(d4['symbol'].unique().tolist())}")
    
    # Test breakout filter with progressively relaxed thresholds
    print(f"\n🎯 TESTING BREAKOUT FILTER")
    print("-" * 30)
    
    # Test ultra-relaxed thresholds
    for vol_spike in [1.5, 1.2, 1.0]:
        for breakout_min in [0.02, 0.01, 0.005]:
            d5 = prefilter.breakout_filter(
                d4.copy(),
                volume_spike_min=vol_spike,
                price_breakout_min=breakout_min,
                prior_high_window=20,
                avg_volume_window=20,
                min_periods_frac=0.5
            )
            survivors = d5['symbol'].nunique() if not d5.empty else 0
            if survivors > 0:
                print(f"✅ SUCCESS with vol_spike={vol_spike}, breakout={breakout_min:.3f}: {survivors} symbols")
                print(f"   Passing symbols: {sorted(d5['symbol'].unique().tolist())}")
                
                # Show breakout details for successful symbols
                latest = d5.groupby('symbol').tail(1)
                for _, row in latest.iterrows():
                    print(f"   {row['symbol']}: Vol spike {row['volume_spike']:.2f}, "
                          f"Price breakout {row['price_breakout']:.3f}")
                
                return d5
            else:
                print(f"❌ No symbols with vol_spike={vol_spike}, breakout={breakout_min:.3f}")
    
    print(f"\n❌ NO COMBINATION WORKED - FUNDAMENTAL ISSUE WITH BREAKOUT FILTER")
    
    # Debug the latest calculations for first symbol
    symbol = 'AAPL'
    symbol_data = df[df['symbol'] == symbol].copy().sort_values('date')
    
    print(f"\n🔍 MANUAL BREAKOUT CALCULATION FOR {symbol}")
    print("-" * 50)
    
    # Calculate manually like the filter does
    symbol_data['avg_volume_20'] = symbol_data['volume'].rolling(20, min_periods=10).mean()
    symbol_data['volume_spike'] = symbol_data['volume'] / symbol_data['avg_volume_20']
    symbol_data['prior_high_20'] = symbol_data['high'].rolling(20, min_periods=10).max().shift(1)
    symbol_data['price_breakout'] = (symbol_data['close'] - symbol_data['prior_high_20']) / symbol_data['prior_high_20']
    
    latest = symbol_data.iloc[-1]
    print(f"Latest close: ${latest['close']:.2f}")
    print(f"Prior high (20-day): ${latest['prior_high_20']:.2f}")
    print(f"Price breakout: {latest['price_breakout']:.4f}")
    print(f"Latest volume: {latest['volume']:,}")
    print(f"Avg volume (20-day): {latest['avg_volume_20']:,.0f}")
    print(f"Volume spike: {latest['volume_spike']:.2f}")
    
    # Show last few days
    print(f"\nLast 5 days of data:")
    recent = symbol_data.tail(5)[['date', 'close', 'high', 'volume', 'volume_spike', 'price_breakout']]
    for _, row in recent.iterrows():
        print(f"  {row['date']}: Close ${row['close']:.2f}, High ${row['high']:.2f}, "
              f"Vol {row['volume']:,}, VolSpike {row['volume_spike']:.2f}, "
              f"PriceBreakout {row['price_breakout']:.4f}")

if __name__ == "__main__":
    test_breakout_conditions()