import unittest
from unittest.mock import patch
from core.data_loader import DataLoader

class TestDataLoaderRateLimitHandling(unittest.TestCase):

    def setUp(self):
        """Set up a DataLoader instance for testing."""
        self.loader = DataLoader('test_api_key', 'test_api_secret', 'test_polygon_key')

    @patch('core.data_loader.time.sleep')
    @patch.object(DataLoader, 'load_from_source', side_effect=[Exception("Rate limit exceeded"), {'data': 'source_data'}])
    def test_rate_limit_handling(self, mock_load_from_source, mock_sleep):
        """Test that rate limit exceptions are handled with retries."""
        result = self.loader.load_with_rate_limit('test_key')

        # Verify load_from_source was called twice (retry after rate limit exception)
        self.assertEqual(mock_load_from_source.call_count, 2, "load_from_source was not retried after rate limit exception.")

        # Verify sleep was called once (between retries)
        mock_sleep.assert_called_once()

        self.assertEqual(result, {'data': 'source_data'}, "Rate limit handling did not return the expected data after retry.")

    @patch.object(DataLoader, 'load_from_source', side_effect=Exception("Rate limit exceeded"))
    def test_rate_limit_exceeded_permanently(self, mock_load_from_source):
        """Test that permanent rate limit exceptions are raised after retries."""
        with self.assertRaises(Exception) as context:
            self.loader.load_with_rate_limit('test_key')

        self.assertEqual(str(context.exception), "Rate limit exceeded", "Permanent rate limit exception was not raised correctly.")

if __name__ == '__main__':
    unittest.main()