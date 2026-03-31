#!/usr/bin/env python3
"""
Test Adaptive Parameter Manager
Quick validation of adaptive parameter calculations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from adaptive.parameter_manager import AdaptiveParameterManager
from bot_v2.config.trading_config import ShortCycleConfig
from data_loader import DataLoader
import pandas as pd


def test_adaptive_parameters():
    """Test adaptive parameter generation"""
    print("=" * 80)
    print("🧪 TESTING ADAPTIVE PARAMETER MANAGER")
    print("=" * 80)
    print()
    
    # Initialize
    config = ShortCycleConfig()
    data_loader = DataLoader()
    adaptive_mgr = AdaptiveParameterManager(config, data_loader)
    
    # Test symbols with different characteristics
    test_symbols = [
        ('MRNA', 'High volatility biotech'),
        ('F', 'Low volatility auto'),
        ('NVDA', 'Tech growth'),
        ('AA', 'Materials')
    ]
    
    print("📊 Testing Adaptive Parameters:\n")
    
    for symbol, description in test_symbols:
        print(f"{'─' * 80}")
        print(f"{symbol} - {description}")
        print(f"{'─' * 80}")
        
        try:
            # Get market data
            market_data = data_loader.get_historical_data(symbol, days=30)
            
            if market_data is None or market_data.empty:
                print(f"❌ No data available for {symbol}\n")
                continue
            
            # Get adaptive parameters
            params = adaptive_mgr.get_adaptive_parameters(symbol, market_data)
            
            # Display parameters
            print(f"✅ Adaptive Parameters Generated:")
            print(f"   Stop Loss:         {params['stop_loss_pct']:.2%} (static: 2.5%)")
            print(f"   Profit Target:     {params['profit_target_pct']:.2%} (static: 3.0%)")
            print(f"   RSI Entry:         {params['rsi_entry']} (static: 30)")
            print(f"   RSI Exit:          {params['rsi_exit']} (static: 70)")
            print(f"   Confidence:        {params['confidence_threshold']:.0%} (static: 60%)")
            print(f"   Exit Time:         {params['exit_time']} (static: 14:30)")
            print()
            
            # Calculate current metrics for context
            atr_pct = adaptive_mgr._calculate_atr_pct(market_data)
            vix_proxy = adaptive_mgr._get_vix_proxy()
            regime = adaptive_mgr._detect_market_regime(market_data)
            
            print(f"📈 Market Context:")
            print(f"   ATR%:              {atr_pct:.2%}")
            print(f"   VIX Proxy:         {vix_proxy:.1f}")
            print(f"   Regime:            {regime}")
            print()
            
        except Exception as e:
            print(f"❌ Error testing {symbol}: {e}\n")
    
    # Test with trade history
    print(f"{'═' * 80}")
    print("📊 Testing Performance Feedback")
    print(f"{'═' * 80}")
    print()
    
    # Simulate some trades
    print("Recording simulated trades...")
    from datetime import datetime, timedelta
    
    # 3 wins, 2 losses (60% win rate)
    base_time = datetime.now() - timedelta(days=5)
    adaptive_mgr.record_trade('TEST1', 100, 103, 10, base_time, base_time + timedelta(hours=2))  # Win
    adaptive_mgr.record_trade('TEST2', 100, 102, 10, base_time, base_time + timedelta(hours=2))  # Win
    adaptive_mgr.record_trade('TEST3', 100, 97, 10, base_time, base_time + timedelta(hours=2))   # Loss
    adaptive_mgr.record_trade('TEST4', 100, 104, 10, base_time, base_time + timedelta(hours=2))  # Win
    adaptive_mgr.record_trade('TEST5', 100, 98, 10, base_time, base_time + timedelta(hours=2))   # Loss
    
    summary = adaptive_mgr.get_performance_summary()
    
    print(f"\n✅ Performance Summary:")
    print(f"   Total Trades:      {summary['total_trades']}")
    print(f"   Win Rate:          {summary['win_rate']:.1%}")
    print(f"   Avg Win:           {summary['avg_win']:.2%}")
    print(f"   Avg Loss:          {summary['avg_loss']:.2%}")
    print(f"   Profit Factor:     {summary['profit_factor']:.2f}")
    print(f"   Consecutive Losses: {summary['consecutive_losses']}")
    print()
    
    # Test confidence adjustment based on performance
    print("Testing confidence adjustment after 2 consecutive losses...")
    adaptive_mgr.record_trade('TEST6', 100, 97, 10, base_time, base_time + timedelta(hours=2))   # Loss
    adaptive_mgr.record_trade('TEST7', 100, 96, 10, base_time, base_time + timedelta(hours=2))   # Loss
    
    # Get updated confidence threshold
    consecutive_losses = adaptive_mgr._get_consecutive_losses()
    win_rate = adaptive_mgr._get_recent_win_rate()
    new_confidence = adaptive_mgr._adaptive_confidence(win_rate, consecutive_losses)
    
    print(f"   Win Rate:          {win_rate:.1%}")
    print(f"   Consecutive Losses: {consecutive_losses}")
    print(f"   New Confidence:    {new_confidence:.0%} (increased selectivity)")
    print()
    
    print("=" * 80)
    print("✅ ADAPTIVE PARAMETER TESTING COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print("  - Adaptive parameters adjust based on volatility, regime, and performance")
    print("  - Stop loss/profit targets scale with ATR (1.5-5% range)")
    print("  - RSI thresholds adapt to market regime (25-40 entry, 60-75 exit)")
    print("  - Confidence threshold adjusts based on win rate (50-75%)")
    print("  - Exit time varies by VIX level (14:00-15:00)")
    print()


if __name__ == "__main__":
    test_adaptive_parameters()
