"""
Enhanced Signal Generator Integration
Purpose: Integrates quality scoring and free data filters into existing trading system
Created: November 4, 2025
"""

import logging
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from intraday_quality_scorer import IntradayQualityScorer
from free_data_filter import FreeDataFilter

logger = logging.getLogger(__name__)


class EnhancedSignalGenerator:
    """
    Wraps existing signal generation with quality scoring and filtering
    
    Flow:
    1. Filter universe through free data filters (VIX, earnings, float)
    2. Generate base signals (existing logic)
    3. Score each signal with quality scorer (0-100)
    4. Classify signals as WEAK/MEDIUM/STRONG
    5. Adjust confidence based on quality and filters
    """
    
    def __init__(self, base_signal_generator):
        """
        Args:
            base_signal_generator: Existing AISignalGenerator instance
        """
        self.base_generator = base_signal_generator
        self.quality_scorer = IntradayQualityScorer()
        self.data_filter = FreeDataFilter()
        
        self.logger = logging.getLogger(__name__ + ".EnhancedSignalGenerator")
        self.logger.info("✅ EnhancedSignalGenerator initialized")
    
    def generate_signals(self, universe: List[str], market_data: Dict[str, pd.DataFrame],
                        active_positions: Optional[List] = None) -> List:
        """
        Generate enhanced signals with quality scoring
        
        Args:
            universe: List of candidate symbols
            market_data: Historical price data
            active_positions: Currently active positions
            
        Returns:
            List of AISignal objects with enhanced quality scoring
        """
        try:
            # Step 1: Filter universe
            filter_results = self.data_filter.filter_universe(universe)
            approved_symbols = filter_results['approved']
            confidence_adjustments = filter_results['adjustments']
            vix_adj = filter_results['vix_adjustment']
            
            self.logger.info(
                f"\n{'='*60}\n"
                f"🔍 SIGNAL GENERATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'='*60}"
            )
            self.logger.info(f"📋 Universe: {len(universe)} symbols → {len(approved_symbols)} after filters")
            self.logger.info(f"📊 VIX: {vix_adj['reason']}")
            
            if len(approved_symbols) == 0:
                self.logger.warning("⚠️  No symbols passed filters!")
                return []
            
            # Step 2: Generate base signals from approved universe
            base_signals = self.base_generator.generate_signals(
                approved_symbols, market_data, active_positions
            )
            
            if len(base_signals) == 0:
                self.logger.info("ℹ️  No base signals generated")
                return []
            
            self.logger.info(f"📡 Base signals: {len(base_signals)}")
            
            # Step 3: Enhance each signal with quality scoring
            enhanced_signals = []
            
            for signal in base_signals:
                try:
                    # Get market data for this symbol
                    symbol_data = market_data.get(signal.symbol)
                    if symbol_data is None or len(symbol_data) < 20:
                        self.logger.warning(f"⚠️  {signal.symbol}: Insufficient data, skipping")
                        continue
                    
                    # Score signal quality
                    quality_result = self.quality_scorer.score_signal(
                        signal.symbol, symbol_data, signal.entry_price
                    )
                    
                    # Add quality info to signal
                    signal.quality_score = quality_result['total_score']
                    signal.quality_tier = quality_result['quality_tier']
                    signal.quality_reasoning = quality_result['reasoning']
                    signal.quality_components = quality_result['component_scores']
                    
                    # Apply confidence adjustments
                    original_confidence = signal.confidence
                    
                    # 1. Quality-based adjustment
                    if signal.quality_tier == "STRONG":
                        signal.confidence *= 1.25  # Boost strong signals
                    elif signal.quality_tier == "WEAK":
                        signal.confidence *= 0.80  # Reduce weak signals
                    
                    # 2. Fundamental-based adjustment (from free data filter)
                    if signal.symbol in confidence_adjustments:
                        signal.confidence *= confidence_adjustments[signal.symbol]
                    
                    # 3. VIX-based adjustment (global)
                    signal.confidence *= vix_adj['position_size_multiplier']
                    
                    # Cap confidence at 1.0
                    signal.confidence = min(signal.confidence, 1.0)
                    
                    self.logger.info(
                        f"\n{'─'*60}\n"
                        f"📈 {signal.symbol} - {signal.quality_tier} ({quality_result['total_score']:.0f}/100)\n"
                        f"   Confidence: {original_confidence:.2f} → {signal.confidence:.2f}\n"
                        f"   {quality_result['reasoning']}\n"
                        f"{'─'*60}"
                    )
                    
                    enhanced_signals.append(signal)
                    
                except Exception as e:
                    self.logger.error(f"Error enhancing signal for {signal.symbol}: {e}")
                    continue
            
            # Step 4: Sort by confidence and apply limits
            enhanced_signals.sort(key=lambda x: x.confidence, reverse=True)
            
            # Apply VIX-based position limits if needed
            if vix_adj['max_positions'] is not None:
                max_positions = min(
                    vix_adj['max_positions'],
                    self.base_generator.config.max_positions_per_day
                )
                enhanced_signals = enhanced_signals[:max_positions]
                if len(enhanced_signals) < len(base_signals):
                    self.logger.info(
                        f"⚠️  VIX limit: Reduced from {len(base_signals)} to {len(enhanced_signals)} positions"
                    )
            
            self.logger.info(
                f"\n{'='*60}\n"
                f"✅ FINAL SIGNALS: {len(enhanced_signals)}\n"
                f"{'='*60}\n"
            )
            
            return enhanced_signals
            
        except Exception as e:
            self.logger.error(f"Error in enhanced signal generation: {e}")
            # Fallback to base generator
            return self.base_generator.generate_signals(universe, market_data, active_positions)
    
    def clear_caches(self):
        """Clear caches at end of day"""
        self.quality_scorer.clear_cache()
        self.data_filter.clear_cache()
        self.logger.info("🧹 Enhanced signal generator caches cleared")


class DynamicExitManager:
    """
    Quality-based exit logic that lets strong signals run
    
    Exit Rules:
    - STRONG (75+): +5% target, -2% stop, trail at +2.5%, ignore zone exits
    - MEDIUM (55-74): +3.5% target, -1.5% stop, trail at +2%, use zone exits
    - WEAK (<55): +2% target, -1.5% stop, trail at +1.5%, quick zone exits
    """
    
    EXIT_RULES = {
        'STRONG': {
            'profit_target': 0.05,       # +5%
            'stop_loss': -0.020,         # -2%
            'trailing_trigger': 0.025,   # Trail at +2.5%
            'trailing_distance': 0.015,  # Trail 1.5% behind
            'ignore_zones': True,        # Don't force early exits
            'min_profit_lock': 0.015     # Lock +1.5% minimum
        },
        'MEDIUM': {
            'profit_target': 0.035,      # +3.5%
            'stop_loss': -0.015,         # -1.5%
            'trailing_trigger': 0.020,   # Trail at +2%
            'trailing_distance': 0.010,  # Trail 1% behind
            'ignore_zones': False,       # Use zone logic
            'min_profit_lock': 0.010     # Lock +1% minimum
        },
        'WEAK': {
            'profit_target': 0.020,      # +2%
            'stop_loss': -0.015,         # -1.5%
            'trailing_trigger': 0.015,   # Trail at +1.5%
            'trailing_distance': 0.008,  # Trail 0.8% behind
            'ignore_zones': False,       # Quick exit
            'min_profit_lock': 0.005     # Lock +0.5% minimum
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".DynamicExitManager")
        self.logger.info("✅ DynamicExitManager initialized")
    
    def get_exit_params(self, position) -> Dict:
        """
        Get exit parameters for a position based on its quality tier
        
        Args:
            position: Position object with quality_tier attribute
            
        Returns:
            Dict with exit parameters
        """
        quality_tier = getattr(position, 'quality_tier', 'MEDIUM')
        
        if quality_tier not in self.EXIT_RULES:
            self.logger.warning(f"Unknown quality tier '{quality_tier}', using MEDIUM")
            quality_tier = 'MEDIUM'
        
        return self.EXIT_RULES[quality_tier]
    
    def should_exit(self, position, current_price: float, current_time: datetime) -> tuple:
        """
        Check if position should be exited
        
        Args:
            position: Position object
            current_price: Current market price
            current_time: Current time
            
        Returns:
            (should_exit: bool, exit_reason: str)
        """
        try:
            rules = self.get_exit_params(position)
            entry_price = position.entry_price
            pnl_pct = (current_price - entry_price) / entry_price
            
            # 1. Stop loss check
            if pnl_pct <= rules['stop_loss']:
                return True, f"STOP_LOSS ({pnl_pct:.2%})"
            
            # 2. Profit target check
            if pnl_pct >= rules['profit_target']:
                return True, f"PROFIT_TARGET ({pnl_pct:.2%})"
            
            # 3. Trailing stop check
            if hasattr(position, 'highest_price') and position.highest_price is not None:
                peak_pnl = (position.highest_price - entry_price) / entry_price
                
                if peak_pnl >= rules['trailing_trigger']:
                    # Trailing stop is active
                    trailing_stop_price = position.highest_price * (1 - rules['trailing_distance'])
                    
                    if current_price <= trailing_stop_price:
                        locked_profit = (trailing_stop_price - entry_price) / entry_price
                        return True, f"TRAILING_STOP (locked {locked_profit:.2%})"
            
            # 4. Time-based zone exits (if not ignored)
            if not rules['ignore_zones']:
                hour = current_time.hour
                minute = current_time.minute
                
                # Zone 2 (11 AM - 2 PM): Take small profits
                if 11 <= hour < 14:
                    if pnl_pct >= 0.005:  # Any profit > 0.5%
                        return True, f"ZONE2_EXIT ({pnl_pct:.2%})"
                
                # Zone 3 (2 PM - 3:30 PM): Be more conservative
                elif 14 <= hour < 15 or (hour == 15 and minute < 30):
                    if pnl_pct >= 0.003:  # Any profit > 0.3%
                        return True, f"ZONE3_EXIT ({pnl_pct:.2%})"
            
            # 5. Force close at 3:45 PM
            if current_time.hour == 15 and current_time.minute >= 45:
                return True, f"FORCE_CLOSE ({pnl_pct:.2%})"
            
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error checking exit for {position.symbol}: {e}")
            return False, None


# Integration test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("\n🧪 Testing Enhanced Signal Integration...\n")
    
    # Test exit manager
    print("="*60)
    print("TEST 1: Dynamic Exit Manager")
    print("="*60)
    
    exit_mgr = DynamicExitManager()
    
    for tier in ['STRONG', 'MEDIUM', 'WEAK']:
        class MockPosition:
            quality_tier = tier
            entry_price = 100.0
            highest_price = 103.0
            symbol = 'TEST'
        
        params = exit_mgr.get_exit_params(MockPosition())
        print(f"\n{tier} Tier:")
        print(f"  Profit Target: {params['profit_target']:.1%}")
        print(f"  Stop Loss: {params['stop_loss']:.1%}")
        print(f"  Trailing Trigger: {params['trailing_trigger']:.1%}")
        print(f"  Ignore Zones: {params['ignore_zones']}")
    
    print("\n✅ Integration test complete!")
