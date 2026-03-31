#!/usr/bin/env python3
"""
Entry Quality Screener - Real-time trade quality validation
Based on predictive characteristic analysis from historical backtests.

This module provides forward-looking screening rules that the bot can use
to reject low-quality entries BEFORE placing trades.

Key insight: Instead of cherry-picking stocks, we screen based on CHARACTERISTICS
(momentum range, volume pattern, sector) that are predictive of success.
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class EntryQualityScreener:
    """
    Screens potential entries for quality indicators.
    
    Based on backtest analysis showing:
    - Momentum sweet spot: 6-9% (best win rates)
    - Volume sweet spot: 1.25-2.0x surge
    - Best combination: 6-8% momentum + 1.5-2x volume = 61.1% win rate
    - Sector impact: Airlines/Travel (51.6% win) vs Consumer (39.2% win)
    """
    
    # Thresholds from backtest analysis
    # Dec 4: Changed for MEAN REVERSION (not momentum)
    # Dec 8: Adjusted volume for mean reversion (quality stocks don't surge on volume)
    MOMENTUM_MIN = -0.02  # -2% - allow stabilizing/flat stocks (was 4% for momentum strategy)
    MOMENTUM_SWEET_MIN = -0.01  # -1% - start of mean reversion sweet spot
    MOMENTUM_SWEET_MAX = 0.02  # +2% - end of sweet spot (stabilized, ready to bounce)
    MOMENTUM_MAX = 0.04  # 4% - above this, already bouncing (late entry for mean reversion)
    
    VOLUME_MIN = 0.70  # Mean reversion: 70% of avg (quiet accumulation) - was 1.25x for momentum
    VOLUME_SWEET_MIN = 0.90  # Start of best range for mean reversion (normal institutional volume)
    VOLUME_SWEET_MAX = 1.50  # End of best range (steady accumulation)
    VOLUME_MAX = 3.00  # Above this = panic selling, not mean reversion (was 2.00)
    
    # Sector classifications based on backtest
    GOOD_SECTORS = ['Airlines/Travel', 'Airline', 'Travel', 'Cruise']
    ACCEPTABLE_SECTORS = ['Automotive', 'Auto', 'Energy']
    BAD_SECTORS = ['Consumer', 'Retail', 'Restaurant']
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize screener.
        
        Args:
            strict_mode: If True, only accept ideal conditions (6-8% momentum, 1.5-2x volume)
                        If False, accept broader range (4-10% momentum, 1.25-2x volume)
        """
        self.strict_mode = strict_mode
        logger.info(f"EntryQualityScreener initialized (strict_mode={strict_mode})")
    
    def screen_entry(
        self,
        symbol: str,
        momentum: float,
        volume_surge: float,
        sector: str = None
    ) -> Tuple[bool, str, str]:
        """
        Screen a potential entry for quality.
        
        Args:
            symbol: Stock ticker
            momentum: Daily momentum as decimal (e.g., 0.0721 = 7.21%)
            volume_surge: Volume ratio vs 20-day avg (e.g., 1.63)
            sector: Optional sector classification
        
        Returns:
            Tuple of (should_enter: bool, quality_level: str, reason: str)
            
            quality_level: 'IDEAL', 'GOOD', 'ACCEPTABLE', 'REJECT'
        
        Example:
            >>> screener = EntryQualityScreener()
            >>> should_enter, quality, reason = screener.screen_entry('AAL', 0.0721, 1.63, 'Airlines')
            >>> print(f"{quality}: {reason}")
            IDEAL: 7.2% momentum in sweet spot (6-9%), 1.63x volume in ideal range (1.5-2x), Airlines/Travel sector (51.6% historical win rate)
        """
        
        # Convert to percentages for logging
        momentum_pct = momentum * 100
        
        # RED FLAG 1: Still falling too fast (mean reversion needs stabilization)
        if momentum < self.MOMENTUM_MIN:
            reason = f"Still falling too fast ({momentum_pct:.1f}% < -2%) - Need stabilization for mean reversion"
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # RED FLAG 2: Already bouncing (late entry for mean reversion)
        if momentum > self.MOMENTUM_MAX:
            reason = f"Already bouncing ({momentum_pct:.1f}% > 4%) - Late entry for mean reversion, buy BEFORE bounce"
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # RED FLAG 3: Volume too weak
        if volume_surge < self.VOLUME_MIN:
            reason = f"Volume too weak ({volume_surge:.2f}x < {self.VOLUME_MIN}x) - Below minimum for quality entry"
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # RED FLAG 4: Volume too extreme (panic/false breakout risk)
        if volume_surge > self.VOLUME_MAX:
            reason = f"Volume too extreme ({volume_surge:.2f}x > {self.VOLUME_MAX}x) - Panic selling, not mean reversion"
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # RED FLAG 5: Bad sector
        if sector and any(bad in sector for bad in self.BAD_SECTORS):
            reason = f"Sector '{sector}' has poor historical fit - Historical win rate: 39.2%"
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # Check for IDEAL conditions (61.1% win rate combination)
        in_sweet_momentum = self.MOMENTUM_SWEET_MIN <= momentum <= self.MOMENTUM_SWEET_MAX
        in_sweet_volume = self.VOLUME_SWEET_MIN <= volume_surge <= self.VOLUME_SWEET_MAX
        in_good_sector = sector and any(good in sector for good in self.GOOD_SECTORS)
        
        if in_sweet_momentum and in_sweet_volume and in_good_sector:
            reason = (
                f"{momentum_pct:.1f}% momentum in sweet spot (-1% to +2% - stabilized), "
                f"{volume_surge:.2f}x volume in ideal range (1.5-2x), "
                f"{sector} sector (mean reversion setup)"
            )
            logger.info(f"✅ IDEAL {symbol}: {reason}")
            return True, 'IDEAL', reason
        
        # Check for GOOD conditions (sweet spot momentum)
        if in_sweet_momentum:
            reason = (
                f"{momentum_pct:.1f}% momentum in sweet spot (-1% to +2% - stabilized), "
                f"{volume_surge:.2f}x volume"
            )
            if in_good_sector:
                reason += f", {sector} sector"
            logger.info(f"✅ GOOD {symbol}: {reason}")
            return True, 'GOOD', reason
        
        # In strict mode, only accept IDEAL or GOOD
        if self.strict_mode:
            reason = (
                f"Strict mode: {momentum_pct:.1f}% momentum outside sweet spot (-1% to +2%), "
                f"requires ideal conditions"
            )
            logger.warning(f"REJECT {symbol}: {reason}")
            return False, 'REJECT', reason
        
        # ACCEPTABLE (but not ideal)
        reason = (
            f"{momentum_pct:.1f}% momentum (acceptable but not in sweet spot -1% to +2%), "
            f"{volume_surge:.2f}x volume"
        )
        logger.info(f"⚠️  ACCEPTABLE {symbol}: {reason}")
        return True, 'ACCEPTABLE', reason
    
    def get_screening_stats(self) -> dict:
        """
        Get statistics about screening thresholds.
        
        Returns:
            Dictionary with threshold info and historical performance
        """
        return {
            'momentum': {
                'min': self.MOMENTUM_MIN,
                'sweet_spot': f"{self.MOMENTUM_SWEET_MIN}-{self.MOMENTUM_SWEET_MAX}",
                'max': self.MOMENTUM_MAX,
                'sweet_spot_win_rate': 0.522  # 52.2% for 8-9%
            },
            'volume': {
                'min': self.VOLUME_MIN,
                'sweet_spot': f"{self.VOLUME_SWEET_MIN}-{self.VOLUME_SWEET_MAX}",
                'max': self.VOLUME_MAX,
                'sweet_spot_win_rate': 0.512  # 51.2% for 1.25-1.5x
            },
            'best_combination': {
                'momentum': '6-8%',
                'volume': '1.5-2.0x',
                'win_rate': 0.611  # 61.1%
            },
            'sectors': {
                'good': self.GOOD_SECTORS,
                'bad': self.BAD_SECTORS
            }
        }


# Convenience functions for quick screening
def screen_entry(
    symbol: str,
    momentum: float,
    volume_surge: float,
    sector: str = None,
    strict: bool = False
) -> Tuple[bool, str, str]:
    """
    Quick screening function without instantiating screener.
    
    Args:
        symbol: Stock ticker
        momentum: Daily momentum as decimal
        volume_surge: Volume ratio vs average
        sector: Optional sector
        strict: Whether to use strict mode
    
    Returns:
        (should_enter, quality_level, reason)
    """
    screener = EntryQualityScreener(strict_mode=strict)
    return screener.screen_entry(symbol, momentum, volume_surge, sector)


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("=" * 80)
    print("ENTRY QUALITY SCREENER - EXAMPLES")
    print("=" * 80)
    
    screener = EntryQualityScreener(strict_mode=False)
    
    # Test cases from Nov 14 analysis
    test_cases = [
        # Nov 14 losers
        ("RIVN", 0.0371, 1.25, "Automotive", "Nov 14 loser - weak momentum"),
        ("NCLH", 0.0543, 1.47, "Cruise", "Nov 14 loser - below sweet spot"),
        
        # Ideal entries (would have been winners)
        ("AAL", 0.0721, 1.63, "Airlines", "Ideal combination"),
        ("JBLU", 0.0812, 1.52, "Airlines", "Ideal combination"),
        
        # Edge cases
        ("PLUG", 0.1010, 1.85, "Energy", "Too high momentum (late entry)"),
        ("SBUX", 0.0599, 1.77, "Consumer", "Bad sector"),
        ("SIRI", 0.0543, 1.70, "Consumer", "Bad sector + weak momentum"),
        
        # Extreme volume (false breakouts)
        ("XYZ", 0.0750, 3.50, None, "Extreme volume (>3x)"),
        
        # Weak signals
        ("ABC", 0.0320, 1.30, None, "Too weak momentum (<4%)"),
    ]
    
    print("\nTest Cases:")
    print("-" * 80)
    
    for symbol, momentum, volume, sector, description in test_cases:
        should_enter, quality, reason = screener.screen_entry(
            symbol, momentum, volume, sector
        )
        
        status = "✅ PASS" if should_enter else "🚨 REJECT"
        print(f"\n{status} {symbol} ({description})")
        print(f"  Quality: {quality}")
        print(f"  Momentum: {momentum*100:.1f}% | Volume: {volume:.2f}x | Sector: {sector or 'N/A'}")
        print(f"  Reason: {reason}")
    
    print("\n" + "=" * 80)
    print("SCREENING STATISTICS")
    print("=" * 80)
    
    stats = screener.get_screening_stats()
    print(f"\nMomentum thresholds:")
    print(f"  Sweet spot: {stats['momentum']['sweet_spot']} (Win rate: {stats['momentum']['sweet_spot_win_rate']:.1%})")
    print(f"  Acceptable: {stats['momentum']['min']}-{stats['momentum']['max']}")
    
    print(f"\nVolume thresholds:")
    print(f"  Sweet spot: {stats['volume']['sweet_spot']} (Win rate: {stats['volume']['sweet_spot_win_rate']:.1%})")
    print(f"  Acceptable: {stats['volume']['min']}-{stats['volume']['max']}")
    
    print(f"\nBest combination:")
    print(f"  Momentum: {stats['best_combination']['momentum']}")
    print(f"  Volume: {stats['best_combination']['volume']}")
    print(f"  Historical win rate: {stats['best_combination']['win_rate']:.1%}")
    
    print(f"\nSector preferences:")
    print(f"  Good sectors: {', '.join(stats['sectors']['good'])}")
    print(f"  Avoid sectors: {', '.join(stats['sectors']['bad'])}")
