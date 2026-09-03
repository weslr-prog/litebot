"""
Automated Symbol Blacklist Manager
Tracks underperforming symbols and automatically blacklists chronic losers
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Set
from pathlib import Path


class SymbolBlacklistManager:
    """Manages automatic blacklisting of chronic losing symbols"""
    
    def __init__(self, blacklist_file='bot_v2/config/symbol_blacklist.json'):
        self.blacklist_file = blacklist_file
        self.blacklist = self._load_blacklist()
        
    def _load_blacklist(self) -> Dict:
        """Load existing blacklist"""
        if os.path.exists(self.blacklist_file):
            with open(self.blacklist_file, 'r') as f:
                return json.load(f)
        return {
            'permanent': [],
            'temporary': {},
            'last_updated': None,
            'performance': {}
        }
    
    def _save_blacklist(self):
        """Save blacklist to file"""
        os.makedirs(os.path.dirname(self.blacklist_file), exist_ok=True)
        self.blacklist['last_updated'] = datetime.now().isoformat()
        with open(self.blacklist_file, 'w') as f:
            json.dump(self.blacklist, f, indent=2)
    
    def analyze_from_alpaca(self, lookback_days=21):
        """Analyze recent Alpaca trades and update blacklist"""
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        
        # Connect to Alpaca
        api_key = os.getenv('APCA_API_KEY_ID')
        api_secret = os.getenv('APCA_API_SECRET_KEY')
        
        if not api_key or not api_secret:
            print("❌ Alpaca credentials not found")
            return
        
        client = TradingClient(api_key, api_secret, paper=True)
        
        # Get recent orders
        req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=500)
        orders = client.get_orders(filter=req)
        
        # Filter to lookback period
        cutoff = datetime.now() - timedelta(days=lookback_days)
        recent_orders = [o for o in orders if o.filled_at and o.filled_at.replace(tzinfo=None) >= cutoff]
        
        # Group trades by symbol
        trade_pairs = defaultdict(list)
        for order in sorted(recent_orders, key=lambda x: x.filled_at):
            trade_pairs[order.symbol].append({
                'side': order.side.value,
                'qty': float(order.filled_qty),
                'price': float(order.filled_avg_price),
                'filled_at': order.filled_at
            })
        
        # Calculate performance per symbol
        symbol_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0, 'trades': 0})
        
        for symbol, trades in trade_pairs.items():
            buys = [t for t in trades if t['side'] == 'buy']
            sells = [t for t in trades if t['side'] == 'sell']
            
            for buy in buys:
                matching_sells = [s for s in sells if s['filled_at'] > buy['filled_at']]
                if matching_sells:
                    sell = matching_sells[0]
                    pnl = (sell['price'] - buy['price']) * min(buy['qty'], sell['qty'])
                    
                    symbol_stats[symbol]['trades'] += 1
                    symbol_stats[symbol]['pnl'] += pnl
                    
                    if pnl > 0:
                        symbol_stats[symbol]['wins'] += 1
                    elif pnl < 0:
                        symbol_stats[symbol]['losses'] += 1
        
        # Update performance tracking
        self.blacklist['performance'] = {}
        for symbol, stats in symbol_stats.items():
            win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
            self.blacklist['performance'][symbol] = {
                'trades': stats['trades'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': win_rate,
                'pnl': stats['pnl'],
                'last_analyzed': datetime.now().isoformat()
            }
        
        # Apply blacklist rules
        self._apply_blacklist_rules(symbol_stats)
        self._save_blacklist()
        
        return symbol_stats
    
    def _apply_blacklist_rules(self, symbol_stats: Dict):
        """Apply automatic blacklisting rules"""
        
        # Rule 1: PERMANENT blacklist - 0% win rate with 3+ trades
        for symbol, stats in symbol_stats.items():
            if stats['trades'] >= 3 and stats['wins'] == 0:
                if symbol not in self.blacklist['permanent']:
                    self.blacklist['permanent'].append(symbol)
                    print(f"🚫 PERMANENT BLACKLIST: {symbol} (0% WR, {stats['trades']} trades, ${stats['pnl']:.2f})")
        
        # Rule 2: PERMANENT blacklist - 5+ trades with < 25% win rate and negative P&L
        for symbol, stats in symbol_stats.items():
            win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
            if stats['trades'] >= 5 and win_rate < 0.25 and stats['pnl'] < 0:
                if symbol not in self.blacklist['permanent']:
                    self.blacklist['permanent'].append(symbol)
                    print(f"🚫 PERMANENT BLACKLIST: {symbol} ({win_rate*100:.0f}% WR, ${stats['pnl']:.2f})")
        
        # Rule 3: TEMPORARY blacklist (30 days) - 3 consecutive losses
        for symbol, stats in symbol_stats.items():
            # Check if last 3 trades were all losses
            # This requires more detailed trade tracking, so we'll use simpler criteria
            if stats['trades'] >= 3 and stats['losses'] >= 3 and stats['wins'] == 0:
                if symbol not in self.blacklist['permanent']:
                    expiry = (datetime.now() + timedelta(days=30)).isoformat()
                    self.blacklist['temporary'][symbol] = {
                        'added': datetime.now().isoformat(),
                        'expires': expiry,
                        'reason': f"{stats['losses']} consecutive losses"
                    }
                    print(f"⏸️  TEMPORARY BLACKLIST (30d): {symbol} ({stats['losses']} losses)")
        
        # Clean up expired temporary blacklists
        now = datetime.now()
        expired = []
        for symbol, info in self.blacklist['temporary'].items():
            if datetime.fromisoformat(info['expires']) < now:
                expired.append(symbol)
        
        for symbol in expired:
            del self.blacklist['temporary'][symbol]
            print(f"✅ REMOVED from temporary blacklist: {symbol}")
    
    def get_blacklisted_symbols(self) -> Set[str]:
        """Get all currently blacklisted symbols"""
        blacklisted = set(self.blacklist['permanent'])
        
        # Add temporary blacklist that hasn't expired
        now = datetime.now()
        for symbol, info in self.blacklist['temporary'].items():
            if datetime.fromisoformat(info['expires']) > now:
                blacklisted.add(symbol)
        
        return blacklisted
    
    def is_blacklisted(self, symbol: str) -> bool:
        """Check if a symbol is blacklisted"""
        return symbol in self.get_blacklisted_symbols()
    
    def get_report(self) -> str:
        """Generate blacklist report"""
        report = ["=" * 60]
        report.append("SYMBOL BLACKLIST REPORT")
        report.append("=" * 60)
        
        # Permanent blacklist
        report.append(f"\n🚫 PERMANENT BLACKLIST ({len(self.blacklist['permanent'])} symbols):")
        for symbol in sorted(self.blacklist['permanent']):
            perf = self.blacklist['performance'].get(symbol, {})
            trades = perf.get('trades', 0)
            wr = perf.get('win_rate', 0) * 100
            pnl = perf.get('pnl', 0)
            report.append(f"   {symbol}: {trades} trades, {wr:.0f}% WR, ${pnl:.2f} P&L")
        
        # Temporary blacklist
        active_temp = {s: i for s, i in self.blacklist['temporary'].items() 
                       if datetime.fromisoformat(i['expires']) > datetime.now()}
        
        report.append(f"\n⏸️  TEMPORARY BLACKLIST ({len(active_temp)} symbols):")
        for symbol, info in sorted(active_temp.items()):
            expires = datetime.fromisoformat(info['expires']).strftime('%Y-%m-%d')
            reason = info['reason']
            report.append(f"   {symbol}: {reason} (expires {expires})")
        
        # Performance summary
        report.append(f"\n📊 PERFORMANCE TRACKING ({len(self.blacklist['performance'])} symbols):")
        
        # Sort by P&L
        sorted_perf = sorted(self.blacklist['performance'].items(), 
                           key=lambda x: x[1]['pnl'], reverse=True)
        
        report.append("\n   Top 5 Performers:")
        for symbol, perf in sorted_perf[:5]:
            blacklisted = " [BLACKLISTED]" if self.is_blacklisted(symbol) else ""
            report.append(f"     {symbol}: ${perf['pnl']:+.2f} ({perf['trades']} trades, {perf['win_rate']*100:.0f}% WR){blacklisted}")
        
        report.append("\n   Bottom 5 Performers:")
        for symbol, perf in sorted_perf[-5:]:
            blacklisted = " [BLACKLISTED]" if self.is_blacklisted(symbol) else ""
            report.append(f"     {symbol}: ${perf['pnl']:+.2f} ({perf['trades']} trades, {perf['win_rate']*100:.0f}% WR){blacklisted}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def manual_add(self, symbol: str, permanent=True, days=30, reason="Manual"):
        """Manually add symbol to blacklist"""
        if permanent:
            if symbol not in self.blacklist['permanent']:
                self.blacklist['permanent'].append(symbol)
                print(f"🚫 Added {symbol} to PERMANENT blacklist")
        else:
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            self.blacklist['temporary'][symbol] = {
                'added': datetime.now().isoformat(),
                'expires': expiry,
                'reason': reason
            }
            print(f"⏸️  Added {symbol} to TEMPORARY blacklist ({days} days)")
        
        self._save_blacklist()
    
    def manual_remove(self, symbol: str):
        """Manually remove symbol from blacklist"""
        removed = False
        
        if symbol in self.blacklist['permanent']:
            self.blacklist['permanent'].remove(symbol)
            removed = True
        
        if symbol in self.blacklist['temporary']:
            del self.blacklist['temporary'][symbol]
            removed = True
        
        if removed:
            self._save_blacklist()
            print(f"✅ Removed {symbol} from blacklist")
        else:
            print(f"⚠️  {symbol} not found in blacklist")


def main():
    """Run blacklist analysis and generate report"""
    import sys
    
    # Load credentials
    from dotenv import load_dotenv
    load_dotenv()
    
    manager = SymbolBlacklistManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'analyze':
            print("Analyzing recent trading performance...")
            manager.analyze_from_alpaca(lookback_days=21)
            print("\n" + manager.get_report())
        
        elif command == 'report':
            print(manager.get_report())
        
        elif command == 'add' and len(sys.argv) >= 3:
            symbol = sys.argv[2].upper()
            permanent = '--temp' not in sys.argv
            manager.manual_add(symbol, permanent=permanent)
        
        elif command == 'remove' and len(sys.argv) >= 3:
            symbol = sys.argv[2].upper()
            manager.manual_remove(symbol)
        
        else:
            print("Usage:")
            print("  python symbol_blacklist_manager.py analyze   # Analyze and update blacklist")
            print("  python symbol_blacklist_manager.py report    # Show current blacklist")
            print("  python symbol_blacklist_manager.py add <SYM> # Add to blacklist")
            print("  python symbol_blacklist_manager.py add <SYM> --temp # Add temporary")
            print("  python symbol_blacklist_manager.py remove <SYM> # Remove from blacklist")
    else:
        # Default: analyze and report
        print("Analyzing recent trading performance...")
        manager.analyze_from_alpaca(lookback_days=21)
        print("\n" + manager.get_report())


if __name__ == '__main__':
    main()
