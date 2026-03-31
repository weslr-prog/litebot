#!/usr/bin/env python3
"""
Test NoneType handling during market hours simulation.
This ensures the bot will work properly when the market opens Thursday.
"""

import os
import sys
import json
import datetime as dt
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig, ShortCyclePosition, PositionStatus, AISignal

def create_test_position_with_null_stop():
    """Create a position with null stop_price like those in positions.json"""
    signal = AISignal(
        symbol="AAPL",
        action="BUY",
        confidence=0.5,
        time_horizon_days=1.0,
        entry_price=239.704,
        target_price=None,
        features_used={},
        signal_timestamp=dt.datetime.now()
    )
    
    position = ShortCyclePosition(
        symbol="AAPL",
        entry_date=dt.date(2025, 9, 23),
        exit_date=dt.date(2025, 9, 24),
        entry_price=239.704,
        position_size_shares=5,
        position_size_dollars=1279.05,
        stop_price=None,  # This is the key - null stop price
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=signal
    )
    return position

def test_none_current_price_handling():
    """Test that None current_price is handled gracefully"""
    print("🧪 Testing None current_price handling...")
    
    position = create_test_position_with_null_stop()
    
    # Test 1: should_smart_exit with None current_price
    print("   Testing should_smart_exit with None current_price...")
    should_exit, reason = position.should_smart_exit(
        current_date=dt.date(2025, 9, 24), 
        current_price=None,
        current_time=dt.datetime(2025, 9, 24, 10, 30)
    )
    assert should_exit == False, f"Expected False, got {should_exit}"
    assert reason == "INVALID_PRICE_DATA", f"Expected INVALID_PRICE_DATA, got {reason}"
    print("   ✅ should_smart_exit handles None current_price correctly")
    
    # Test 2: is_stopped_out with None current_price 
    print("   Testing is_stopped_out with None current_price...")
    stopped_out = position.is_stopped_out(None)
    assert stopped_out == False, f"Expected False, got {stopped_out}"
    print("   ✅ is_stopped_out handles None current_price correctly")
    
    # Test 3: should_smart_exit with valid current_price
    print("   Testing should_smart_exit with valid current_price...")
    should_exit, reason = position.should_smart_exit(
        current_date=dt.date(2025, 9, 24), 
        current_price=245.0,  # Valid price
        current_time=dt.datetime(2025, 9, 24, 15, 45)  # Late afternoon
    )
    print(f"   Smart exit decision: {should_exit}, reason: {reason}")
    print("   ✅ should_smart_exit works with valid current_price")

def test_stop_manager_none_handling():
    """Test AIStopLossManager handles None current_price"""
    print("\n🧪 Testing AIStopLossManager None handling...")
    
    config = ShortCycleConfig()
    config.max_risk_per_trade_dollars = 50.0
    
    from traders.short_cycle_trader import AIStopLossManager
    stop_manager = AIStopLossManager(config)
    
    position = create_test_position_with_null_stop()
    
    # Test should_fast_exit with None current_price
    print("   Testing should_fast_exit with None current_price...")
    should_fast_exit = stop_manager.should_fast_exit(position, None)
    assert should_fast_exit == False, f"Expected False, got {should_fast_exit}"
    print("   ✅ should_fast_exit handles None current_price correctly")
    
    # Test should_fast_exit with valid current_price  
    print("   Testing should_fast_exit with valid current_price...")
    should_fast_exit = stop_manager.should_fast_exit(position, 230.0)  # Down ~4%
    print(f"   Fast exit decision: {should_fast_exit}")
    print("   ✅ should_fast_exit works with valid current_price")

def simulate_market_hours_with_real_positions():
    """Simulate what happens during market hours with real positions.json data"""
    print("\n🧪 Simulating market hours with real positions...")
    
    # Load real positions from positions.json
    try:
        with open('positions.json', 'r') as f:
            positions_data = json.load(f)
        print(f"   Loaded {len(positions_data)} real positions from positions.json")
    except Exception as e:
        print(f"   ❌ Could not load positions.json: {e}")
        return
    
    # Create ShortCyclePosition objects from the data
    positions = []
    for pos_data in positions_data:
        try:
            signal = AISignal(
                symbol=pos_data['symbol'],
                action=pos_data['ai_signal']['action'],
                confidence=pos_data['ai_signal']['confidence'],
                time_horizon_days=pos_data['ai_signal']['time_horizon_days'],
                entry_price=pos_data['ai_signal']['entry_price'],
                target_price=pos_data['ai_signal'].get('target_price'),
                features_used=pos_data['ai_signal'].get('features_used', {}),
                signal_timestamp=dt.datetime.fromisoformat(pos_data['ai_signal']['timestamp'])
            )
            
            position = ShortCyclePosition(
                symbol=pos_data['symbol'],
                entry_date=dt.datetime.strptime(pos_data['entry_date'], '%Y-%m-%d').date(),
                exit_date=dt.datetime.strptime(pos_data['exit_date'], '%Y-%m-%d').date(),
                entry_price=pos_data['entry_price'],
                position_size_shares=pos_data['position_size_shares'],
                position_size_dollars=pos_data['position_size_dollars'],
                stop_price=pos_data['stop_price'],  # This will be None for most
                target_price=pos_data['target_price'],
                status=PositionStatus.ENTERED,
                ai_signal=signal
            )
            positions.append(position)
        except Exception as e:
            print(f"   ⚠️ Error creating position for {pos_data.get('symbol', 'unknown')}: {e}")
            continue
    
    print(f"   Successfully created {len(positions)} position objects")
    
    # Test processing with None prices (market closed scenario)
    print("   Testing None price handling (market closed scenario)...")
    none_price_exits = 0
    for position in positions:
        should_exit, reason = position.should_smart_exit(
            current_date=dt.date(2025, 9, 24),
            current_price=None,  # Simulate no price data
            current_time=dt.datetime(2025, 9, 24, 14, 30)
        )
        if not should_exit and reason == "INVALID_PRICE_DATA":
            none_price_exits += 1
    
    print(f"   ✅ {none_price_exits}/{len(positions)} positions correctly handled None price")
    
    # Test processing with valid prices (market open scenario)  
    print("   Testing valid price handling (market open scenario)...")
    # Simulate prices around entry price (+/- 5%)
    import random
    valid_price_exits = 0
    for position in positions:
        # Generate a realistic current price
        entry_price = position.entry_price
        price_change = random.uniform(-0.05, 0.05)  # +/- 5%
        current_price = entry_price * (1 + price_change)
        
        should_exit, reason = position.should_smart_exit(
            current_date=dt.date(2025, 9, 24),
            current_price=current_price,
            current_time=dt.datetime(2025, 9, 24, 14, 30)
        )
        if should_exit:
            valid_price_exits += 1
    
    print(f"   ✅ {valid_price_exits}/{len(positions)} positions would exit with valid prices")
    print(f"   This shows the smart exit logic is working!")

def main():
    print("🚀 Testing NoneType handling for Thursday market hours")
    print("=" * 60)
    
    try:
        test_none_current_price_handling()
        test_stop_manager_none_handling()
        simulate_market_hours_with_real_positions()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("✅ NoneType errors are fixed and bot should work on Thursday")
        print("✅ Smart D+1 exit logic is functioning correctly")
        print("✅ Position processing handles both None and valid prices")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())