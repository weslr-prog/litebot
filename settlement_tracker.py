"""
T+2 Settlement Tracker
======================
Tracks cash settlement dates for cash account compliance.
Prevents good faith violations and free riding by monitoring unsettled funds.

Author: LiteBotX Team
Date: October 31, 2025
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SettlementRecord:
    """Tracks a single cash settlement"""
    trade_date: date  # Date of sale
    settlement_date: date  # Date cash becomes available (T+2)
    amount: float  # Dollar amount settling
    symbol: str  # Stock symbol sold
    is_settled: bool = False  # True when settlement_date reached
    
    def check_settlement(self, current_date: date) -> bool:
        """Check if settlement date has been reached"""
        if current_date >= self.settlement_date:
            self.is_settled = True
        return self.is_settled


class SettlementTracker:
    """
    Tracks T+2 settlement for cash accounts.
    
    Cash Account Rules:
    - When you sell stock on Day T, cash is "unsettled" until Day T+2
    - Can see the cash but can't trade with it until T+2
    - Trading with unsettled funds then selling before settlement = VIOLATION
    - 3 violations in 12 months = 90-day trading freeze
    
    Usage:
        tracker = SettlementTracker(buffer_amount=50.0)
        
        # After selling stock
        tracker.record_sale(trade_date=date.today(), amount=300.0, symbol="AAPL")
        
        # Before buying stock
        available = tracker.get_settled_cash(account_cash=1000.0)
        if available >= purchase_amount:
            # Safe to buy
            pass
    """
    
    def __init__(self, buffer_amount: float = 50.0):
        """
        Initialize settlement tracker.
        
        Args:
            buffer_amount: Emergency reserve to never trade (safety margin)
        """
        self.buffer_amount = buffer_amount
        self.pending_settlements: List[SettlementRecord] = []
        self.settled_history: List[SettlementRecord] = []
        
    def record_sale(self, trade_date: date, amount: float, symbol: str) -> SettlementRecord:
        """
        Record a stock sale that will settle in T+2.
        
        Args:
            trade_date: Date of sale
            amount: Dollar amount from sale
            symbol: Stock symbol sold
            
        Returns:
            SettlementRecord for tracking
        """
        # Calculate settlement date (T+2 business days)
        settlement_date = self._calculate_settlement_date(trade_date)
        
        record = SettlementRecord(
            trade_date=trade_date,
            settlement_date=settlement_date,
            amount=amount,
            symbol=symbol,
            is_settled=False
        )
        
        self.pending_settlements.append(record)
        
        logger.info(f"📅 Settlement tracked: ${amount:.2f} from {symbol} sale on {trade_date} → settles {settlement_date}")
        
        return record
    
    def _calculate_settlement_date(self, trade_date: date) -> date:
        """
        Calculate T+2 settlement date (skipping weekends).
        
        Args:
            trade_date: Date of trade
            
        Returns:
            Settlement date (2 business days later)
        """
        current = trade_date
        business_days_added = 0
        
        while business_days_added < 2:
            current += timedelta(days=1)
            # Skip weekends (5=Saturday, 6=Sunday)
            if current.weekday() < 5:
                business_days_added += 1
        
        return current
    
    def update_settlements(self, current_date: date) -> List[SettlementRecord]:
        """
        Update settlement status and move settled records to history.
        
        Args:
            current_date: Current date
            
        Returns:
            List of newly settled records
        """
        newly_settled = []
        still_pending = []
        
        for record in self.pending_settlements:
            if record.check_settlement(current_date):
                newly_settled.append(record)
                self.settled_history.append(record)
                logger.info(f"✅ Settlement complete: ${record.amount:.2f} from {record.symbol} now available")
            else:
                still_pending.append(record)
        
        self.pending_settlements = still_pending
        
        return newly_settled
    
    def get_settled_cash(self, account_cash: float, current_date: Optional[date] = None) -> float:
        """
        Calculate how much cash is truly available for trading.
        
        Args:
            account_cash: Total cash shown in account
            current_date: Current date (defaults to today)
            
        Returns:
            Available settled cash (after buffer)
        """
        if current_date is None:
            current_date = date.today()
        
        # Update settlements first
        self.update_settlements(current_date)
        
        # Calculate unsettled amount
        unsettled_amount = sum(r.amount for r in self.pending_settlements if not r.is_settled)
        
        # Available = Total - Unsettled - Buffer
        available = account_cash - unsettled_amount - self.buffer_amount
        
        # Never return negative
        return max(0, available)
    
    def get_unsettled_amount(self) -> float:
        """Get total amount of unsettled cash"""
        return sum(r.amount for r in self.pending_settlements if not r.is_settled)
    
    def get_settlement_summary(self, current_date: Optional[date] = None) -> Dict:
        """
        Get summary of settlement status.
        
        Args:
            current_date: Current date (defaults to today)
            
        Returns:
            Dict with settlement details
        """
        if current_date is None:
            current_date = date.today()
        
        self.update_settlements(current_date)
        
        unsettled_total = self.get_unsettled_amount()
        
        # Group by settlement date
        by_date = {}
        for record in self.pending_settlements:
            settle_date = record.settlement_date
            if settle_date not in by_date:
                by_date[settle_date] = []
            by_date[settle_date].append(record)
        
        return {
            'current_date': current_date,
            'unsettled_total': unsettled_total,
            'pending_count': len(self.pending_settlements),
            'buffer_reserved': self.buffer_amount,
            'by_settlement_date': {
                str(settle_date): {
                    'amount': sum(r.amount for r in records),
                    'symbols': [r.symbol for r in records],
                    'days_until_settlement': (settle_date - current_date).days
                }
                for settle_date, records in sorted(by_date.items())
            }
        }
    
    def check_violation_risk(self, purchase_amount: float, account_cash: float, 
                            current_date: Optional[date] = None) -> tuple[bool, str]:
        """
        Check if a purchase would risk a good faith violation.
        
        A good faith violation occurs when you:
        1. Buy stock with unsettled funds
        2. Sell that stock before the original funds settle
        
        Args:
            purchase_amount: Amount you want to spend
            account_cash: Total cash in account
            current_date: Current date (defaults to today)
            
        Returns:
            (is_risky, warning_message)
        """
        if current_date is None:
            current_date = date.today()
        
        settled_cash = self.get_settled_cash(account_cash, current_date)
        unsettled = self.get_unsettled_amount()
        
        # Safe if buying with settled funds only
        if purchase_amount <= settled_cash:
            return False, "Safe: Using settled funds only"
        
        # Risky if using unsettled funds
        unsettled_usage = purchase_amount - settled_cash
        unsettled_pct = (unsettled_usage / purchase_amount) * 100 if purchase_amount > 0 else 0
        
        warning = (
            f"⚠️ VIOLATION RISK: Purchase uses ${unsettled_usage:.2f} ({unsettled_pct:.1f}%) "
            f"unsettled funds. DO NOT SELL before {self._get_latest_settlement_date()}!"
        )
        
        return True, warning
    
    def _get_latest_settlement_date(self) -> Optional[date]:
        """Get the latest settlement date from pending settlements"""
        if not self.pending_settlements:
            return None
        return max(r.settlement_date for r in self.pending_settlements)
    
    def clear_history(self, days_to_keep: int = 30):
        """
        Clear old settled records to prevent memory bloat.
        
        Args:
            days_to_keep: Keep records from last N days
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        self.settled_history = [
            r for r in self.settled_history 
            if r.settlement_date >= cutoff_date
        ]
        logger.info(f"🧹 Cleared settlement history older than {days_to_keep} days")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("T+2 SETTLEMENT TRACKER DEMO")
    print("=" * 60)
    
    # Initialize tracker with $50 buffer
    tracker = SettlementTracker(buffer_amount=50.0)
    
    # Simulate Monday sale
    monday = date(2025, 11, 4)  # Monday
    tracker.record_sale(monday, 300.0, "AAPL")
    
    # Simulate Tuesday sale
    tuesday = date(2025, 11, 5)  # Tuesday
    tracker.record_sale(tuesday, 200.0, "GOOGL")
    
    # Check status on Tuesday
    print(f"\n📊 Status on Tuesday ({tuesday}):")
    summary = tracker.get_settlement_summary(tuesday)
    print(f"   Unsettled Total: ${summary['unsettled_total']:.2f}")
    print(f"   Pending Settlements: {summary['pending_count']}")
    
    for settle_date, info in summary['by_settlement_date'].items():
        print(f"\n   Settles {settle_date} ({info['days_until_settlement']} days):")
        print(f"      Amount: ${info['amount']:.2f}")
        print(f"      Symbols: {', '.join(info['symbols'])}")
    
    # Check available cash
    account_cash = 1000.0
    available = tracker.get_settled_cash(account_cash, tuesday)
    print(f"\n💰 Cash Availability on Tuesday:")
    print(f"   Account Cash: ${account_cash:.2f}")
    print(f"   Unsettled: ${summary['unsettled_total']:.2f}")
    print(f"   Buffer: ${tracker.buffer_amount:.2f}")
    print(f"   AVAILABLE: ${available:.2f}")
    
    # Check violation risk for a purchase
    purchase = 600.0
    is_risky, warning = tracker.check_violation_risk(purchase, account_cash, tuesday)
    print(f"\n🔍 Risk Check for ${purchase:.2f} purchase:")
    if is_risky:
        print(f"   {warning}")
    else:
        print(f"   ✅ {warning}")
    
    # Fast-forward to Thursday (settlement day for Monday's trade)
    thursday = date(2025, 11, 7)
    print(f"\n📊 Status on Thursday ({thursday}):")
    newly_settled = tracker.update_settlements(thursday)
    print(f"   Newly Settled: {len(newly_settled)} records")
    for record in newly_settled:
        print(f"      ${record.amount:.2f} from {record.symbol}")
    
    available = tracker.get_settled_cash(account_cash, thursday)
    print(f"   AVAILABLE NOW: ${available:.2f}")
    
    print("\n" + "=" * 60)
