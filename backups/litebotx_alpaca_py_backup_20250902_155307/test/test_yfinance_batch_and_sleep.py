import unittest
from unittest.mock import patch
from core.data_fetcher import DataFetcher

class TestYFinanceBatchAndSleep(unittest.TestCase):

    def setUp(self):
        """Set up a DataFetcher instance for testing."""
        self.fetcher = DataFetcher()

    @patch('core.data_fetcher.time.sleep')
    def test_batch_processing_with_sleep(self, mock_sleep):
        """Test that yfinance batching includes sleep between requests."""
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        batch_size = 2

        with patch.object(self.fetcher, 'fetch_data', return_value={}) as mock_fetch:
            self.fetcher.fetch_in_batches(tickers, batch_size=batch_size, sleep_time=1)

            # Verify fetch_data was called for each ticker
            self.assertEqual(mock_fetch.call_count, len(tickers), "fetch_data was not called for each ticker.")

            # Verify sleep was called between batches
            self.assertEqual(mock_sleep.call_count, len(tickers) // batch_size - 1, "Sleep was not called the correct number of times.")

    def test_empty_ticker_list(self):
        """Test that an empty ticker list is handled gracefully."""
        tickers = []
        batch_size = 2

        with patch.object(self.fetcher, 'fetch_data', return_value={}) as mock_fetch:
            self.fetcher.fetch_in_batches(tickers, batch_size=batch_size, sleep_time=1)

            # Verify fetch_data was not called
            mock_fetch.assert_not_called()

if __name__ == '__main__':
    unittest.main()