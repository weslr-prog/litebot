#!/usr/bin/env python3
"""
Analyze Entry Timing Patterns
Answers: Of winning trades, how many entered on pullback vs immediate strength?
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

def load_positions():
    """Load positions from JSON"""
    positions_file = Path(__file__).parent / "positions.json"
    with open(positions_file, 'r') as f:
        return json.load(f)

def load_pnl_history():
    """Load historical trades from pnl_history"""
    pnl_file = Path(__file__).parent / "bot_v2" / "data" / "pnl_history.json"
    with open(pnl_file, 'r') as f:
        return json.load(f)

def analyze_entry_timing(symbol, entry_date, entry_price):
    """
    Analyze if entry was on pullback or immediate strength.
    
    Pullback = entered below opening range high OR below prior day high
    Immediate strength = entered at new highs
    
    Returns: ('pullback', details) or ('strength', details) or ('unknown', details)
    """
    try:
        # Fetch intraday data for entry day and prior day
        entry_dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
        start_date = entry_dt - timedelta(days=5)
        end_date = entry_dt + timedelta(days=2)
        
        # Get daily data
        ticker = yf.Ticker(symbol)
        daily = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if daily.empty or len(daily) < 2:
            return ('unknown', 'Insufficient data')
        
        # Find entry day in data
        entry_day_data = None
        prior_day_data = None
        
        for i, (idx, row) in enumerate(daily.iterrows()):
            if idx.date() == entry_dt.date():
                entry_day_data = row
                if i > 0:
                    prior_day_data = daily.iloc[i-1]
                break
        
        if entry_day_data is None:
            return ('unknown', 'Entry day not found')
        
        # Calculate metrics
        day_open = entry_day_data['Open']
        day_high = entry_day_data['High']
        day_low = entry_day_data['Low']
        
        prior_high = prior_day_data['High'] if prior_day_data is not None else None
        prior_close = prior_day_data['Close'] if prior_day_data is not None else None
        
        # Calculate opening range (first 30 min approximation using high/low)
        opening_range_high = day_open + (day_high - day_low) * 0.15  # Assume 15% of range is opening
        
        # Determine classification
        details = {
            'entry_price': entry_price,
            'day_open': day_open,
            'day_high': day_high,
            'day_low': day_low,
            'prior_high': prior_high,
            'prior_close': prior_close,
            'opening_range_high_est': opening_range_high
        }
        
        # Pullback indicators
        pullback_signs = 0
        strength_signs = 0
        
        # Check 1: Entry below opening range high
        if entry_price < opening_range_high:
            pullback_signs += 1
            details['below_opening_range'] = True
        else:
            strength_signs += 1
            details['below_opening_range'] = False
        
        # Check 2: Entry below prior day high
        if prior_high and entry_price < prior_high:
            pullback_signs += 1
            details['below_prior_high'] = True
        else:
            strength_signs += 1
            details['below_prior_high'] = False
        
        # Check 3: Entry in lower 50% of daily range
        if entry_price < (day_high + day_low) / 2:
            pullback_signs += 1
            details['lower_half_range'] = True
        else:
            strength_signs += 1
            details['lower_half_range'] = False
        
        # Check 4: Gap analysis
        if prior_close:
            gap_pct = (day_open - prior_close) / prior_close
            if gap_pct > 0.02:  # Gapped up
                if entry_price < day_open + (day_high - day_open) * 0.5:
                    pullback_signs += 1
                    details['gap_pullback'] = True
                else:
                    strength_signs += 1
                    details['gap_continuation'] = True
            details['gap_pct'] = gap_pct
        
        # Classify
        if pullback_signs > strength_signs:
            classification = 'pullback'
        elif strength_signs > pullback_signs:
            classification = 'strength'
        else:
            classification = 'neutral'
        
        details['pullback_signs'] = pullback_signs
        details['strength_signs'] = strength_signs
        
        return (classification, details)
        
    except Exception as e:
        return ('unknown', f'Error: {str(e)}')

def main():
    """Main analysis"""
    print("=" * 80)
    print("ENTRY TIMING ANALYSIS: Pullback vs Strength Entries")
    print("=" * 80)
    print()
    
    positions = load_positions()
    
    # Filter to exited positions with P&L data
    exited_positions = [p for p in positions if p['status'] == 'exited' and p['realized_pnl'] is not None]
    
    # Separate winners and losers
    winners = [p for p in exited_positions if p['realized_pnl'] > 0]
    losers = [p for p in exited_positions if p['realized_pnl'] < 0]
    
    print(f"Total Exited Positions: {len(exited_positions)}")
    print(f"Winners: {len(winners)}")
    print(f"Losers: {len(losers)}")
    print()
    
    # Analyze winners
    print("=" * 80)
    print("WINNER ANALYSIS")
    print("=" * 80)
    print()
    
    winner_classifications = {'pullback': [], 'strength': [], 'neutral': [], 'unknown': []}
    
    for pos in winners:
        symbol = pos['symbol']
        entry_date = pos['entry_date']
        entry_price = pos['entry_price']
        pnl = pos['realized_pnl']
        pnl_pct = (pnl / pos['position_size_dollars']) * 100
        
        classification, details = analyze_entry_timing(symbol, entry_date, entry_price)
        winner_classifications[classification].append({
            'symbol': symbol,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'details': details
        })
        
        print(f"{symbol} ({entry_date}): {classification.upper()}")
        print(f"  Entry: ${entry_price:.2f}, P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        if isinstance(details, dict):
            print(f"  Pullback signs: {details.get('pullback_signs', 'N/A')}, Strength signs: {details.get('strength_signs', 'N/A')}")
            if 'day_open' in details:
                print(f"  Day open: ${details['day_open']:.2f}, Day high: ${details['day_high']:.2f}")
        print()
    
    # Analyze losers
    print("=" * 80)
    print("LOSER ANALYSIS")
    print("=" * 80)
    print()
    
    loser_classifications = {'pullback': [], 'strength': [], 'neutral': [], 'unknown': []}
    
    for pos in losers:
        symbol = pos['symbol']
        entry_date = pos['entry_date']
        entry_price = pos['entry_price']
        pnl = pos['realized_pnl']
        pnl_pct = (pnl / pos['position_size_dollars']) * 100
        
        classification, details = analyze_entry_timing(symbol, entry_date, entry_price)
        loser_classifications[classification].append({
            'symbol': symbol,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'details': details
        })
        
        print(f"{symbol} ({entry_date}): {classification.upper()}")
        print(f"  Entry: ${entry_price:.2f}, P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        if isinstance(details, dict):
            print(f"  Pullback signs: {details.get('pullback_signs', 'N/A')}, Strength signs: {details.get('strength_signs', 'N/A')}")
            if 'day_open' in details:
                print(f"  Day open: ${details['day_open']:.2f}, Day high: ${details['day_high']:.2f}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print("WINNERS:")
    for classification in ['pullback', 'strength', 'neutral', 'unknown']:
        count = len(winner_classifications[classification])
        pct = (count / len(winners) * 100) if winners else 0
        print(f"  {classification.capitalize()}: {count} ({pct:.1f}%)")
    
    print()
    print("LOSERS:")
    for classification in ['pullback', 'strength', 'neutral', 'unknown']:
        count = len(loser_classifications[classification])
        pct = (count / len(losers) * 100) if losers else 0
        print(f"  {classification.capitalize()}: {count} ({pct:.1f}%)")
    
    print()
    print("=" * 80)
    print("INSIGHT")
    print("=" * 80)
    
    winner_pullback_pct = (len(winner_classifications['pullback']) / len(winners) * 100) if winners else 0
    winner_strength_pct = (len(winner_classifications['strength']) / len(winners) * 100) if winners else 0
    
    loser_pullback_pct = (len(loser_classifications['pullback']) / len(losers) * 100) if losers else 0
    loser_strength_pct = (len(loser_classifications['strength']) / len(losers) * 100) if losers else 0
    
    print(f"Winners on pullback: {winner_pullback_pct:.1f}%")
    print(f"Winners on strength: {winner_strength_pct:.1f}%")
    print(f"Losers on pullback: {loser_pullback_pct:.1f}%")
    print(f"Losers on strength: {loser_strength_pct:.1f}%")
    print()
    
    if winner_pullback_pct > winner_strength_pct:
        print("✅ EDGE IDENTIFIED: Winners favor pullback entries")
        print(f"   Pullback entries win {winner_pullback_pct - loser_pullback_pct:+.1f}pp more than expected")
    elif winner_strength_pct > winner_pullback_pct:
        print("✅ EDGE IDENTIFIED: Winners favor strength entries")
        print(f"   Strength entries win {winner_strength_pct - loser_strength_pct:+.1f}pp more than expected")
    else:
        print("⚠️  NO CLEAR EDGE: Entry timing shows no pattern")
    
if __name__ == "__main__":
    main()
