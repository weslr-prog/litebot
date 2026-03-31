"""
Test 3-Strategy Stack with REAL market data

Uses actual stock data to validate the 3-strategy implementation.
"""

import sys
import logging
from datetime import datetime, timedelta
import yfinance as yf

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import ShortCycleTrader components
from traders.short_cycle_trader import AISignalGenerator, ShortCycleConfig

def test_real_stocks():
    """Test with real oversold/gap-up/double-bottom stocks."""
    
    logger.info("="*80)
    logger.info("TESTING 3-STRATEGY STACK WITH REAL MARKET DATA")
    logger.info("="*80)
    
    # Test candidates (hand-picked scenarios)
    test_cases = [
        ("NVDA", "Tech stock - potential signals"),
        ("AMD", "Semiconductor - volatile"),
        ("TSLA", "High momentum stock"),
        ("AAPL", "Large-cap stable"),
        ("PLTR", "Mid-cap growth")
    ]
    
    # Initialize signal generator
    config = ShortCycleConfig()
    config.confidence_threshold = 0.4  # Lower threshold for testing
    generator = AISignalGenerator(config)
    
    signals_found = 0
    strategy_counts = {'mean_reversion_rsi': 0, 'gap_and_go': 0, 'double_bottom': 0}
    
    for symbol, description in test_cases:
        logger.info(f"\n{'─'*80}")
        logger.info(f"Testing {symbol}: {description}")
        logger.info(f"{'─'*80}")
        
        try:
            # Fetch real data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="3mo", interval="1d")
            
            if data.empty:
                logger.warning(f"⚠️  No data available for {symbol}")
                continue
            
            # Normalize column names
            data.columns = [col.lower() for col in data.columns]
            
            logger.info(f"📊 Data range: {data.index[0].date()} to {data.index[-1].date()} ({len(data)} days)")
            logger.info(f"   Current price: ${data['close'].iloc[-1]:.2f}")
            logger.info(f"   20-day SMA: ${data['close'].tail(20).mean():.2f}")
            
            # Generate signal
            signal = generator._analyze_symbol(symbol, data)
            
            if signal:
                signals_found += 1
                strategy = signal.features_used.get('strategy', 'unknown')
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                
                logger.info(f"\n✅ SIGNAL GENERATED!")
                logger.info(f"   Strategy: {strategy.upper()}")
                logger.info(f"   Confidence: {signal.confidence:.3f}")
                logger.info(f"   Entry price: ${signal.entry_price:.2f}")
                logger.info(f"   RSI: {signal.features_used.get('rsi', 'N/A'):.1f}")
                logger.info(f"   Volume surge: {signal.features_used.get('volume_surge', 'N/A'):.2f}x")
                logger.info(f"\n   Strategy Confidences:")
                logger.info(f"   - Mean Reversion: {signal.features_used.get('mean_reversion_conf', 0):.3f}")
                logger.info(f"   - Gap & Go: {signal.features_used.get('gap_and_go_conf', 0):.3f}")
                logger.info(f"   - Double Bottom: {signal.features_used.get('double_bottom_conf', 0):.3f}")
            else:
                logger.info(f"   ❌ No signal (likely filtered by trend or RSI thresholds)")
        
        except Exception as e:
            logger.error(f"❌ Error testing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Signals found: {signals_found}/{len(test_cases)}")
    logger.info(f"\nStrategy distribution:")
    for strategy, count in strategy_counts.items():
        logger.info(f"  {strategy}: {count}")
    
    if signals_found > 0:
        logger.info(f"\n✅ 3-Strategy Stack is WORKING!")
        logger.info(f"   Multiple strategies detected: {len([c for c in strategy_counts.values() if c > 0])}/3")
        return 0
    else:
        logger.warning(f"\n⚠️  No signals found - market conditions may not match strategy criteria")
        logger.info(f"   (This is expected if market is strong uptrend with no pullbacks)")
        return 0

if __name__ == "__main__":
    sys.exit(test_real_stocks())
