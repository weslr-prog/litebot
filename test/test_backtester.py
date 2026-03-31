import unittest
from unittest.mock import patch, mock_open
import os
from backtest.backtester import run_backtests_from_universe, BacktestConfig

class TestBacktester(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data="symbol\nAAPL\nGOOGL\nTSLA\n")
    @patch("os.path.exists", return_value=True)
    @patch("backtest.backtester.run_backtest", return_value={"ok": True})
    def test_run_backtests_from_universe(self, mock_run_backtest, mock_exists, mock_file):
        """Test that backtests are run for all symbols in the universe CSV."""
        run_backtests_from_universe()

        # Check if the universe file was opened
        mock_file.assert_called_once_with("data/universe.csv", "r")

        # Check if backtests were run for each symbol
        mock_run_backtest.assert_any_call(BacktestConfig(symbol="AAPL"))
        mock_run_backtest.assert_any_call(BacktestConfig(symbol="GOOGL"))
        mock_run_backtest.assert_any_call(BacktestConfig(symbol="TSLA"))
        self.assertEqual(mock_run_backtest.call_count, 3)

    @patch("os.path.exists", return_value=False)
    def test_universe_file_missing(self, mock_exists):
        """Test behavior when the universe file is missing."""
        with self.assertLogs(level="ERROR") as log:
            run_backtests_from_universe()
            self.assertIn("Universe file not found", log.output[0])

if __name__ == "__main__":
    unittest.main()