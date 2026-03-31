import datetime as dt
import pytz

from traders.short_cycle_trader import (
    ShortCycleTrader,
    ShortCycleConfig,
    ShortCyclePosition,
    AISignal,
    PositionStatus,
)


def test_entry_filled_price_capture():
    # Create trader with default config
    cfg = ShortCycleConfig()
    trader = ShortCycleTrader(config=cfg, launch_gui=False, enable_intraday_analysis=False)

    # Replace execution_engine with a mock that returns a filled avg price
    class MockEngine:
        def submit_order(self, symbol, quantity, side):
            return {
                'order_id': 'mock-order-123',
                'status': 'filled',
                'avg_fill_price': 12.56,
                'submitted_at': dt.datetime.now(pytz.UTC),
                'filled_at': dt.datetime.now(pytz.UTC),
            }

    trader.execution_engine = MockEngine()

    # Build minimal AISignal
    sig = AISignal(symbol='FOO', action='BUY', confidence=0.9, time_horizon_days=1.0, entry_price=10.0)

    # Construct a ShortCyclePosition to execute
    today = dt.date.today()
    pos = ShortCyclePosition(
        symbol='FOO',
        entry_date=today,
        exit_date=today,  # Not used in this test
        entry_price=10.0,
        position_size_shares=10,
        position_size_dollars=100.0,
        stop_price=9.5,
        target_price=None,
        status=PositionStatus.PENDING,
        ai_signal=sig,
    )

    # Execute trade
    res = trader._execute_trade(pos)

    # After execution, the position.entry_price should be updated to filled price
    assert res is True
    assert pos.entry_price == 12.56
    assert pos.order_id == 'mock-order-123'
