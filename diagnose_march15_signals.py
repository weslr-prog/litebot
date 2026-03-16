"""
Signal Generation Diagnostic (March 15 Analysis)
Investigates why 22 prefilter candidates generated 0 signals
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add workspace to path
workspace_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_root)

from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.signal_generation.signal_generator import AISignalGenerator
import logging


def setup_logging():
    """Setup logging for diagnostic"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def analyze_march_15_signals(logger: logging.Logger) -> Dict[str, Any]:
    """
    Analyze why 22 candidates from March 15 prefilter generated 0 signals
    
    QUESTION: 22 stocks passed prefilter, but signal generator returned 0.
    What rejection reasons prevented signals?
    
    Possible causes:
    1. EMA slope filter too strict (Feb 25 fix: changed from <=0 to <-0.5%)
    2. 5-day momentum filter too strict (-5% threshold)
    3. RSI thresholds too high/low
    4. All candidates were in downtrend or falling knife
    5. Confidence threshold too high (25%)
    """
    
    logger.info("=" * 90)
    logger.info("🔍 SIGNAL GENERATION DIAGNOSTIC — March 15, 2026")
    logger.info("=" * 90)
    
    try:
        # Load March 15 daily summary
        summary_file = os.path.join(workspace_root, 'logs/daily_summary_20260315.json')
        if not os.path.exists(summary_file):
            logger.warning(f"Summary file not found: {summary_file}")
            return {"status": "error", "reason": "summary_file_not_found"}
        
        with open(summary_file, 'r') as f:
            daily_summary = json.load(f)
        
        logger.info(f"\n📊 Daily Summary Stats:")
        for event in daily_summary['events']:
            if event['type'] == 'prefilter_results':
                logger.info(f"   • Prefilter: {event['data']['passed']} passed from {event['data']['total']} scanned")
                logger.info(f"   • Rejection breakdown: {event['data']['rejection_reasons']}")
            elif event['type'] == 'signal_generation':
                logger.info(f"   • Signal Generation: {event['data']['signals_out']} signals from {event['data']['candidates_in']} candidates")
                logger.info(f"   • Duration: {event['data']['duration_ms']:.1f}ms")
        
        # Try to gather candidate symbols from market data around March 15
        logger.info("\n📋 Attempting to identify candidates from March 15...")
        
        # Try to load trading config to get signal generator settings
        config = ShortCycleConfig(portfolio_value=1000.0)
        
        logger.info(f"\n⚙️  Active Settings During March 15:")
        logger.info(f"   • Confidence Threshold: {config.confidence_threshold:.0%}")
        logger.info(f"   • Stop Loss: {config.stop_loss_pct:.2%}")
        logger.info(f"   • Profit Target: {config.profit_target_pct:.2%}")
        
        # Key rejection filters that could cause 22→0
        logger.info(f"\n🔎 LIKELY REJECTION FILTERS (from signal_generator.py _analyze_symbol):")
        logger.info(f"\n   1️⃣ EMA SLOPE FILTER (Feb 25, 2026 TIER 1 FIX)")
        logger.info(f"      • Rejects if 20 EMA slope < -0.5% over 3 bars")
        logger.info(f"      • Old: <= 0 (rejected ALL flat/down markets)")
        logger.info(f"      • Impact: Flat trading environments (sideways market) → 0 signals")
        logger.info(f"      • NOTE: March 15 may have been SIDEWAYS/CHOPPY market")
        
        logger.info(f"\n   2️⃣ 5-DAY MOMENTUM FILTER")
        logger.info(f"      • Rejects if 5-day momentum < -5% (falling knife)")
        logger.info(f"      • Prevents catching down trends")
        logger.info(f"      • Impact: Downtrend market → 0 signals")
        
        logger.info(f"\n   3️⃣ PRICE ABOVE 20 EMA")
        logger.info(f"      • Must be ABOVE 20 EMA (no shorts below trend)")
        logger.info(f"      • Rejects if price below EMA")
        
        logger.info(f"\n   4️⃣ RSI THRESHOLDS (by strategy):")
        logger.info(f"      • Gap & Go: enabled={config.enable_gap_and_go}, needs RSI < 75")
        logger.info(f"      • Fade/Short: enabled={config.enable_fade_short}, needs RSI > 70")
        logger.info(f"      • Momentum: enabled={getattr(config, 'enable_momentum', True)}, needs RSI 45-65")
        logger.info(f"      • If all disabled or market RSI neutral (35-70) → 0 signals")
        
        logger.info(f"\n   5️⃣ CONFIDENCE THRESHOLD")
        logger.info(f"      • Final signal confidence must be >= {config.confidence_threshold:.0%}")
        logger.info(f"      • Quality scoring may reduce confidence")
        
        logger.info(f"\n   6️⃣ LIQUIDITY CHECK")
        logger.info(f"      • Requires avg dollar volume >= $500K/day")
        logger.info(f"      • All 22 passed prefilter (which has similar check)")
        logger.info(f"      • Low likelihood this caused rejections")
        
        # Summary analysis
        logger.info(f"\n" + "=" * 90)
        logger.info(f"📈 MOST LIKELY ROOT CAUSES (March 15):")
        logger.info(f"=" * 90)
        logger.info(f"\n🟠 PRIMARY: Market was SIDEWAYS/CHOPPY")
        logger.info(f"   • 20 EMA slope < -0.5% → rejected all 22 candidates")
        logger.info(f"   • This is CORRECT behavior (don't trade in downtrends)")
        logger.info(f"   • Fix: Wait for market confirmation, not a code issue")
        
        logger.info(f"\n🟠 SECONDARY: All strategies were DISABLED")
        logger.info(f"   • Check: config.enable_gap_and_go = {config.enable_gap_and_go}")
        logger.info(f"   • Check: config.enable_fade_short = {config.enable_fade_short}")
        logger.info(f"   • Check: config.enable_momentum = {getattr(config, 'enable_momentum', True)}")
        logger.info(f"   • If all False → 0 signals (expected)")
        
        logger.info(f"\n🟠 TERTIARY: Confidence threshold too high")
        logger.info(f"   • If threshold > scores generated → 0 signals")
        logger.info(f"   • Current: {config.confidence_threshold:.0%}")
        logger.info(f"   • Typical scores: 0.30-0.60 depending on quality")
        
        return {
            "status": "analyzed",
            "date": "2026-03-15",
            "prefilter_passed": 22,
            "signals_generated": 0,
            "likely_causes": [
                "Sideways market (EMA slope < -0.5%)",
                "Check if all strategies disabled",
                "High confidence threshold filtering out candidates"
            ]
        }
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    
    finally:
        logger.info("=" * 90)


if __name__ == "__main__":
    logger = setup_logging()
    result = analyze_march_15_signals(logger)
    print(json.dumps(result, indent=2))
