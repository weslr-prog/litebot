#!/usr/bin/env python3
"""
Analyze recent trading performance from Alpaca
"""
import os
os.environ['APCA_API_KEY_ID'] = 'PKH5EOWZNTP7Z2AQEDQSKZVOQJ'
os.environ['APCA_API_SECRET_KEY'] = '8jrnoVaufgaLdq9Y8UT3bQZb7TNwRY15Uk9v11cnYMmB'

from alpaca.trading.client import TradingClient
from datetime import datetime, timedelta
from collections import defaultdict

client = TradingClient(os.environ['APCA_API_KEY_ID'], os.environ['APCA_API_SECRET_KEY'], paper=True)

# Get account info
account = client.get_account()
print(f"=== ALPACA PAPER TRADING ACCOUNT ===")
print(f"Portfolio Value: ${float(account.portfolio_value):.2f}")
print(f"Equity: ${float(account.equity):.2f}")
print(f"Cash: ${float(account.cash):.2f}")

# Get positions
positions = client.get_all_positions()
print(f"\n📊 ACTIVE POSITIONS ({len(positions)}):")
total_unrealized = 0
for pos in positions:
    unrealized_pl = float(pos.unrealized_pl)
    unrealized_plpc = float(pos.unrealized_plpc) * 100
    total_unrealized += unrealized_pl
    print(f"  {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
    print(f"    Current: ${float(pos.current_price):.2f} | Unrealized: ${unrealized_pl:+.2f} ({unrealized_plpc:+.1f}%)")

print(f"\n  Total Unrealized P&L: ${total_unrealized:+.2f}")

# Get recent orders
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=500)
orders = client.get_orders(filter=req)

# Filter to last 3 weeks
cutoff = datetime.now() - timedelta(days=21)
recent_orders = [o for o in orders if o.filled_at and o.filled_at.replace(tzinfo=None) >= cutoff]

print(f"\n📋 LAST 3 WEEKS: {len(recent_orders)} filled orders")

# Group trades
trade_pairs = defaultdict(list)
for order in sorted(recent_orders, key=lambda x: x.filled_at):
    trade_pairs[order.symbol].append({
        'side': order.side.value,
        'qty': float(order.filled_qty),
        'price': float(order.filled_avg_price),
        'filled_at': order.filled_at
    })

# Calculate completed trades
completed_trades = []
for symbol, trades in trade_pairs.items():
    buys = [t for t in trades if t['side'] == 'buy']
    sells = [t for t in trades if t['side'] == 'sell']
    
    for buy in buys:
        matching_sells = [s for s in sells if s['filled_at'] > buy['filled_at']]
        if matching_sells:
            sell = matching_sells[0]
            qty = min(buy['qty'], sell['qty'])
            pnl = (sell['price'] - buy['price']) * qty
            pct = ((sell['price'] - buy['price']) / buy['price']) * 100
            hold_time = (sell['filled_at'] - buy['filled_at']).total_seconds() / 3600
            
            completed_trades.append({
                'symbol': symbol,
                'entry_time': buy['filled_at'],
                'exit_time': sell['filled_at'],
                'entry_price': buy['price'],
                'exit_price': sell['price'],
                'qty': qty,
                'pnl': pnl,
                'pct': pct,
                'hold_hours': hold_time
            })

if completed_trades:
    wins = [t for t in completed_trades if t['pnl'] > 0]
    losses = [t for t in completed_trades if t['pnl'] < 0]
    breakeven = [t for t in completed_trades if t['pnl'] == 0]
    total_pnl = sum(t['pnl'] for t in completed_trades)
    
    print(f"\n💰 COMPLETED TRADES ({len(completed_trades)}):")
    print(f"  Total Realized P&L: ${total_pnl:.2f}")
    print(f"  Win Rate: {len(wins)}/{len(completed_trades)} = {len(wins)/len(completed_trades)*100:.1f}%")
    print(f"  ({len(wins)}W / {len(losses)}L / {len(breakeven)}BE)")
    
    if wins:
        avg_win = sum(w['pnl'] for w in wins)/len(wins)
        avg_win_pct = sum(w['pct'] for w in wins)/len(wins)
        print(f"  Avg Win: ${avg_win:.2f} ({avg_win_pct:.2f}%)")
    
    if losses:
        avg_loss = sum(l['pnl'] for l in losses)/len(losses)
        avg_loss_pct = sum(l['pct'] for l in losses)/len(losses)
        print(f"  Avg Loss: ${avg_loss:.2f} ({avg_loss_pct:.2f}%)")
    
    if wins and losses:
        profit_factor = abs(sum(w['pnl'] for w in wins) / sum(l['pnl'] for l in losses))
        print(f"  Profit Factor: {profit_factor:.2f}x")
    
    avg_hold = sum(t['hold_hours'] for t in completed_trades)/len(completed_trades)
    print(f"  Avg Hold Time: {avg_hold:.1f} hours ({avg_hold/24:.1f} days)")
    
    # Winners vs losers hold time
    if wins:
        avg_win_hold = sum(w['hold_hours'] for w in wins)/len(wins)
        print(f"  Avg Winner Hold: {avg_win_hold:.1f} hours")
    if losses:
        avg_loss_hold = sum(l['hold_hours'] for l in losses)/len(losses)
        print(f"  Avg Loser Hold: {avg_loss_hold:.1f} hours")
    
    print(f"\n📊 ALL COMPLETED TRADES (sorted by date):")
    for t in sorted(completed_trades, key=lambda x: x['exit_time'], reverse=True):
        emoji = "✅" if t['pnl'] > 0 else "❌" if t['pnl'] < 0 else "➖"
        date = t['exit_time'].strftime('%m/%d %H:%M')
        print(f"  {emoji} {t['symbol']:6} ({date}): ${t['pnl']:+6.2f} ({t['pct']:+5.1f}%) | {t['hold_hours']:5.1f}h | ${t['entry_price']:.2f}→${t['exit_price']:.2f}")
    
    # Symbol analysis
    print(f"\n📈 PERFORMANCE BY SYMBOL:")
    symbol_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0})
    for t in completed_trades:
        symbol_stats[t['symbol']]['trades'] += 1
        symbol_stats[t['symbol']]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            symbol_stats[t['symbol']]['wins'] += 1
    
    for symbol in sorted(symbol_stats.keys(), key=lambda s: symbol_stats[s]['pnl'], reverse=True):
        stats = symbol_stats[symbol]
        wr = stats['wins']/stats['trades']*100 if stats['trades'] > 0 else 0
        emoji = "🔥" if stats['pnl'] > 0 else "❄️"
        print(f"  {emoji} {symbol:6}: ${stats['pnl']:+6.2f} | {stats['trades']} trades | {wr:.0f}% WR")
    
    print(f"\n🔍 TRADE FREQUENCY:")
    days_trading = 21
    trades_per_day = len(completed_trades) / days_trading
    print(f"  {trades_per_day:.2f} completed trades per day avg")
    print(f"  {len(completed_trades)} total trades in 21 days")
else:
    print("\n⚠️ No completed trades found in last 3 weeks")
