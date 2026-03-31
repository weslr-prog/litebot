#!/usr/bin/env python3
"""
Daily Watchlist Refresh - Runs After Market Close
Ensures fresh candidates are always available for next trading day
"""
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/watchlist_refresh.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_data(symbol, days=30):
    """Fetch historical data for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=days*2)  # Get extra for weekends
        hist = ticker.history(start=start, end=end)
        if len(hist) > 0:
            return hist.tail(days)
        return None
    except Exception as e:
        logger.debug(f"  {symbol}: {e}")
        return None


def calculate_score(df):
    """Calculate momentum + volume surge score"""
    if len(df) < 10:
        return 0
    
    # Price momentum (last 10 days)
    price_momentum = (df['Close'].iloc[-1] / df['Close'].iloc[-10] - 1) * 100
    
    # Volume surge (last 3 days vs previous 7 days)
    recent_vol = df['Volume'].iloc[-3:].mean()
    prev_vol = df['Volume'].iloc[-10:-3].mean()
    vol_surge = recent_vol / prev_vol if prev_vol > 0 else 1
    
    # Combined score
    score = price_momentum * vol_surge
    
    return score


def refresh_watchlist():
    """Generate fresh watchlist for tomorrow"""
    logger.info("=" * 70)
    logger.info("🔄 DAILY WATCHLIST REFRESH")
    logger.info("=" * 70)
    
    # Load universe
    try:
        with open('config/short_cycle_universe.json', 'r') as f:
            config = json.load(f)
        universe = config.get('base_universe', [])
    except Exception as e:
        logger.error(f"Failed to load universe config: {e}")
        return False
    
    logger.info(f"📋 Scanning {len(universe)} symbols...")
    
    # Fetch data and score
    candidates = []
    success_count = 0
    
    for i, symbol in enumerate(universe, 1):
        if i % 10 == 0:
            logger.info(f"  Progress: {i}/{len(universe)}")
        
        df = get_data(symbol, days=30)
        if df is not None and len(df) >= 10:
            score = calculate_score(df)
            if score > 0:  # Only positive momentum
                candidates.append({
                    'symbol': symbol,
                    'score': float(score),
                    'price': float(df['Close'].iloc[-1]),
                    'volume': int(df['Volume'].iloc[-1]),
                    'momentum_10d': float((df['Close'].iloc[-1] / df['Close'].iloc[-10] - 1) * 100)
                })
                success_count += 1
    
    logger.info(f"✅ Successfully scored {success_count}/{len(universe)} symbols")
    
    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Take top 15
    top_candidates = candidates[:15]
    
    if len(top_candidates) < 8:
        logger.warning(f"⚠️  Only {len(top_candidates)} candidates found (need 8 minimum)")
        return False
    
    logger.info("\n" + "=" * 70)
    logger.info(f"✅ FOUND {len(top_candidates)} TOP CANDIDATES FOR TOMORROW")
    logger.info("=" * 70)
    
    for i, c in enumerate(top_candidates, 1):
        logger.info(f"  {i:2d}. {c['symbol']:6s} | Score: {c['score']:7.2f} | "
                   f"Price: ${c['price']:.2f} | Mom: {c['momentum_10d']:+.1f}%")
    
    # Save to file
    et_tz = pytz.timezone('US/Eastern')
    watchlist = {
        'generated_at': datetime.now(et_tz).isoformat(),
        'symbols': [c['symbol'] for c in top_candidates],
        'count': len(top_candidates),
        'config': {
            'max_size': 15,
            'min_size': 8,
            'pipeline': 'daily_momentum_scan',
            'refresh_frequency': 'daily_after_close'
        },
        'details': top_candidates
    }
    
    output_file = 'logs/current_watchlist.json'
    with open(output_file, 'w') as f:
        json.dump(watchlist, f, indent=2)
    
    logger.info(f"\n💾 Watchlist saved to: {output_file}")
    
    # Also save dated backup
    date_str = datetime.now().strftime('%Y%m%d')
    backup_file = f'logs/watchlist_{date_str}.json'
    with open(backup_file, 'w') as f:
        json.dump(watchlist, f, indent=2)
    
    logger.info(f"💾 Backup saved to: {backup_file}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ WATCHLIST REFRESH COMPLETE")
    logger.info("🌅 Tomorrow the bot will use these fresh candidates")
    logger.info("=" * 70)
    
    return True


def main():
    """Main entry point"""
    try:
        # Check if yfinance is available
        try:
            import yfinance
            logger.info("✅ yfinance is available")
        except ImportError:
            logger.error("❌ yfinance not installed - install with: pip install yfinance")
            return False
        
        # Run refresh
        success = refresh_watchlist()
        
        if success:
            logger.info("\n✅ Daily watchlist refresh succeeded!")
            return True
        else:
            logger.error("\n❌ Daily watchlist refresh failed")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
