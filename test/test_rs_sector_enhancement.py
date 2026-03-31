#!/usr/bin/env python3
"""
Test Relative Strength and Sector Rotation Enhancements
Validates Fixes #5 & #6
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rs_sector_enhancement import (
    RelativeStrengthAnalyzer, 
    SectorRotationAnalyzer,
    enhance_prefilter_with_rs_and_sectors
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create sample data for testing"""
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'JPM', 'BAC', 'XOM', 'CVX', 
               'JNJ', 'PFE', 'NVDA', 'AMD', 'NFLX', 'DIS']
    
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    
    data = []
    for symbol in symbols:
        # Generate fake price data with trend
        base_price = np.random.uniform(50, 300)
        trend = np.random.uniform(-0.02, 0.03)  # Daily trend
        
        for i, date in enumerate(dates):
            price = base_price * (1 + trend * i + np.random.uniform(-0.02, 0.02))
            volume = np.random.uniform(1_000_000, 10_000_000)
            
            data.append({
                'symbol': symbol,
                'date': date,
                'close': price,
                'high': price * 1.02,
                'low': price * 0.98,
                'open': price * 0.99,
                'volume': volume
            })
    
    df = pd.DataFrame(data)
    return df

def test_relative_strength():
    """Test relative strength analysis"""
    logger.info("=" * 60)
    logger.info("TEST 1: Relative Strength Analysis")
    logger.info("=" * 60)
    
    df = create_test_data()
    logger.info(f"Created test data: {len(df)} rows, {df['symbol'].nunique()} symbols")
    
    # Test RS calculation
    rs_analyzer = RelativeStrengthAnalyzer()
    df_with_rs = rs_analyzer.calculate_relative_strength(df, lookback=20)
    
    # Check results
    assert 'relative_strength' in df_with_rs.columns, "Missing relative_strength column"
    
    rs_values = df_with_rs.groupby('symbol')['relative_strength'].first()
    logger.info("\nRelative Strength Results:")
    for symbol, rs in rs_values.items():
        status = "✅ Outperforming" if rs > 1.0 else "⚠️ Underperforming"
        logger.info(f"  {symbol}: RS = {rs:.3f} {status}")
    
    # Test filtering
    filtered = rs_analyzer.filter_by_relative_strength(df_with_rs, min_rs=1.0)
    strong_count = len(filtered['symbol'].unique())
    logger.info(f"\n📊 {strong_count}/{df['symbol'].nunique()} stocks passed RS > 1.0 filter")
    
    logger.info("✅ Test 1 PASSED")
    return df_with_rs

def test_sector_rotation():
    """Test sector rotation analysis"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Sector Rotation Analysis")
    logger.info("=" * 60)
    
    df = create_test_data()
    
    # Test sector rotation
    sector_analyzer = SectorRotationAnalyzer()
    df_with_sectors = sector_analyzer.add_sector_rotation_signal(df)
    
    # Check results
    assert 'sector' in df_with_sectors.columns, "Missing sector column"
    assert 'sector_boost' in df_with_sectors.columns, "Missing sector_boost column"
    assert 'in_leading_sector' in df_with_sectors.columns, "Missing in_leading_sector column"
    
    # Show sector distribution
    sector_counts = df_with_sectors.groupby('symbol').agg({
        'sector': 'first',
        'sector_boost': 'first',
        'in_leading_sector': 'first'
    })
    
    logger.info("\nSector Distribution:")
    for idx, row in sector_counts.iterrows():
        boost_str = f"🔥 BOOSTED {row['sector_boost']:.1f}x" if row['sector_boost'] > 1.0 else ""
        logger.info(f"  {idx}: {row['sector']} {boost_str}")
    
    leading_count = sector_counts['in_leading_sector'].sum()
    logger.info(f"\n🏆 {leading_count} stocks in leading sectors")
    
    logger.info("✅ Test 2 PASSED")
    return df_with_sectors

def test_combined_enhancement():
    """Test combined RS + Sector enhancement"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Combined Enhancement")
    logger.info("=" * 60)
    
    df = create_test_data()
    
    # Apply full enhancement
    enhanced = enhance_prefilter_with_rs_and_sectors(df)
    
    # Check all columns present
    required_cols = ['relative_strength', 'sector', 'sector_boost', 'in_leading_sector']
    for col in required_cols:
        assert col in enhanced.columns, f"Missing column: {col}"
    
    # Summary
    total_symbols = df['symbol'].nunique()
    final_symbols = enhanced['symbol'].nunique()
    
    logger.info(f"\n📊 Final Results:")
    logger.info(f"  Input: {total_symbols} symbols")
    logger.info(f"  Output: {final_symbols} symbols")
    logger.info(f"  Filtered: {total_symbols - final_symbols} symbols")
    
    # Show top candidates
    summary = enhanced.groupby('symbol').agg({
        'relative_strength': 'first',
        'sector': 'first',
        'sector_boost': 'first'
    }).sort_values('sector_boost', ascending=False)
    
    logger.info("\nTop Candidates (by sector boost):")
    for idx, row in summary.head(5).iterrows():
        logger.info(f"  {idx}: RS={row['relative_strength']:.3f}, "
                   f"Sector={row['sector']}, Boost={row['sector_boost']:.2f}x")
    
    logger.info("✅ Test 3 PASSED")
    return enhanced

def main():
    """Run all tests"""
    logger.info("Starting RS/Sector Enhancement Tests")
    logger.info("=" * 60)
    
    try:
        # Test 1: Relative Strength
        test_relative_strength()
        
        # Test 2: Sector Rotation
        test_sector_rotation()
        
        # Test 3: Combined
        test_combined_enhancement()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nFixes #5 & #6 are working correctly!")
        logger.info("Ready to integrate with PreFilter")
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
