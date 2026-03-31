#!/usr/bin/env python3
"""
Manual Watchlist Refresh for Tomorrow
Triggers PreFilter to regenerate candidates with all new fixes applied
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def refresh_watchlist_now():
    """Manually refresh the watchlist to benefit from today's fixes"""
    logger.info("=" * 70)
    logger.info("🔄 MANUAL WATCHLIST REFRESH - Applying Oct 22 Fixes")
    logger.info("=" * 70)
    
    try:
        # Import the PreFilter
        from pre_filter import PreFilter
        from data_loader import DataLoader
        
        logger.info("📊 Loading PreFilter with enhancements...")
        
        # Initialize data loader
        data_loader = DataLoader()
        
        # Initialize PreFilter with all enhancements enabled
        prefilter = PreFilter(
            simulation_mode=False,
            fast_mode=True,
            data_loader=data_loader,
            enable_gap_detection=True,
            enable_intraday_analysis=False  # Not needed for post-market
        )
        
        logger.info("✅ PreFilter initialized with:")
        logger.info("   ✅ Fix #4: Improved breakout filter (10d window, 1.2x volume, 0.5% breakout)")
        logger.info("   ✅ Fix #5: Relative strength filtering (RS ≥ 0.98)")
        logger.info("   ✅ Fix #6: Sector rotation (boost top 3 sectors)")
        logger.info("   ✅ Fix #7: Universe size 8-15 stocks")
        
        # Run the filter
        logger.info("\n🔍 Running PreFilter...")
        
        # Load base universe from config
        import json
        with open('config/short_cycle_universe.json', 'r') as f:
            universe_config = json.load(f)
        
        base_universe = universe_config.get('base_universe', [])
        logger.info(f"📋 Base universe: {len(base_universe)} symbols")
        
        # Fetch data for all symbols
        logger.info("📥 Fetching market data...")
        data_dict = data_loader.get_historical_data_bulk(base_universe, days=60)
        
        if not data_dict:
            logger.error("❌ No data loaded, cannot refresh watchlist")
            return False
        
        # Convert dict to single dataframe with symbol column
        all_data_frames = []
        for symbol, df in data_dict.items():
            df['symbol'] = symbol
            all_data_frames.append(df)
        
        all_data = pd.concat(all_data_frames, ignore_index=True)
        logger.info(f"✅ Data loaded: {len(all_data)} rows for {all_data['symbol'].nunique()} symbols")
        
        # Run adaptive filtering
        logger.info("\n🎯 Running adaptive filter with all enhancements...")
        filtered = prefilter.adaptive_high_return_candidates(
            all_data,
            target_min=8,
            target_max=15
        )
        
        if filtered.empty:
            logger.warning("⚠️ No candidates passed filters")
            return False
        
        # Get final candidate list
        candidates = filtered['symbol'].unique().tolist()
        scores = filtered.groupby('symbol')['pf_score'].first().to_dict()
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ WATCHLIST REFRESH COMPLETE: {len(candidates)} candidates")
        logger.info("=" * 70)
        
        # Show top candidates with scores
        logger.info("\n🏆 TOP CANDIDATES FOR TOMORROW:")
        sorted_candidates = sorted(candidates, key=lambda x: scores.get(x, 0), reverse=True)
        
        for i, symbol in enumerate(sorted_candidates[:15], 1):
            score = scores.get(symbol, 0)
            
            # Get additional info if available
            sym_data = filtered[filtered['symbol'] == symbol].iloc[-1]
            rs = sym_data.get('relative_strength', 'N/A')
            sector = sym_data.get('sector', 'N/A')
            sector_boost = sym_data.get('sector_boost', 1.0)
            
            rs_str = f"RS={rs:.3f}" if isinstance(rs, float) else "RS=N/A"
            boost_str = f"🔥{sector_boost:.1f}x" if isinstance(sector_boost, (int, float)) and sector_boost > 1.0 else ""
            sector_str = str(sector)[:15] if sector and sector != 'N/A' else 'N/A'
            
            logger.info(f"   {i:2d}. {symbol:6s} | Score: {score:6.2f} | {rs_str} | {sector_str:15s} {boost_str}")
        
        # Save to file for tomorrow morning
        output_file = 'watchlist_oct23.json'
        watchlist_data = {
            'generated_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
            'candidates': sorted_candidates,
            'scores': scores,
            'count': len(candidates),
            'fixes_applied': [
                'Fix #4: Breakout filter improvements',
                'Fix #5: Relative strength filtering',
                'Fix #6: Sector rotation',
                'Fix #7: Universe size 8-15'
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(watchlist_data, f, indent=2)
        
        logger.info(f"\n💾 Watchlist saved to: {output_file}")
        logger.info("\n" + "=" * 70)
        logger.info("✅ SUCCESS: Tomorrow's watchlist ready with all fixes applied!")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Error refreshing watchlist: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import pandas as pd
    
    print("\n🚀 MANUAL WATCHLIST REFRESH")
    print("This will regenerate tomorrow's candidate list with all Oct 22 fixes\n")
    
    success = refresh_watchlist_now()
    
    if success:
        print("\n✅ Watchlist refresh complete!")
        print("🌅 Tomorrow morning the bot will use these enhanced candidates")
        print("\nExpected benefits:")
        print("  • More candidates (8-15 vs 2)")
        print("  • Only stocks outperforming SPY")
        print("  • Focused on top 3 sectors")
        print("  • Better breakout detection")
        sys.exit(0)
    else:
        print("\n❌ Watchlist refresh failed - check logs above")
        sys.exit(1)
