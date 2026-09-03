"""
Daily Summary Report Generator
Provides end-of-day trading summary and performance analysis
"""

import datetime as dt
import pytz
from typing import Dict, List
import logging
from pathlib import Path
import json


class DailySummary:
    """Generate end-of-day summary report"""
    
    def __init__(self, data_loader, position_tracker, logger=None):
        self.data_loader = data_loader
        self.position_tracker = position_tracker
        self.logger = logger or logging.getLogger(__name__)
        self.tz = pytz.timezone('America/New_York')
        self.stats_file = Path("bot_v2/data/daily_stats.json")
    
    def generate_summary(self, session_data: Dict) -> Dict:
        """
        Generate daily summary report
        
        Args:
            session_data: Dict with today's activity:
                - scans_run: int
                - candidates_reviewed: List[str] (unique symbols)
                - signals_generated: int
                - entries_executed: List[Dict]
                - rejections: Dict[str, int]
        
        Returns:
            Dict with complete daily summary
        """
        now = dt.datetime.now(self.tz)
        
        try:
            # Get market performance
            spy_performance = self._get_spy_performance()
            vix_change = self._get_vix_change()
            
            # Get trading activity
            positions = self.position_tracker.get_positions()
            active_positions = [p for p in positions if p.status == 'open']
            # exit_date is already a date object, don't call .date() on it
            closed_today = [p for p in positions if p.exit_date and p.exit_date == now.date()]
            
            # Calculate P&L
            realized_pnl = sum(p.realized_pnl for p in closed_today if p.realized_pnl)
            unrealized_pnl = sum(self._calculate_unrealized_pnl(p) for p in active_positions)
            total_pnl = realized_pnl + unrealized_pnl
            
            # Get deployed capital
            deployed_capital = sum(p.entry_price * p.shares for p in active_positions)
            pnl_pct = (total_pnl / deployed_capital * 100) if deployed_capital > 0 else 0
            
            # Calculate setup quality (retroactive)
            setup_quality = self._calculate_setup_quality_retroactive(session_data)
            
            # Get week-to-date stats
            wtd_stats = self._get_week_to_date_stats(now)
            
            summary = {
                'date': now.strftime('%A, %B %d, %Y'),
                'time': now.strftime('%I:%M %p ET'),
                'market': {
                    'spy_change': spy_performance,
                    'vix_change': vix_change,
                    'setup_quality': setup_quality
                },
                'activity': {
                    'scans_run': session_data.get('scans_run', 0),
                    'candidates_reviewed': len(set(session_data.get('candidates_reviewed', []))),
                    'signals_generated': session_data.get('signals_generated', 0),
                    'entries_executed': len(session_data.get('entries_executed', [])),
                    'positions_overnight': len(active_positions)
                },
                'pnl': {
                    'realized': realized_pnl,
                    'unrealized': unrealized_pnl,
                    'total': total_pnl,
                    'total_pct': pnl_pct,
                    'deployed_capital': deployed_capital
                },
                'rejections': session_data.get('rejections', {}),
                'entries': session_data.get('entries_executed', []),
                'exits': [self._format_exit(p) for p in closed_today],
                'open_positions': [self._format_position(p) for p in active_positions],
                'week_stats': wtd_stats,
                'next_session': self._get_next_session(now)
            }
            
            # Save daily stats for historical tracking
            self._save_daily_stats(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate daily summary: {e}")
            return self._get_fallback_summary(now)
    
    def _get_spy_performance(self) -> float:
        """Get SPY daily performance"""
        try:
            bars = self.data_loader.get_bars(['SPY'], timeframe='1Day', limit=1)
            if 'SPY' in bars and len(bars['SPY']) > 0:
                bar = bars['SPY'][-1]
                return ((bar.close - bar.open) / bar.open) * 100
            return 0.0
        except:
            return 0.0
    
    def _get_vix_change(self) -> float:
        """Get VIX daily change"""
        try:
            bars = self.data_loader.get_bars(['VIX'], timeframe='1Day', limit=2)
            if 'VIX' in bars and len(bars['VIX']) >= 2:
                yesterday = bars['VIX'][-2].close
                today = bars['VIX'][-1].close
                return today - yesterday
            return 0.0
        except:
            return 0.0
    
    def _calculate_unrealized_pnl(self, position) -> float:
        """Calculate unrealized P&L for open position"""
        try:
            # Get current price
            bars = self.data_loader.get_bars([position.symbol], timeframe='1Day', limit=1)
            if position.symbol in bars and len(bars[position.symbol]) > 0:
                current_price = bars[position.symbol][-1].close
                return (current_price - position.entry_price) * position.shares
            return 0.0
        except:
            return 0.0
    
    def _calculate_setup_quality_retroactive(self, session_data: Dict) -> int:
        """Calculate setup quality based on actual results (1-5 stars)"""
        signals = session_data.get('signals_generated', 0)
        candidates = len(set(session_data.get('candidates_reviewed', [])))
        
        if candidates == 0:
            return 1
        
        signal_rate = (signals / candidates * 100) if candidates > 0 else 0
        
        if signal_rate >= 15:
            return 5
        elif signal_rate >= 10:
            return 4
        elif signal_rate >= 7:
            return 3
        elif signal_rate >= 4:
            return 2
        else:
            return 1
    
    def _get_week_to_date_stats(self, now: dt.datetime) -> Dict:
        """Get week-to-date statistics"""
        try:
            # Get Monday of this week
            monday = now - dt.timedelta(days=now.weekday())
            monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get all positions from this week
            positions = self.position_tracker.get_positions()
            week_positions = [p for p in positions if p.entry_date >= monday]
            
            # Calculate stats
            closed_positions = [p for p in week_positions if p.status == 'closed']
            winners = [p for p in closed_positions if p.realized_pnl and p.realized_pnl > 0]
            losers = [p for p in closed_positions if p.realized_pnl and p.realized_pnl <= 0]
            
            win_rate = (len(winners) / len(closed_positions) * 100) if closed_positions else 0
            total_pnl = sum(p.realized_pnl for p in closed_positions if p.realized_pnl)
            
            # Get starting portfolio value (approximation)
            starting_value = 1000.0  # TODO: Get from config or account
            current_value = starting_value + total_pnl
            weekly_return = (total_pnl / starting_value * 100) if starting_value > 0 else 0
            
            return {
                'trades': len(closed_positions),
                'wins': len(winners),
                'losses': len(losers),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'portfolio_value': current_value,
                'weekly_return': weekly_return,
                'monday_date': monday.strftime('%b %d')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate week-to-date stats: {e}")
            return {
                'trades': 0, 'wins': 0, 'losses': 0,
                'win_rate': 0, 'total_pnl': 0,
                'portfolio_value': 1000, 'weekly_return': 0,
                'monday_date': 'N/A'
            }
    
    def _format_position(self, position) -> Dict:
        """Format position for display"""
        try:
            # Get current price
            bars = self.data_loader.get_bars([position.symbol], timeframe='1Day', limit=1)
            current_price = bars[position.symbol][-1].close if position.symbol in bars and bars[position.symbol] else position.entry_price
            
            unrealized_pnl = (current_price - position.entry_price) * position.shares
            unrealized_pct = (unrealized_pnl / (position.entry_price * position.shares)) * 100
            
            return {
                'symbol': position.symbol,
                'entry_price': position.entry_price,
                'current_price': current_price,
                'shares': position.shares,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pct': unrealized_pct,
                'entry_date': position.entry_date.strftime('%m/%d %H:%M'),
                'hold_days': (dt.datetime.now(self.tz) - position.entry_date).days,
                'exit_strategy': position.exit_strategy or 'D+1'
            }
        except:
            return {
                'symbol': position.symbol,
                'entry_price': position.entry_price,
                'current_price': position.entry_price,
                'shares': position.shares,
                'unrealized_pnl': 0,
                'unrealized_pct': 0,
                'entry_date': 'N/A',
                'hold_days': 0,
                'exit_strategy': 'D+1'
            }
    
    def _format_exit(self, position) -> Dict:
        """Format closed position for display"""
        return {
            'symbol': position.symbol,
            'entry_price': position.entry_price,
            'exit_price': position.exit_price,
            'shares': position.shares,
            'realized_pnl': position.realized_pnl,
            'realized_pct': (position.realized_pnl / (position.entry_price * position.shares)) * 100 if position.entry_price else 0,
            'hold_time': str(position.exit_date - position.entry_date),
            'exit_reason': position.exit_reason or 'Unknown'
        }
    
    def _get_next_session(self, now: dt.datetime) -> Dict:
        """Get info about next trading session"""
        # Simple logic: next weekday
        next_day = now + dt.timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekend
            next_day += dt.timedelta(days=1)
        
        # Check if Monday (weekend gap scanner)
        is_monday = next_day.weekday() == 0
        
        return {
            'date': next_day.strftime('%A, %B %d, %Y'),
            'is_monday': is_monday,
            'special_note': 'Weekend gap scanner will run 9:30-9:45 AM' if is_monday else 'Regular session'
        }
    
    def _save_daily_stats(self, summary: Dict):
        """Save daily stats to JSON for historical tracking"""
        try:
            # Load existing stats
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    all_stats = json.load(f)
            else:
                all_stats = []
            
            # Append today's stats
            daily_record = {
                'date': summary['date'],
                'trades': summary['activity']['entries_executed'],
                'pnl': summary['pnl']['total'],
                'win_rate': summary['week_stats']['win_rate'],
                'setup_quality': summary['market']['setup_quality']
            }
            all_stats.append(daily_record)
            
            # Keep last 90 days
            all_stats = all_stats[-90:]
            
            # Save
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, 'w') as f:
                json.dump(all_stats, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save daily stats: {e}")
    
    def _get_fallback_summary(self, now: dt.datetime) -> Dict:
        """Return fallback summary if data unavailable"""
        return {
            'date': now.strftime('%A, %B %d, %Y'),
            'time': now.strftime('%I:%M %p ET'),
            'market': {'spy_change': 0, 'vix_change': 0, 'setup_quality': 3},
            'activity': {'scans_run': 0, 'candidates_reviewed': 0, 'signals_generated': 0, 
                        'entries_executed': 0, 'positions_overnight': 0},
            'pnl': {'realized': 0, 'unrealized': 0, 'total': 0, 'total_pct': 0, 'deployed_capital': 0},
            'rejections': {},
            'entries': [],
            'exits': [],
            'open_positions': [],
            'week_stats': {'trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 
                          'total_pnl': 0, 'portfolio_value': 1000, 'weekly_return': 0, 'monday_date': 'N/A'},
            'next_session': {'date': 'Unknown', 'is_monday': False, 'special_note': 'Unknown'}
        }
    
    def print_summary(self, summary: Dict, show_details: bool = False):
        """Print formatted daily summary to console"""
        print("\n" + "=" * 70)
        print(f"📊 DAILY SUMMARY - {summary['date']}")
        print("=" * 70)
        
        # Market performance
        market = summary['market']
        spy_emoji = "📈" if market['spy_change'] > 0 else "📉"
        vix_emoji = "↑" if market['vix_change'] > 0 else "↓"
        print("\nMARKET PERFORMANCE:")
        print(f"  • SPY: {market['spy_change']:+.1f}% {spy_emoji}")
        print(f"  • VIX: {market['vix_change']:+.1f} {vix_emoji}")
        
        stars = "⭐" * market['setup_quality'] + "☆" * (5 - market['setup_quality'])
        print(f"  • Gap & Go + Fade/Short setup quality: {stars} ({market['setup_quality']}/5)")
        
        # Trading activity
        activity = summary['activity']
        print("\nTRADING ACTIVITY:")
        print(f"  • Scans run: {activity['scans_run']}")
        print(f"  • Candidates reviewed: {activity['candidates_reviewed']} unique stocks")
        print(f"  • Signals generated: {activity['signals_generated']}")
        print(f"  • Entries executed: {activity['entries_executed']}")
        print(f"  • Positions held overnight: {activity['positions_overnight']} (D+1 exit tomorrow)")
        
        # P&L
        pnl = summary['pnl']
        pnl_emoji = "✅" if pnl['total'] > 0 else "❌" if pnl['total'] < 0 else "➖"
        print("\nTODAY'S P&L:")
        print(f"  • Realized: ${pnl['realized']:.2f} (exits completed)")
        print(f"  • Unrealized: ${pnl['unrealized']:.2f} (open positions)")
        print(f"  • Total: ${pnl['total']:+.2f} ({pnl['total_pct']:+.1f}% of deployed capital) {pnl_emoji}")
        
        # Rejection breakdown
        if summary['rejections']:
            total_rejected = sum(summary['rejections'].values())
            print(f"\nREJECTION BREAKDOWN:")
            print(f"  • Total rejected: {total_rejected} stocks")
            
            # Show top 3 rejection reasons
            sorted_rejections = sorted(summary['rejections'].items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_rejections[:3]:
                pct = (count / total_rejected * 100) if total_rejected > 0 else 0
                print(f"  • {reason}: {count} ({pct:.0f}%)")
            
            print(f"  • Strategy discipline: ✅ Avoided {total_rejected} marginal setups")
        
        # Week-to-date
        wtd = summary['week_stats']
        wtd_emoji = "📈" if wtd['weekly_return'] > 0 else "📉"
        print(f"\nWEEK-TO-DATE (Mon-{summary['date'].split(',')[0]}):")
        print(f"  • Trades: {wtd['trades']} ({wtd['wins']}W, {wtd['losses']}L)")
        if wtd['trades'] > 0:
            print(f"  • Win rate: {wtd['win_rate']:.0f}%")
        print(f"  • Total P&L: ${wtd['total_pnl']:+.2f} ({wtd['weekly_return']:+.1f}% weekly) {wtd_emoji}")
        print(f"  • Portfolio: ${wtd['portfolio_value']:.2f}")
        
        # Expandable details
        if show_details:
            self._print_detailed_sections(summary)
        else:
            print("\n💡 Type 'show details' to see entries, exits, and open positions")
        
        # Next session
        next_session = summary['next_session']
        print(f"\nNEXT SESSION: {next_session['date']}")
        print(f"  • {next_session['special_note']}")
        
        print("=" * 70 + "\n")
    
    def _print_detailed_sections(self, summary: Dict):
        """Print detailed sections (entries, exits, positions)"""
        
        # Entries today
        if summary['entries']:
            print("\n" + "-" * 70)
            print("📥 ENTRIES TODAY:")
            for entry in summary['entries']:
                print(f"\n  {entry['symbol']}:")
                print(f"    • Entry: ${entry['entry_price']:.2f} @ {entry['entry_time']}")
                print(f"    • Shares: {entry['shares']}")
                print(f"    • Reason: {entry.get('entry_reason', 'Gap & Go or Fade/Short setup')}")
                if 'rsi' in entry:
                    print(f"    • RSI: {entry['rsi']:.0f}, Gap: {entry.get('gap_pct', 0):.1f}%")
        
        # Exits today
        if summary['exits']:
            print("\n" + "-" * 70)
            print("📤 EXITS TODAY:")
            for exit in summary['exits']:
                result_emoji = "✅" if exit['realized_pnl'] > 0 else "❌"
                print(f"\n  {exit['symbol']}: {result_emoji}")
                print(f"    • Entry: ${exit['entry_price']:.2f} → Exit: ${exit['exit_price']:.2f}")
                print(f"    • P&L: ${exit['realized_pnl']:+.2f} ({exit['realized_pct']:+.1f}%)")
                print(f"    • Hold time: {exit['hold_time']}")
                print(f"    • Exit reason: {exit['exit_reason']}")
        
        # Open positions
        if summary['open_positions']:
            print("\n" + "-" * 70)
            print("💼 OPEN POSITIONS (Overnight holds):")
            for pos in summary['open_positions']:
                pnl_emoji = "📈" if pos['unrealized_pnl'] > 0 else "📉"
                print(f"\n  {pos['symbol']}: {pnl_emoji}")
                print(f"    • Entry: ${pos['entry_price']:.2f} ({pos['entry_date']})")
                print(f"    • Current: ${pos['current_price']:.2f}")
                print(f"    • P&L: ${pos['unrealized_pnl']:+.2f} ({pos['unrealized_pct']:+.1f}%)")
                print(f"    • Hold: {pos['hold_days']} days | Strategy: {pos['exit_strategy']}")
