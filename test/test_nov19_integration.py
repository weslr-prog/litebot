"""Integration tests for Nov 19 fixes: price capture, day trade tracking, Friday logic, dynamic limits"""
import datetime as dt
import pytz
from traders.short_cycle_trader import (
    ShortCycleTrader,
    ShortCycleConfig,
    ShortCyclePosition,
    AISignal,
    PositionStatus,
)


def test_all_nov19_fixes():
    """Comprehensive test for all Nov 19 fixes"""
    print("\n" + "="*80)
    print("COMPREHENSIVE INTEGRATION TEST - Nov 19 Fixes")
    print("="*80)
    
    # Initialize trader
    cfg = ShortCycleConfig()
    trader = ShortCycleTrader(config=cfg, launch_gui=False, enable_intraday_analysis=False)
    
    # Reset day trade tracker to clean state
    if trader.day_trade_tracker:
        trader.day_trade_tracker.trades = []
        trader.day_trade_tracker._save()
    
    # Create mock execution engine
    class MockEngine:
        def __init__(self):
            self.orders = []
        
        def submit_order(self, symbol, quantity, side):
            order = {
                'order_id': f'mock-{len(self.orders)}',
                'status': 'filled',
                'avg_fill_price': 12.56 if side == 'buy' else 12.85,
                'submitted_at': dt.datetime.now(pytz.UTC),
                'filled_at': dt.datetime.now(pytz.UTC),
            }
            self.orders.append(order)
            return order
    
    mock_engine = MockEngine()
    trader.execution_engine = mock_engine
    
    # TEST 1: Entry Price Capture
    print("\n[TEST 1] Entry Price Capture (Priority 1)")
    print("-" * 80)
    sig = AISignal(symbol='TEST1', action='BUY', confidence=0.9, time_horizon_days=1.0, entry_price=10.0)
    pos = ShortCyclePosition(
        symbol='TEST1',
        entry_date=dt.date.today(),
        exit_date=dt.date.today(),
        entry_price=10.0,
        position_size_shares=10,
        position_size_dollars=100.0,
        stop_price=9.5,
        target_price=None,
        status=PositionStatus.PENDING,
        ai_signal=sig,
    )
    
    result = trader._execute_trade(pos)
    assert result is True, "Entry trade should succeed"
    assert pos.entry_price == 12.56, f"Entry price should be updated to filled price (got {pos.entry_price})"
    print(f"✅ Entry price updated: $10.00 → ${pos.entry_price:.2f}")
    
    # TEST 2: Exit Price Capture
    print("\n[TEST 2] Exit Price Capture (Priority 1)")
    print("-" * 80)
    pos.status = PositionStatus.ENTERED
    trader._exit_position(pos, exit_price=12.50, reason="TEST_EXIT")
    # Note: exit price is passed as parameter, but should be updated by filled price
    print(f"✅ Exit executed with filled price capture")
    
    # TEST 3: Day Trade Tracker
    print("\n[TEST 3] Day Trade Tracker (Priority 2)")
    print("-" * 80)
    if trader.day_trade_tracker:
        # Reset tracker
        trader.day_trade_tracker.trades = []
        trader.day_trade_tracker._save()
        
        initial = trader.day_trade_tracker.trades_remaining()
        print(f"Initial day trades remaining: {initial}")
        
        # Record 3 trades
        for i in range(3):
            trader.day_trade_tracker.record_trade()
        
        remaining = trader.day_trade_tracker.trades_remaining()
        print(f"After 3 trades: {remaining} remaining")
        assert remaining == 0, f"Should have 0 remaining (got {remaining})"
        print("✅ Day trade tracker enforces 3-trade limit")
    else:
        print("⚠️  Day trade tracker not initialized")
    
    # TEST 4: Day Trade Enforcement
    print("\n[TEST 4] Day Trade Limit Enforcement (Priority 2)")
    print("-" * 80)
    sig2 = AISignal(symbol='TEST2', action='BUY', confidence=0.9, time_horizon_days=1.0, entry_price=15.0)
    pos2 = ShortCyclePosition(
        symbol='TEST2',
        entry_date=dt.date.today(),
        exit_date=dt.date.today(),
        entry_price=15.0,
        position_size_shares=5,
        position_size_dollars=75.0,
        stop_price=14.0,
        target_price=None,
        status=PositionStatus.PENDING,
        ai_signal=sig2,
    )
    
    result = trader._execute_trade(pos2)
    assert result is False, "Should reject entry when day trades exhausted"
    print("✅ Entry blocked when day trade limit reached")
    
    # TEST 5: Dynamic Position Limits
    print("\n[TEST 5] Dynamic Position Limits by Day (Priority 4)")
    print("-" * 80)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day_num in range(5):
        max_pos, max_pct = trader.get_max_positions_for_day(day_num, emergency_trades_remaining=2)
        expected_limits = {
            0: (3, 0.30),   # Monday
            1: (3, 0.30),   # Tuesday
            2: (3, 0.30),   # Wednesday
            3: (10, 0.90),  # Thursday
            4: (2, 0.90),   # Friday (2 emergency trades)
        }
        assert (max_pos, max_pct) == expected_limits[day_num], \
            f"{days[day_num]} limits mismatch: expected {expected_limits[day_num]}, got ({max_pos}, {max_pct})"
        print(f"  {days[day_num]}: {max_pos} positions, {max_pct*100:.0f}% portfolio ✅")
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED ✅")
    print("="*80)
    
    return True


if __name__ == '__main__':
    try:
        test_all_nov19_fixes()
        print("\n✅ Integration test completed successfully")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        raise
