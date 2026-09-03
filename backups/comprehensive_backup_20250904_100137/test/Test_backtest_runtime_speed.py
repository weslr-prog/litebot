import unittest
import time
from backtest.backtester import Backtester

class TestBacktestRuntimeSpeed(unittest.TestCase):

    def setUp(self):
        """Set up a Backtester instance for testing."""
        self.backtester = Backtester()

    def test_runtime_speed_under_threshold(self):
        """Test that the backtest runtime is under the acceptable threshold."""
        input_data = {
            'frequency': 'daily',
            'data': [
                {'date': '2025-08-20', 'price': 100},
                {'date': '2025-08-21', 'price': 105},
                {'date': '2025-08-22', 'price': 110}
            ]
        }

        start_time = time.time()
        self.backtester.run_backtest(input_data)
        end_time = time.time()

        runtime = end_time - start_time
        acceptable_threshold = 1.0  # seconds

        self.assertLess(runtime, acceptable_threshold, f"Backtest runtime exceeded the acceptable threshold of {acceptable_threshold} seconds.")

    def test_runtime_speed_with_large_data(self):
        """Test that the backtest runtime is reasonable with large input data."""
        large_input_data = {
            'frequency': 'daily',
            'data': [{'date': f'2025-08-{day:02d}', 'price': 100 + day} for day in range(1, 1001)]
        }

        start_time = time.time()
        self.backtester.run_backtest(large_input_data)
        end_time = time.time()

        runtime = end_time - start_time
        reasonable_threshold = 5.0  # seconds

        self.assertLess(runtime, reasonable_threshold, f"Backtest runtime for large data exceeded the reasonable threshold of {reasonable_threshold} seconds.")

if __name__ == '__main__':
    unittest.main()