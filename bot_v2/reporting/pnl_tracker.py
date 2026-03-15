"""
Daily P&L Tracker for Bot V2
Tracks daily, weekly, and cumulative P&L to measure optimization impact

Created: Jan 13, 2026
Purpose: Track trading performance over time and measure optimization effectiveness
"""

import datetime as dt
import json
import pytz
from pathlib import Path
from typing import Dict, List, Optional
import logging


class PnLTracker:
    """Track and persist daily P&L data for performance analysis"""
    
    def __init__(self, data_dir: str = "bot_v2/data", logger=None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pnl_file = self.data_dir / "pnl_history.json"
        self.logger = logger or logging.getLogger(__name__)
        self.tz = pytz.timezone('America/New_York')
        self._history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load P&L history from file"""
        if self.pnl_file.exists():
            try:
                with open(self.pnl_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load P&L history: {e}")
        return []
    
    def _save_history(self):
        """Save P&L history to file"""
        try:
            with open(self.pnl_file, 'w') as f:
                json.dump(self._history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save P&L history: {e}")
    
    def record_day(self, 
                   realized_pnl: float,
                   unrealized_pnl: float,
                   trades: int,
                   wins: int,
                   entries: int = 0,
                   exits: int = 0,
                   deployed_capital: float = 0.0,
                   account_equity: float = 0.0,
                   strategy_breakdown: Optional[Dict] = None,
                   notes: str = "") -> Dict:
        """
        Record today's P&L and trading activity.
        
        Args:
            realized_pnl: Realized P&L from closed positions
            unrealized_pnl: Unrealized P&L from open positions  
            trades: Total trades (entries + exits)
            wins: Number of winning trades
            entries: Number of entries today
            exits: Number of exits today
            deployed_capital: Capital in open positions
            account_equity: Current account equity
            strategy_breakdown: Optional dict with per-strategy stats
            notes: Optional notes for the day
            
        Returns:
            Dict with the recorded day's data
        """
        now = dt.datetime.now(self.tz)
        date_str = now.strftime('%Y-%m-%d')
        
        # Check if we already have an entry for today (update it)
        existing_idx = None
        for i, entry in enumerate(self._history):
            if entry.get('date') == date_str:
                existing_idx = i
                break
        
        total_pnl = realized_pnl + unrealized_pnl
        wins = max(0, int(wins))
        exits = max(0, int(exits))
        if wins > exits:
            wins = exits
        losses = max(0, exits - wins)
        win_rate = (wins / exits * 100) if exits > 0 else 0.0
        pnl_pct = (total_pnl / deployed_capital * 100) if deployed_capital > 0 else 0.0
        
        day_data = {
            'date': date_str,
            'day_of_week': now.strftime('%A'),
            'realized_pnl': round(realized_pnl, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'total_pnl': round(total_pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'trades': trades,
            'entries': entries,
            'exits': exits,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'deployed_capital': round(deployed_capital, 2),
            'account_equity': round(account_equity, 2),
            'strategy_breakdown': strategy_breakdown or {},
            'notes': notes,
            'recorded_at': now.isoformat()
        }
        
        if existing_idx is not None:
            self._history[existing_idx] = day_data
            self.logger.info(f"📊 Updated P&L for {date_str}: ${total_pnl:+.2f} ({pnl_pct:+.1f}%)")
        else:
            self._history.append(day_data)
            self.logger.info(f"📊 Recorded P&L for {date_str}: ${total_pnl:+.2f} ({pnl_pct:+.1f}%)")
        
        self._save_history()
        return day_data
    
    def get_today(self) -> Optional[Dict]:
        """Get today's P&L record if it exists"""
        today = dt.datetime.now(self.tz).strftime('%Y-%m-%d')
        for entry in reversed(self._history):
            if entry.get('date') == today:
                return entry
        return None
    
    def get_week_stats(self) -> Dict:
        """Get week-to-date statistics"""
        now = dt.datetime.now(self.tz)
        week_start = now - dt.timedelta(days=now.weekday())
        week_start_str = week_start.strftime('%Y-%m-%d')
        
        week_entries = [e for e in self._history if e.get('date', '') >= week_start_str]
        
        if not week_entries:
            return {
                'total_pnl': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'trading_days': 0,
                'avg_daily_pnl': 0.0
            }
        
        total_pnl = sum(e.get('realized_pnl', 0) for e in week_entries)
        unrealized = week_entries[-1].get('unrealized_pnl', 0) if week_entries else 0
        trades = sum(e.get('trades', 0) for e in week_entries)
        wins = sum(e.get('wins', 0) for e in week_entries)
        losses = sum(e.get('losses', 0) for e in week_entries)
        
        return {
            'total_pnl': round(total_pnl + unrealized, 2),
            'realized_pnl': round(total_pnl, 2),
            'unrealized_pnl': round(unrealized, 2),
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round((wins / (wins + losses) * 100) if (wins + losses) > 0 else 0, 1),
            'trading_days': len(week_entries),
            'avg_daily_pnl': round(total_pnl / len(week_entries), 2) if week_entries else 0.0
        }
    
    def get_month_stats(self) -> Dict:
        """Get month-to-date statistics"""
        now = dt.datetime.now(self.tz)
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        
        month_entries = [e for e in self._history if e.get('date', '') >= month_start]
        
        if not month_entries:
            return {
                'total_pnl': 0.0,
                'trades': 0,
                'win_rate': 0.0,
                'trading_days': 0,
                'best_day': 0.0,
                'worst_day': 0.0
            }
        
        pnl_values = [e.get('realized_pnl', 0) for e in month_entries]
        total_pnl = sum(pnl_values)
        wins = sum(e.get('wins', 0) for e in month_entries)
        losses = sum(e.get('losses', 0) for e in month_entries)
        
        return {
            'total_pnl': round(total_pnl, 2),
            'trades': sum(e.get('trades', 0) for e in month_entries),
            'win_rate': round((wins / (wins + losses) * 100) if (wins + losses) > 0 else 0, 1),
            'trading_days': len(month_entries),
            'best_day': round(max(pnl_values), 2) if pnl_values else 0,
            'worst_day': round(min(pnl_values), 2) if pnl_values else 0
        }
    
    def get_cumulative_stats(self) -> Dict:
        """Get all-time cumulative statistics"""
        if not self._history:
            return {
                'total_pnl': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'trading_days': 0,
                'best_day': 0.0,
                'worst_day': 0.0,
                'avg_daily_pnl': 0.0,
                'streak_current': 0,
                'streak_best_wins': 0,
                'streak_worst_losses': 0
            }
        
        pnl_values = [e.get('realized_pnl', 0) for e in self._history]
        total_pnl = sum(pnl_values)
        wins = sum(e.get('wins', 0) for e in self._history)
        losses = sum(e.get('losses', 0) for e in self._history)
        
        # Calculate streaks
        current_streak = 0
        best_win_streak = 0
        worst_loss_streak = 0
        temp_streak = 0
        
        for entry in self._history:
            pnl = entry.get('realized_pnl', 0)
            if pnl > 0:
                if temp_streak >= 0:
                    temp_streak += 1
                else:
                    temp_streak = 1
                best_win_streak = max(best_win_streak, temp_streak)
            elif pnl < 0:
                if temp_streak <= 0:
                    temp_streak -= 1
                else:
                    temp_streak = -1
                worst_loss_streak = min(worst_loss_streak, temp_streak)
            current_streak = temp_streak
        
        return {
            'total_pnl': round(total_pnl, 2),
            'total_trades': sum(e.get('trades', 0) for e in self._history),
            'win_rate': round((wins / (wins + losses) * 100) if (wins + losses) > 0 else 0, 1),
            'trading_days': len(self._history),
            'best_day': round(max(pnl_values), 2) if pnl_values else 0,
            'worst_day': round(min(pnl_values), 2) if pnl_values else 0,
            'avg_daily_pnl': round(total_pnl / len(self._history), 2) if self._history else 0,
            'streak_current': current_streak,
            'streak_best_wins': best_win_streak,
            'streak_worst_losses': abs(worst_loss_streak)
        }
    
    def print_summary(self):
        """Print a formatted P&L summary to console"""
        week = self.get_week_stats()
        month = self.get_month_stats()
        cumulative = self.get_cumulative_stats()
        today = self.get_today()
        
        print("\n" + "=" * 60)
        print("📊 P&L PERFORMANCE SUMMARY")
        print("=" * 60)
        
        if today:
            print(f"\n📅 TODAY ({today['date']}):")
            print(f"   Realized: ${today['realized_pnl']:+.2f}")
            print(f"   Unrealized: ${today['unrealized_pnl']:+.2f}")
            print(f"   Total: ${today['total_pnl']:+.2f} ({today['pnl_pct']:+.1f}%)")
            print(f"   Win Rate: {today['win_rate']:.0f}% ({today['wins']}/{today['exits']} exits)")
        
        print(f"\n📅 THIS WEEK:")
        print(f"   P&L: ${week['total_pnl']:+.2f} | Win Rate: {week['win_rate']:.0f}%")
        print(f"   Trades: {week['trades']} | Trading Days: {week['trading_days']}")
        
        print(f"\n📅 THIS MONTH:")
        print(f"   P&L: ${month['total_pnl']:+.2f} | Win Rate: {month['win_rate']:.0f}%")
        print(f"   Best Day: ${month['best_day']:+.2f} | Worst Day: ${month['worst_day']:+.2f}")
        
        print(f"\n📅 ALL TIME:")
        print(f"   P&L: ${cumulative['total_pnl']:+.2f} | Win Rate: {cumulative['win_rate']:.0f}%")
        print(f"   Avg Daily: ${cumulative['avg_daily_pnl']:+.2f}")
        print(f"   Trading Days: {cumulative['trading_days']}")
        
        print("=" * 60)


# Utility function for quick P&L recording from main bot
def record_daily_pnl(realized: float = 0, unrealized: float = 0, 
                     trades: int = 0, wins: int = 0, 
                     entries: int = 0, exits: int = 0,
                     deployed: float = 0, equity: float = 0) -> Dict:
    """Quick helper to record today's P&L"""
    tracker = PnLTracker()
    return tracker.record_day(
        realized_pnl=realized,
        unrealized_pnl=unrealized,
        trades=trades,
        wins=wins,
        entries=entries,
        exits=exits,
        deployed_capital=deployed,
        account_equity=equity
    )


def show_pnl_summary():
    """Quick helper to show P&L summary"""
    tracker = PnLTracker()
    tracker.print_summary()


if __name__ == "__main__":
    # Test the tracker
    tracker = PnLTracker()
    tracker.print_summary()
