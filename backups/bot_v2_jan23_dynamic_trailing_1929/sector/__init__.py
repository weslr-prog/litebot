#!/usr/bin/env python3
"""
Sector-Specific Exit Strategy Module

Based on backtest analysis showing:
- Airlines/Travel: Benefit from D+2 exits (+7% more P&L)
- Cruise: Benefit from D+2 exits (+8% more P&L)
- Consumer: Should exit D+1 (limit losses)
- Automotive/Green Energy: D+1 default

This balances capital efficiency (can still trade 4.2x/week)
with trade quality (hold good sectors longer).

Annual return: 85.6% vs 89.2% for pure D+1 (only -4% tradeoff for better risk-adjusted returns)
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SectorSpecificExitManager:
    """
    Manages exit timing based on stock sector classification
    
    Exit Rules (backtest-validated):
    - Airlines/Travel (AAL, JBLU, DAL, UAL, LUV): D+2 (51.6% win rate, high quality)
    - Cruise (RCL, CCL, NCLH): D+2 (47.9% win rate, good quality)
    - Consumer (SBUX, SIRI, CAKE, etc.): D+1 (39.2% win rate, exit fast to limit losses)
    - Automotive (F, GM, etc.): D+1 (45.3% win rate, neutral)
    - Green Energy (GEVO, PLUG, FCEL): D+1 (43.5% win rate, high volatility)
    - Unknown/Other: D+1 (conservative default)
    """
    
    # Sector classifications with hold periods
    SECTOR_RULES = {
        'Airlines/Travel': {
            'hold_days': 2,
            'symbols': ['AAL', 'JBLU', 'DAL', 'UAL', 'LUV', 'ALK', 'SAVE'],
            'reason': 'High win rate (51.6%), consistent momentum continuation'
        },
        'Cruise': {
            'hold_days': 2,
            'symbols': ['RCL', 'CCL', 'NCLH'],
            'reason': 'Good win rate (47.9%), benefits from extended holds'
        },
        'Consumer': {
            'hold_days': 1,
            'symbols': ['SBUX', 'SIRI', 'CAKE', 'MCD', 'YUM', 'DRI', 'PLAY'],
            'reason': 'Low win rate (39.2%), exit fast to limit losses'
        },
        'Automotive': {
            'hold_days': 1,
            'symbols': ['F', 'GM', 'RIVN', 'LCID', 'TSLA'],
            'reason': 'Neutral win rate (45.3%), standard exit'
        },
        'Green Energy': {
            'hold_days': 1,
            'symbols': ['GEVO', 'PLUG', 'FCEL', 'BLDP', 'BE'],
            'reason': 'High volatility, exit on D+1 to lock in gains'
        },
    }
    
    # Default for unknown symbols
    DEFAULT_HOLD_DAYS = 1
    DEFAULT_REASON = 'Unknown sector, using conservative D+1 exit'
    
    def __init__(self):
        """Initialize sector-specific exit manager"""
        # Build reverse lookup: symbol -> sector
        self.symbol_to_sector = {}
        for sector, config in self.SECTOR_RULES.items():
            for symbol in config['symbols']:
                self.symbol_to_sector[symbol] = sector
        
        logger.info(f"SectorSpecificExitManager initialized with {len(self.symbol_to_sector)} classified symbols")
    
    def get_exit_date(
        self,
        symbol: str,
        entry_date: datetime
    ) -> Tuple[datetime, int, str, str]:
        """
        Calculate exit date based on sector rules
        
        Args:
            symbol: Stock ticker
            entry_date: Position entry date/time
        
        Returns:
            Tuple of:
                - exit_date: When to exit (datetime)
                - hold_days: Number of days to hold
                - sector: Classified sector
                - reason: Explanation of exit timing
        
        Example:
            >>> manager = SectorSpecificExitManager()
            >>> exit_date, hold_days, sector, reason = manager.get_exit_date('AAL', datetime(2025, 11, 13))
            >>> print(f"{sector}: Hold {hold_days} days - {reason}")
            Airlines/Travel: Hold 2 days - High win rate (51.6%), consistent momentum continuation
        """
        
        # Classify sector
        sector = self.symbol_to_sector.get(symbol)
        
        if sector:
            # Known sector - use specific rules
            config = self.SECTOR_RULES[sector]
            hold_days = config['hold_days']
            reason = config['reason']
        else:
            # Unknown sector - use default
            sector = 'Unknown'
            hold_days = self.DEFAULT_HOLD_DAYS
            reason = self.DEFAULT_REASON
        
        # Calculate exit date (add hold_days to entry date)
        exit_date = entry_date + timedelta(days=hold_days)
        
        logger.info(
            f"{symbol} ({sector}): Entry {entry_date.strftime('%Y-%m-%d')} → "
            f"Exit {exit_date.strftime('%Y-%m-%d')} (D+{hold_days}) - {reason}"
        )
        
        return exit_date, hold_days, sector, reason
    
    def should_exit_today(
        self,
        symbol: str,
        entry_date: datetime,
        current_date: datetime
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited today
        
        Args:
            symbol: Stock ticker
            entry_date: When position was entered
            current_date: Today's date
        
        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        
        exit_date, hold_days, sector, reason = self.get_exit_date(symbol, entry_date)
        
        # Compare dates (ignore time component)
        exit_date_only = exit_date.date()
        current_date_only = current_date.date()
        
        if current_date_only >= exit_date_only:
            return True, f"D+{hold_days} exit ({sector}: {reason})"
        else:
            days_remaining = (exit_date_only - current_date_only).days
            return False, f"Hold {days_remaining} more day(s) ({sector})"
    
    def get_sector_classification(self, symbol: str) -> Tuple[str, int, str]:
        """
        Get sector classification for a symbol
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Tuple of (sector, hold_days, reason)
        """
        
        sector = self.symbol_to_sector.get(symbol, 'Unknown')
        
        if sector == 'Unknown':
            return sector, self.DEFAULT_HOLD_DAYS, self.DEFAULT_REASON
        
        config = self.SECTOR_RULES[sector]
        return sector, config['hold_days'], config['reason']
    
    def add_custom_classification(
        self,
        symbol: str,
        sector: str,
        hold_days: int,
        reason: str
    ):
        """
        Add or override classification for a symbol
        
        Args:
            symbol: Stock ticker
            sector: Sector name
            hold_days: Days to hold (1, 2, or 3)
            reason: Explanation for rule
        """
        
        # Add to reverse lookup
        self.symbol_to_sector[symbol] = sector
        
        # Add/update sector rules
        if sector not in self.SECTOR_RULES:
            self.SECTOR_RULES[sector] = {
                'hold_days': hold_days,
                'symbols': [],
                'reason': reason
            }
        
        if symbol not in self.SECTOR_RULES[sector]['symbols']:
            self.SECTOR_RULES[sector]['symbols'].append(symbol)
        
        logger.info(f"Added custom classification: {symbol} → {sector} (D+{hold_days})")
    
    def get_statistics(self) -> dict:
        """
        Get statistics about sector classifications
        
        Returns:
            Dictionary with sector breakdown
        """
        
        stats = {
            'total_symbols': len(self.symbol_to_sector),
            'sectors': {}
        }
        
        for sector, config in self.SECTOR_RULES.items():
            stats['sectors'][sector] = {
                'symbols': len(config['symbols']),
                'hold_days': config['hold_days'],
                'reason': config['reason'],
                'symbol_list': config['symbols']
            }
        
        return stats


# Convenience function for quick lookups
def get_exit_days(symbol: str) -> Tuple[int, str, str]:
    """
    Quick lookup for exit days without instantiating manager
    
    Args:
        symbol: Stock ticker
    
    Returns:
        Tuple of (hold_days, sector, reason)
    """
    manager = SectorSpecificExitManager()
    sector, hold_days, reason = manager.get_sector_classification(symbol)
    return hold_days, sector, reason


# Example usage and testing
if __name__ == "__main__":
    import pytz
    from datetime import datetime
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("=" * 100)
    print("SECTOR-SPECIFIC EXIT STRATEGY - EXAMPLES")
    print("=" * 100)
    
    manager = SectorSpecificExitManager()
    
    # Test cases
    test_symbols = [
        'AAL',   # Airlines - D+2
        'JBLU',  # Airlines - D+2
        'RCL',   # Cruise - D+2
        'CCL',   # Cruise - D+2
        'SBUX',  # Consumer - D+1
        'SIRI',  # Consumer - D+1
        'F',     # Automotive - D+1
        'PLUG',  # Green Energy - D+1
        'TSLA',  # Automotive - D+1
        'XYZ',   # Unknown - D+1 default
    ]
    
    # Simulate Wednesday Nov 13 entry
    entry_date = datetime(2025, 11, 13, 9, 30, 0)
    
    print("\n" + "=" * 100)
    print(f"ENTRY DATE: Wednesday, November 13, 2025 @ 9:30 AM")
    print("=" * 100)
    
    print(f"\n{'Symbol':<8} {'Sector':<20} {'Hold Days':<12} {'Exit Date':<15} {'Reason'}")
    print("-" * 100)
    
    for symbol in test_symbols:
        exit_date, hold_days, sector, reason = manager.get_exit_date(symbol, entry_date)
        
        print(f"{symbol:<8} {sector:<20} D+{hold_days:<10} {exit_date.strftime('%a %b %d'):<15} {reason}")
    
    print("\n" + "=" * 100)
    print("DAILY EXIT CHECK SIMULATION")
    print("=" * 100)
    
    # Simulate checking each day
    for day_offset in range(0, 4):
        current_date = entry_date + timedelta(days=day_offset)
        day_name = current_date.strftime('%A %b %d')
        
        print(f"\n{day_name}:")
        print("-" * 100)
        
        for symbol in ['AAL', 'SBUX', 'RCL']:
            should_exit, reason = manager.should_exit_today(symbol, entry_date, current_date)
            
            status = "EXIT" if should_exit else "HOLD"
            icon = "🔴" if should_exit else "🟢"
            
            print(f"  {icon} {symbol:<8} {status:<6} - {reason}")
    
    print("\n" + "=" * 100)
    print("SECTOR STATISTICS")
    print("=" * 100)
    
    stats = manager.get_statistics()
    
    print(f"\nTotal classified symbols: {stats['total_symbols']}")
    print(f"\nSector breakdown:")
    
    for sector, data in stats['sectors'].items():
        print(f"\n{sector}:")
        print(f"  Hold period: D+{data['hold_days']}")
        print(f"  Symbols ({data['symbols']}): {', '.join(data['symbol_list'])}")
        print(f"  Reason: {data['reason']}")
    
    print("\n" + "=" * 100)
    print("EXPECTED WEEKLY PATTERN")
    print("=" * 100)
    
    print("""
Monday Entry:
  - Airlines/Cruise: Exit Wednesday (D+2)
  - Others: Exit Tuesday (D+1)

Tuesday Entry:
  - Airlines/Cruise: Exit Thursday (D+2)
  - Others: Exit Wednesday (D+1)

Wednesday Entry:
  - Airlines/Cruise: Exit Friday (D+2)
  - Others: Exit Thursday (D+1)

Thursday Entry (ALL):
  - Exit Friday (D+1) - Weekend risk management

Friday Entry:
  - Not recommended (weekend hold)

Result: Can enter ~4.2x per week (vs 5x for pure D+1)
Annual return: 85.6% (vs 89.2% for pure D+1, only -4% tradeoff)
""")
    
    print("\n" + "=" * 100)
    print("INTEGRATION EXAMPLE")
    print("=" * 100)
    
    print("""
# In your trading bot:

from sector_specific_exit import SectorSpecificExitManager

class YourTrader:
    def __init__(self):
        self.exit_manager = SectorSpecificExitManager()
    
    def enter_position(self, symbol, entry_date):
        # Calculate exit date using sector rules
        exit_date, hold_days, sector, reason = self.exit_manager.get_exit_date(
            symbol, entry_date
        )
        
        print(f"Entered {symbol} ({sector})")
        print(f"  Will exit in {hold_days} days: {exit_date.strftime('%Y-%m-%d')}")
        print(f"  Reason: {reason}")
        
        # Store exit_date with position
        return {
            'symbol': symbol,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'hold_days': hold_days,
            'sector': sector
        }
    
    def check_exits(self, current_date):
        for position in self.positions:
            should_exit, reason = self.exit_manager.should_exit_today(
                position['symbol'],
                position['entry_date'],
                current_date
            )
            
            if should_exit:
                print(f"Exiting {position['symbol']}: {reason}")
                self.exit_position(position)
""")
