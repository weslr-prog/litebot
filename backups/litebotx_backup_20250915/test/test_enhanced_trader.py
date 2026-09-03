#!/usr/bin/env python3
"""
Test the enhanced automated momentum trader with risk-adjusted sizing
"""

import logging
from automated_momentum_trader_v2 import AutomatedMomentumTraderV2

# Setup console logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def test_enhanced_trader():
    """Test the enhanced trader with risk-adjusted position sizing"""
    logging.info("🧪 Testing Enhanced Automated Momentum Trader V2")
    logging.info("=" * 60)
    
    # Create enhanced trader
    trader = AutomatedMomentumTraderV2()
    
    # Test portfolio summary
    logging.info("\n📊 Testing Enhanced Portfolio Summary:")
    trader.portfolio_summary()
    
    # Test enhanced momentum cycle
    logging.info("\n🚀 Testing Enhanced Momentum Cycle:")
    trader.execute_enhanced_momentum_cycle()
    
    logging.info("\n✅ Enhanced trader test complete!")

if __name__ == "__main__":
    test_enhanced_trader()
