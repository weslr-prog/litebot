import unittest
from backtest.backtester import Backtester

class TestFastBacktestUsesDailyBars(unittest.TestCase):

    def setUp(self):
        """Set up a Backtester instance for testing."""
        self.backtester = Backtester()

    def test_fast_backtest_uses_daily_bars(self):
        """Test that the fast backtest uses daily bars as expected."""
        # Simulate input data
        input_data = {
            'frequency': 'daily',
            'data': [
                {'date': '2025-08-20', 'price': 100},
                {'date': '2025-08-21', 'price': 105},
                {'date': '2025-08-22', 'price': 110}
            ]
        }

        # Run fast backtest
        result = self.backtester.run_fast_backtest(input_data)

        # Verify that daily bars were used
        self.assertTrue(result['used_daily_bars'], "Fast backtest did not use daily bars as expected.")

    def test_fast_backtest_invalid_frequency(self):
        """Test that an invalid frequency raises an exception."""
        input_data = {
            'frequency': 'hourly',
            'data': [
                {'date': '2025-08-20', 'price': 100},
                {'date': '2025-08-21', 'price': 105}
            ]
        }

        with self.assertRaises(ValueError):
            self.backtester.run_fast_backtest(input_data)

if __name__ == '__main__':
    unittest.main()