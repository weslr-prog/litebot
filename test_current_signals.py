#!/usr/bin/env python3
"""
Test which stocks on the current watchlist would pass confidence threshold
This simulates what will happen tomorrow morning at 9:45 AM
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import yfinance as yf
from datetime import datetime
import json

def test_watchlist_signals():
    """Test if current watchlist stocks would generate tradeable signals"""
    
    print("\n" + "="*70)
    print("  🔍 TESTING CURRENT WATCHLIST FOR TRADEABLE SIGNALS")
    print("="*70)
    
    # Load components
    try:
        from small_portfolio_config import SmallPortfolioConfig
        from traders.short_cycle_trader import AISignalGenerator
        
        config = SmallPortfolioConfig()
        signal_gen = AISignalGenerator(config)
        
        print(f"\n✅ Bot components loaded")
        print(f"   Confidence threshold: {config.confidence_threshold:.1%}")
        print(f"   Late entry threshold: {config.confidence_threshold * 1.3:.1%}")
        print(f"   Quality scorer active: {signal_gen.quality_scorer is not None}")
        
    except Exception as e:
        print(f"❌ Failed to load bot components: {e}")
        return
    
    # Load watchlist
    try:
        with open('logs/current_watchlist.json', 'r') as f:
            watchlist_data = json.load(f)
            symbols = watchlist_data.get('symbols', [])
        print(f"\n✅ Loaded watchlist: {len(symbols)} symbols")
        print(f"   {', '.join(symbols)}")
    except Exception as e:
        print(f"❌ Failed to load watchlist: {e}")
        return
    
    print(f"\n📊 Fetching 5-day intraday data for analysis...")
    print(f"   (This simulates what bot sees at 9:45 AM)")
    
    # Fetch market data
    market_data = {}
    failed = []
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='5d', interval='5m')
            
            if not data.empty:
                # Normalize column names
                data.columns = [col.lower() for col in data.columns]
                market_data[symbol] = data
                print(f"   ✅ {symbol}: {len(data)} bars")
            else:
                failed.append(symbol)
                print(f"   ⚠️  {symbol}: No data")
        except Exception as e:
            failed.append(symbol)
            print(f"   ❌ {symbol}: {str(e)[:50]}")
    
    if not market_data:
        print("\n❌ No market data available (market closed)")
        return
    
    print(f"\n🎯 Generating signals with quality scoring...")
    print(f"   {'='*66}")
    
    # Generate signals
    signals = signal_gen.generate_signals(
        universe=list(market_data.keys()),
        market_data=market_data,
        active_positions=[]
    )
    
    # Analyze results
    print(f"\n{'='*70}")
    print(f"  📊 RESULTS")
    print(f"{'='*70}")
    
    # Morning entry threshold
    morning_threshold = config.confidence_threshold
    # Late entry threshold (30% higher)
    late_threshold = config.confidence_threshold * 1.3
    
    print(f"\n✅ Signals that meet MORNING entry threshold ({morning_threshold:.1%}):")
    morning_signals = [s for s in signals if s.confidence >= morning_threshold]
    
    if morning_signals:
        for i, signal in enumerate(morning_signals, 1):
            features = signal.features_used or {}
            base_conf = features.get('base_confidence', signal.confidence)
            quality_enhanced = features.get('quality_enhanced', False)
            
            print(f"\n   {i}. {signal.symbol}")
            print(f"      Final Confidence: {signal.confidence:.3f} ({signal.confidence:.1%})")
            print(f"      Base Confidence:  {base_conf:.3f}")
            
            if quality_enhanced:
                boost = signal.confidence / base_conf if base_conf > 0 else 1
                print(f"      Quality Boost:    {boost:.2f}x ⭐")
            else:
                print(f"      Quality Boost:    None")
            
            print(f"      Momentum:         {features.get('momentum_score', 0):.5f}")
            print(f"      Volume Surge:     {features.get('volume_surge', 0):.2f}x")
            print(f"      Entry Price:      ${signal.entry_price:.2f}")
    else:
        print(f"   ❌ None - All signals below {morning_threshold:.1%} threshold")
    
    print(f"\n✅ Signals that meet LATE entry threshold ({late_threshold:.1%}):")
    late_signals = [s for s in signals if s.confidence >= late_threshold]
    
    if late_signals:
        for i, signal in enumerate(late_signals, 1):
            print(f"   {i}. {signal.symbol} - {signal.confidence:.1%}")
    else:
        print(f"   ❌ None - All signals below {late_threshold:.1%} threshold")
    
    # Show top 5 by confidence even if below threshold
    print(f"\n📊 Top 5 by confidence (even if below threshold):")
    top_5 = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5] if signals else []
    
    if top_5:
        for i, signal in enumerate(top_5, 1):
            features = signal.features_used or {}
            base_conf = features.get('base_confidence', signal.confidence)
            quality_enhanced = features.get('quality_enhanced', False)
            
            status = "✅" if signal.confidence >= morning_threshold else "❌"
            boost_marker = "⭐" if quality_enhanced else ""
            
            print(f"   {status} {i}. {signal.symbol}: {signal.confidence:.3f} ({signal.confidence:.1%}) {boost_marker}")
            print(f"         Base: {base_conf:.3f}, Momentum: {features.get('momentum_score', 0):.5f}")
    else:
        print(f"   ❌ No signals generated at all")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"  📈 SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n   Symbols analyzed:        {len(market_data)}")
    print(f"   Signals generated:       {len(signals)}")
    print(f"   Morning entry ready:     {len(morning_signals)}")
    print(f"   Late entry ready:        {len(late_signals)}")
    print(f"   Failed to fetch data:    {len(failed)}")
    
    if len(morning_signals) > 0:
        print(f"\n   ✅ GOOD NEWS: {len(morning_signals)} stock(s) would trade tomorrow morning!")
        print(f"\n   💡 Bot will attempt to enter these at 9:45-10:00 AM")
    elif len(signals) > 0:
        print(f"\n   ⚠️  WEAK SIGNALS: {len(signals)} signals found but all below threshold")
        print(f"\n   💡 Reasons:")
        print(f"      • Low momentum (sideways market)")
        print(f"      • Weak volume (not enough conviction)")
        print(f"      • Quality scoring couldn't boost confidence enough")
        print(f"\n   💡 Bot will keep scanning every 5 min for better setups")
    else:
        print(f"\n   ❌ NO SIGNALS: Current market conditions too weak")
        print(f"\n   💡 This is NORMAL and GOOD - bot is protecting capital")
        print(f"      Bot will scan again tomorrow for better opportunities")
    
    # Check if quality scoring actually helped
    if signals:
        quality_boosted = [s for s in signals if s.features_used.get('quality_enhanced', False)]
        if quality_boosted:
            print(f"\n   ⭐ Quality scoring boosted {len(quality_boosted)} signal(s)")
        else:
            print(f"\n   ℹ️  No signals received quality boost")
            print(f"      (Either too few bars or multi-timeframe not aligned)")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    test_watchlist_signals()
