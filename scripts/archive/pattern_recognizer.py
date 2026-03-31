"""
Pattern Recognition System for D+1 Trading
Purpose: Classify stocks by behavior pattern to optimize entry/exit timing
Author: AI Assistant
Date: October 17, 2025
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class StockPattern(Enum):
    """Stock behavior patterns for D+1 trading"""
    MORNING_GAPPER = "morning_gapper"      # Gaps at open, fades by midday
    MOMENTUM_RUNNER = "momentum_runner"    # Steady climb throughout day
    LATE_BLOOMER = "late_bloomer"          # Slow start, moves afternoon
    RANGE_BOUND = "range_bound"            # Choppy, no clear direction
    REVERSAL = "reversal"                  # Gaps then reverses direction
    UNKNOWN = "unknown"                    # Insufficient data


class PatternRecognizer:
    """
    Recognizes stock behavior patterns to optimize trading timing.
    """
    
    def __init__(self):
        """Initialize pattern recognizer"""
        # Initialization logged by parent class (trader)
    
    def identify_pattern(self, 
                        current_price: float,
                        entry_price: float,
                        gap_at_open: Optional[float] = None,
                        minutes_held: int = 0,
                        price_history: Optional[List[float]] = None) -> StockPattern:
        """
        Identify the pattern a position is following.
        
        Args:
            current_price: Current stock price
            entry_price: Entry price
            gap_at_open: Gap % at market open (if available)
            minutes_held: Minutes since entry
            price_history: List of prices since entry (chronological)
            
        Returns:
            StockPattern enum
        """
        try:
            # Calculate basic metrics
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Pattern 1: MORNING_GAPPER
            # - Gapped 1%+ at open
            # - Key indicator: gap present regardless of fade
            if gap_at_open is not None and abs(gap_at_open) >= 0.01:
                logger.debug(f"Pattern: MORNING_GAPPER (gap present: {gap_at_open:.1%})")
                return StockPattern.MORNING_GAPPER
            
            # Pattern 2: MOMENTUM_RUNNER
            # - Steady climb with higher highs
            # - No big gap, just consistent gains
            if price_history and len(price_history) >= 3:
                # Check for higher highs
                recent_high = max(price_history[-3:])
                earlier_high = max(price_history[:3]) if len(price_history) >= 6 else price_history[0]
                
                if recent_high > earlier_high and pnl_pct > 0.005:  # Up 0.5%+
                    # Steady climb pattern
                    logger.debug(f"Pattern: MOMENTUM_RUNNER (steady climb)")
                    return StockPattern.MOMENTUM_RUNNER
            
            # Pattern 3: LATE_BLOOMER
            # - Flat or slight move early
            # - Held 60+ minutes, slow gradual climb
            if minutes_held >= 60 and (gap_at_open is None or abs(gap_at_open) < 0.01):
                # Check if movement is slow and steady
                if 0 < pnl_pct < 0.01:  # Small gain 0-1%
                    logger.debug(f"Pattern: LATE_BLOOMER (slow gradual climb)")
                    return StockPattern.LATE_BLOOMER
            
            # Pattern 5: RANGE_BOUND (check before REVERSAL - more specific)
            # - Choppy, no clear direction
            # - Small moves back and forth
            if price_history and len(price_history) >= 4 and minutes_held >= 30:
                price_range = max(price_history) - min(price_history)
                range_pct = price_range / entry_price
                
                # Choppy if range < 1% AND not much net movement AND no gap
                if range_pct < 0.01 and abs(pnl_pct) < 0.005 and (gap_at_open is None or abs(gap_at_open) < 0.005):
                    logger.debug(f"Pattern: RANGE_BOUND (choppy, range: {range_pct:.1%})")
                    return StockPattern.RANGE_BOUND
            
            # Pattern 4: REVERSAL (check after RANGE_BOUND)
            # - Gapped one way, moving opposite direction
            if gap_at_open is not None and abs(gap_at_open) >= 0.01:
                if (gap_at_open > 0 and pnl_pct < -0.005) or \
                   (gap_at_open < 0 and pnl_pct > 0.005):
                    logger.debug(f"Pattern: REVERSAL (gap reversed)")
                    return StockPattern.REVERSAL
            
            # Default: Unknown (need more data)
            logger.debug(f"Pattern: UNKNOWN (insufficient data)")
            return StockPattern.UNKNOWN
            
        except Exception as e:
            logger.error(f"Error identifying pattern: {e}")
            return StockPattern.UNKNOWN
    
    def get_optimal_exit_time(self, pattern: StockPattern, 
                             current_time: datetime,
                             pnl_pct: float) -> Tuple[bool, str]:
        """
        Determine if it's optimal exit time based on pattern.
        
        Args:
            pattern: Stock pattern
            current_time: Current market time
            pnl_pct: Current profit/loss %
            
        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        try:
            market_hour = current_time.hour + current_time.minute / 60.0
            
            # MORNING_GAPPER: Exit 10:00-11:00 AM (gaps fade)
            if pattern == StockPattern.MORNING_GAPPER:
                if 10.0 <= market_hour < 11.0:
                    if pnl_pct > 0:  # Any profit
                        return True, "GAPPER_FADE_EXIT"
                elif market_hour >= 11.0:
                    if pnl_pct > -0.01:  # Not deeply negative
                        return True, "GAPPER_LATE_EXIT"
            
            # MOMENTUM_RUNNER: Exit 11:30 AM-1:30 PM (catch peak)
            elif pattern == StockPattern.MOMENTUM_RUNNER:
                if 11.5 <= market_hour < 13.5:
                    if pnl_pct >= 0.01:  # 1%+ profit
                        return True, "MOMENTUM_PEAK_EXIT"
                elif market_hour >= 13.5:
                    if pnl_pct > 0:  # Any profit after 1:30 PM
                        return True, "MOMENTUM_LATE_EXIT"
            
            # LATE_BLOOMER: Exit 2:00-3:30 PM (afternoon movers)
            elif pattern == StockPattern.LATE_BLOOMER:
                if 14.0 <= market_hour < 15.5:
                    if pnl_pct >= 0.005:  # 0.5%+ profit
                        return True, "BLOOMER_AFTERNOON_EXIT"
                elif market_hour >= 15.5:
                    return True, "BLOOMER_FORCE_EXIT"
            
            # REVERSAL: Exit ASAP if profitable, or cut loss
            elif pattern == StockPattern.REVERSAL:
                if pnl_pct > 0.005:  # Any small profit
                    return True, "REVERSAL_PROFIT_EXIT"
                elif pnl_pct < -0.015:  # -1.5% loss
                    return True, "REVERSAL_STOP_LOSS"
            
            # RANGE_BOUND: Exit on any profit after 11 AM
            elif pattern == StockPattern.RANGE_BOUND:
                if market_hour >= 11.0 and pnl_pct > 0.003:  # 0.3%+ profit
                    return True, "RANGE_PROFIT_EXIT"
                elif market_hour >= 14.0:
                    if pnl_pct >= 0:  # Breakeven or better
                        return True, "RANGE_AFTERNOON_EXIT"
            
            # UNKNOWN: Use standard exit logic
            else:
                # Standard time-based exits
                if market_hour >= 10.0 and pnl_pct >= 0.015:  # 1.5%+ profit
                    return True, "STANDARD_PROFIT_EXIT"
                elif market_hour >= 14.0 and pnl_pct >= 0:  # Breakeven after 2 PM
                    return True, "STANDARD_AFTERNOON_EXIT"
            
            return False, "HOLD_FOR_BETTER_TIMING"
            
        except Exception as e:
            logger.error(f"Error determining exit time: {e}")
            return False, "ERROR"
    
    def get_pattern_description(self, pattern: StockPattern) -> str:
        """Get human-readable pattern description"""
        descriptions = {
            StockPattern.MORNING_GAPPER: "Gapped at open, likely to fade by midday",
            StockPattern.MOMENTUM_RUNNER: "Steady climb, peaks around midday",
            StockPattern.LATE_BLOOMER: "Slow start, moves in afternoon",
            StockPattern.RANGE_BOUND: "Choppy, no clear direction",
            StockPattern.REVERSAL: "Gap reversed, unpredictable",
            StockPattern.UNKNOWN: "Pattern unclear, need more data"
        }
        return descriptions.get(pattern, "Unknown pattern")
    
    def get_recommended_check_times(self, pattern: StockPattern) -> List[float]:
        """
        Get recommended times (hours) to check for exits based on pattern.
        
        Returns:
            List of market hours (e.g., [10.0, 10.5, 11.0] = 10:00, 10:30, 11:00 AM)
        """
        check_times = {
            StockPattern.MORNING_GAPPER: [10.0, 10.5, 11.0],
            StockPattern.MOMENTUM_RUNNER: [11.0, 11.5, 12.0, 12.5, 13.0],
            StockPattern.LATE_BLOOMER: [13.0, 13.5, 14.0, 14.5, 15.0],
            StockPattern.RANGE_BOUND: [11.0, 12.0, 13.0, 14.0],
            StockPattern.REVERSAL: [10.0, 10.5, 11.0, 11.5],
            StockPattern.UNKNOWN: [10.0, 11.0, 12.0, 13.0, 14.0]
        }
        return check_times.get(pattern, [10.0, 12.0, 14.0])


class PatternTracker:
    """
    Tracks patterns for positions over time.
    """
    
    def __init__(self):
        """Initialize pattern tracker"""
        self.position_patterns: Dict[str, StockPattern] = {}
        self.pattern_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.recognizer = PatternRecognizer()
    
    def update_position_pattern(self, symbol: str, 
                               current_price: float,
                               entry_price: float,
                               gap_at_open: Optional[float] = None,
                               minutes_held: int = 0) -> StockPattern:
        """
        Update and return pattern for a position.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            entry_price: Entry price
            gap_at_open: Gap at open (if available)
            minutes_held: Minutes since entry
            
        Returns:
            Identified pattern
        """
        try:
            # Track price history
            if symbol not in self.pattern_history:
                self.pattern_history[symbol] = []
            
            self.pattern_history[symbol].append((datetime.now(), current_price))
            
            # Get price history as list
            price_history = [p[1] for p in self.pattern_history[symbol]]
            
            # Identify pattern
            pattern = self.recognizer.identify_pattern(
                current_price=current_price,
                entry_price=entry_price,
                gap_at_open=gap_at_open,
                minutes_held=minutes_held,
                price_history=price_history
            )
            
            # Update tracked pattern
            old_pattern = self.position_patterns.get(symbol)
            if old_pattern != pattern:
                logger.info(
                    f"📊 {symbol} pattern: {old_pattern.value if old_pattern else 'NEW'} "
                    f"→ {pattern.value}"
                )
            
            self.position_patterns[symbol] = pattern
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error updating pattern for {symbol}: {e}")
            return StockPattern.UNKNOWN
    
    def get_pattern(self, symbol: str) -> Optional[StockPattern]:
        """Get current pattern for symbol"""
        return self.position_patterns.get(symbol)
    
    def clear_position(self, symbol: str):
        """Clear pattern data for exited position"""
        self.position_patterns.pop(symbol, None)
        self.pattern_history.pop(symbol, None)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    recognizer = PatternRecognizer()
    
    # Test morning gapper
    print("\n🧪 Test 1: Morning Gapper")
    pattern = recognizer.identify_pattern(
        current_price=101.5,
        entry_price=100.0,
        gap_at_open=0.02,  # 2% gap at open
        minutes_held=45
    )
    print(f"Pattern: {pattern.value}")
    print(f"Description: {recognizer.get_pattern_description(pattern)}")
    
    # Test momentum runner
    print("\n🧪 Test 2: Momentum Runner")
    pattern = recognizer.identify_pattern(
        current_price=101.0,
        entry_price=100.0,
        gap_at_open=None,
        minutes_held=60,
        price_history=[100.0, 100.3, 100.6, 100.8, 101.0]
    )
    print(f"Pattern: {pattern.value}")
    print(f"Check times: {recognizer.get_recommended_check_times(pattern)}")
