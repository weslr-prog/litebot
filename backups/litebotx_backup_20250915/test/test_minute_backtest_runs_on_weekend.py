import unittest
from backtest.backtester import Backtester

class TestMinuteBacktestRunsOnWeekend(unittest.TestCase):

    def setUp(self):
        """Set up a Backtester instance for testing."""
        self.backtester = Backtester()

    def test_minute_backtest_runs_on_weekend(self):
        """Test that the minute backtest runs on weekend data."""
        # Simulate weekend data
        input_data = {
            'frequency': 'minute',
            'data': [
                {'date': '2025-08-23', 'time': '10:00', 'price': 100},  # Saturday
                {'date': '2025-08-23', 'time': '10:01', 'price': 101},
                {'date': '2025-08-24', 'time': '10:00', 'price': 102}   # Sunday
            ]
        }

        # Run minute backtest
        result = self.backtester.run_minute_backtest(input_data)

        # Verify that weekend data was processed
        self.assertTrue(result['processed_weekend_data'], "Minute backtest did not process weekend data as expected.")

    def test_minute_backtest_no_weekend_data(self):
        """Test that the minute backtest handles absence of weekend data gracefully."""
        input_data = {
            'frequency': 'minute',
            'data': [
                {'date': '2025-08-21', 'time': '10:00', 'price': 100},  # Weekday
                {'date': '2025-08-21', 'time': '10:01', 'price': 101}
            ]
        }

        # Run minute backtest
        result = self.backtester.run_minute_backtest(input_data)

        # Verify that no weekend data was processed
        self.assertFalse(result['processed_weekend_data'], "Minute backtest incorrectly processed non-weekend data as weekend data.")

if __name__ == '__main__':
    unittest.main()