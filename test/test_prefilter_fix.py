#!/usr/bin/env python3
"""Quick Pre-Filter Test"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prefilter_fix():
    from pre_filter import PreFilter
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Simulate free tier data (16 business days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=21)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    business_dates = [d for d in dates if d.weekday() < 5]
    
    print(f"Business days available: {len(business_dates)}")
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    data = []
    for symbol in symbols:
        for date in business_dates:
            data.append({
                'symbol': symbol,
                'date': date,
                'close': 100.0,
                'volume': 1000000
            })
    
    df = pd.DataFrame(data)
    print(f"Data rows per symbol: {len(df) // len(symbols)}")
    
    pre_filter = PreFilter()
    
    # Test with min_rows=15
    result = pre_filter.data_completeness_filter(df, min_rows=15)
    symbols_15 = len(result['symbol'].unique()) if not result.empty else 0
    
    print(f"Symbols passing with min_rows=15: {symbols_15}")
    
    if symbols_15 >= 3:
        print("✅ Pre-filter fix working!")
        return True
    else:
        print("❌ Still not working")
        return False

if __name__ == "__main__":
    test_prefilter_fix()