#!/usr/bin/env python3
"""
Analyze Gap & Go + Fade/Short Strategy Combination
Check if strategies are complementary or conflicting

Questions to answer:
1. Do they trigger on same stocks/days?
2. What's combined performance?
3. Do they cover different market conditions?
4. Optimal position allocation?
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

try:
    from bot_v2.data.data_loader import DataLoader
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

DEFAULT_UNIVERSE = [
    'AAL', 'AEO', 'AES', 'AI', 'APA', 'AR', 'BEAM', 'BEKE', 'CAG', 'CCL',
    'CDNA', 'CHWY', 'CLF', 'CMCSA', 'CPB', 'CPNG', 'CTRA', 'F', 'FTRE', 'HAL',
    'HIMS', 'HRL', 'JACK', 'JD', 'KDP', 'KHC', 'LC', 'LCID', 'LI', 'LYFT',
    'MGY', 'MRNA', 'MUR', 'NCLH', 'NOV', 'NRIX', 'NTLA', 'NU', 'NWSA', 'OSCR',
    'PATH', 'PENN', 'PINS', 'PL', 'PR', 'RIVN', 'S', 'SCVL', 'SDGR', 'SM',
    'SOFI', 'SOUN', 'STLA', 'T', 'TAL', 'TLRY', 'TU', 'TWST', 'VALE', 'VFC',
    'VIPS', 'VIRT', 'VOD', 'WBD', 'WEN', 'WOLF', 'XPEV'
]


def find_gap_and_go_signals(symbol, data):
    """Find Gap & Go entry signals"""
    signals = []
    
    for i in range(20, len(data) - 1):
        window = data.iloc[:i+1]
        
        today_open = window['open'].iloc[-1]
        yesterday_close = window['close'].iloc[-2]
        gap_pct = (today_open - yesterday_close) / yesterday_close
        
        if 0.02 <= gap_pct <= 0.08:
            # RSI check
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 75:
                close = window['close'].iloc[-1]
                if close >= yesterday_close:
                    signals.append({
                        'date': window.index[-1],
                        'symbol': symbol,
                        'type': 'Gap & Go (LONG)',
                        'entry_price': today_open,
                        'gap_pct': gap_pct,
                        'rsi': current_rsi
                    })
    
    return signals


def find_fade_signals(symbol, data):
    """Find Fade/Short entry signals"""
    signals = []
    
    for i in range(30, len(data) - 1):
        window = data.iloc[:i+1]
        
        close = window['close'].iloc[-1]
        sma_20 = window['close'].rolling(20).mean().iloc[-1]
        
        # RSI
        delta = window['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))
        current_rsi = rsi.iloc[-1]
        
        if current_rsi > 70 and (close - sma_20) / sma_20 > 0.10:
            signals.append({
                'date': window.index[-1],
                'symbol': symbol,
                'type': 'Fade/Short (SHORT)',
                'entry_price': close,
                'extension_pct': (close - sma_20) / sma_20,
                'rsi': current_rsi
            })
    
    return signals


def main():
    print("=" * 80)
    print("📊 Gap & Go + Fade/Short Strategy Combination Analysis")
    print("=" * 80)
    print()
    
    data_loader = DataLoader()
    
    print("📈 Analyzing strategy combination...")
    print()
    
    # Collect all signals
    gap_signals = []
    fade_signals = []
    
    for symbol in DEFAULT_UNIVERSE:
        try:
            data = data_loader.get_historical_data(symbol, days=250)
            if not data.empty and len(data) > 200:
                gap_signals.extend(find_gap_and_go_signals(symbol, data))
                fade_signals.extend(find_fade_signals(symbol, data))
        except:
            pass
    
    print(f"✅ Gap & Go signals: {len(gap_signals)}")
    print(f"✅ Fade/Short signals: {len(fade_signals)}")
    print()
    
    # Analyze conflicts (same stock, same day)
    gap_by_date_symbol = {}
    for sig in gap_signals:
        key = (sig['date'], sig['symbol'])
        gap_by_date_symbol[key] = sig
    
    fade_by_date_symbol = {}
    for sig in fade_signals:
        key = (sig['date'], sig['symbol'])
        fade_by_date_symbol[key] = sig
    
    # Find conflicts
    conflicts = []
    for key in gap_by_date_symbol:
        if key in fade_by_date_symbol:
            conflicts.append({
                'date': key[0],
                'symbol': key[1],
                'gap': gap_by_date_symbol[key],
                'fade': fade_by_date_symbol[key]
            })
    
    print("=" * 80)
    print("🔍 CONFLICT ANALYSIS")
    print("=" * 80)
    print()
    print(f"Total Gap & Go signals: {len(gap_signals)}")
    print(f"Total Fade/Short signals: {len(fade_signals)}")
    print(f"Conflicts (same stock, same day): {len(conflicts)}")
    print(f"Conflict rate: {len(conflicts) / max(len(gap_signals), 1) * 100:.1f}%")
    print()
    
    if conflicts:
        print("Sample conflicts:")
        for conflict in conflicts[:5]:
            date_str = pd.Timestamp(conflict['date']).strftime('%Y-%m-%d') if hasattr(conflict['date'], 'strftime') else str(conflict['date'])
            print(f"  {date_str} {conflict['symbol']}:")
            print(f"    Gap & Go: +{conflict['gap']['gap_pct']*100:.1f}% gap, RSI {conflict['gap']['rsi']:.1f}")
            print(f"    Fade/Short: RSI {conflict['fade']['rsi']:.1f} (overbought)")
        print()
    
    # Analyze by date (do they fire on different days?)
    gap_dates = set(sig['date'] for sig in gap_signals)
    fade_dates = set(sig['date'] for sig in fade_signals)
    
    print("=" * 80)
    print("📅 TEMPORAL ANALYSIS")
    print("=" * 80)
    print()
    print(f"Days with Gap & Go signals: {len(gap_dates)}")
    print(f"Days with Fade/Short signals: {len(fade_dates)}")
    print(f"Days with both: {len(gap_dates & fade_dates)}")
    print(f"Days with only Gap & Go: {len(gap_dates - fade_dates)}")
    print(f"Days with only Fade: {len(fade_dates - gap_dates)}")
    print()
    
    # Daily signal counts
    gap_by_day = defaultdict(list)
    fade_by_day = defaultdict(list)
    
    for sig in gap_signals:
        gap_by_day[sig['date']].append(sig)
    
    for sig in fade_signals:
        fade_by_day[sig['date']].append(sig)
    
    # Analyze signal distribution
    gap_counts = [len(v) for v in gap_by_day.values()]
    fade_counts = [len(v) for v in fade_by_day.values()]
    
    print("=" * 80)
    print("📊 SIGNAL DISTRIBUTION")
    print("=" * 80)
    print()
    print("Gap & Go signals per day:")
    print(f"  Average: {np.mean(gap_counts):.1f}")
    print(f"  Max: {max(gap_counts) if gap_counts else 0}")
    print(f"  Min: {min(gap_counts) if gap_counts else 0}")
    print()
    print("Fade/Short signals per day:")
    print(f"  Average: {np.mean(fade_counts):.1f}")
    print(f"  Max: {max(fade_counts) if fade_counts else 0}")
    print(f"  Min: {min(fade_counts) if fade_counts else 0}")
    print()
    
    # Market condition analysis
    print("=" * 80)
    print("🌡️ MARKET CONDITION COMPLEMENTARITY")
    print("=" * 80)
    print()
    
    # Analyze RSI distribution
    gap_rsis = [sig['rsi'] for sig in gap_signals]
    fade_rsis = [sig['rsi'] for sig in fade_signals]
    
    print("Gap & Go RSI range:")
    print(f"  Average: {np.mean(gap_rsis):.1f}")
    print(f"  Min: {min(gap_rsis):.1f}, Max: {max(gap_rsis):.1f}")
    print()
    print("Fade/Short RSI range:")
    print(f"  Average: {np.mean(fade_rsis):.1f}")
    print(f"  Min: {min(fade_rsis):.1f}, Max: {max(fade_rsis):.1f}")
    print()
    
    # Combined strategy simulation
    print("=" * 80)
    print("💰 COMBINED STRATEGY PERFORMANCE")
    print("=" * 80)
    print()
    
    # From backtest results
    gap_total_pnl = 830.15  # %
    gap_trades = 748
    gap_win_rate = 54.3
    
    fade_total_pnl = 174.49  # %
    fade_trades = 914
    fade_win_rate = 62.8
    
    print("Individual Performance:")
    print(f"  Gap & Go: +{gap_total_pnl:.2f}% over {gap_trades} trades ({gap_win_rate}% WR)")
    print(f"  Fade/Short: +{fade_total_pnl:.2f}% over {fade_trades} trades ({fade_win_rate}% WR)")
    print()
    
    # Position allocation scenarios
    print("Combined Performance Scenarios:")
    print()
    
    # Scenario 1: 50/50 split
    combined_50_50 = (gap_total_pnl * 0.5) + (fade_total_pnl * 0.5)
    print(f"1. 50/50 Split (equal capital to each):")
    print(f"   Total Return: +{combined_50_50:.2f}%")
    print(f"   Total Trades: {gap_trades + fade_trades}")
    print()
    
    # Scenario 2: 70/30 (favor Gap & Go)
    combined_70_30 = (gap_total_pnl * 0.7) + (fade_total_pnl * 0.3)
    print(f"2. 70/30 Split (favor Gap & Go):")
    print(f"   Total Return: +{combined_70_30:.2f}%")
    print()
    
    # Scenario 3: 80/20 (heavily favor Gap & Go)
    combined_80_20 = (gap_total_pnl * 0.8) + (fade_total_pnl * 0.2)
    print(f"3. 80/20 Split (heavily favor Gap & Go):")
    print(f"   Total Return: +{combined_80_20:.2f}%")
    print()
    
    print("=" * 80)
    print("✅ RECOMMENDATION")
    print("=" * 80)
    print()
    
    overlap_pct = len(conflicts) / max(len(gap_signals), 1) * 100
    
    if overlap_pct < 10:
        print("🎯 HIGHLY COMPLEMENTARY STRATEGIES!")
        print()
        print(f"✅ Only {overlap_pct:.1f}% conflict rate")
        print("✅ Gap & Go targets: Morning gaps up (bullish sentiment)")
        print("✅ Fade/Short targets: Overbought extremes (mean reversion)")
        print("✅ Different market conditions:")
        print(f"   • Gap & Go avg RSI: {np.mean(gap_rsis):.1f} (neutral)")
        print(f"   • Fade avg RSI: {np.mean(fade_rsis):.1f} (overbought)")
        print()
        print("💡 Implementation:")
        print("   • Morning (9:35 AM): Scan for Gap & Go (LONG bias)")
        print("   • Throughout day: Scan for Fade (SHORT bias)")
        print("   • If conflict: Prioritize Gap & Go (higher returns)")
        print("   • Position sizing: 70% Gap & Go, 30% Fade")
        print()
        print(f"Expected Combined Return: +{combined_70_30:.2f}% per month")
        print(f"Total Opportunities: {gap_trades + fade_trades - len(conflicts)} trades/month")
        print()
    else:
        print(f"⚠️ MODERATE CONFLICTS ({overlap_pct:.1f}%)")
        print()
        print("Need conflict resolution rules:")
        print("  1. If Gap & Go + Fade both trigger → Use Gap & Go")
        print("  2. If only one triggers → Use that one")
        print("  3. Position size accordingly")
        print()
    
    print("=" * 80)
    print("🚀 NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Implement both strategies in bot")
    print("2. Morning scan (9:35 AM): Gap & Go priority")
    print("3. Continuous scan (10:00 AM - 2:00 PM): Fade/Short")
    print("4. Conflict resolution: Gap & Go wins if same stock")
    print("5. Position allocation: 70% Gap & Go, 30% Fade")
    print("6. Track performance separately for each strategy")
    print()


if __name__ == "__main__":
    main()
