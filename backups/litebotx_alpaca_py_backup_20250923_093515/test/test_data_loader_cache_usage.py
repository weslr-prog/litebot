import unittest
from unittest.mock import patch
from core.data_loader import DataLoader

class TestDataLoaderCacheUsage(unittest.TestCase):

    def setUp(self):
        """Set up a DataLoader instance for testing."""
        self.loader = DataLoader('test_api_key', 'test_api_secret', 'test_polygon_key')

    @patch.object(DataLoader, 'load_from_cache', return_value={'data': 'cached_data'})
    def test_cache_hit(self, mock_load_from_cache):
        """Test that data is loaded from cache when available."""
        result = self.loader.load('test_key')

        # Verify load_from_cache was called
        mock_load_from_cache.assert_called_once_with('test_key')
        self.assertEqual(result, {'data': 'cached_data'}, "Cache hit did not return the expected data.")

    @patch.object(DataLoader, 'load_from_cache', return_value=None)
    @patch.object(DataLoader, 'load_from_source', return_value={'data': 'source_data'})
    def test_cache_miss(self, mock_load_from_source, mock_load_from_cache):
        """Test that data is loaded from source when cache is missed."""
        result = self.loader.load('test_key')

        # Verify load_from_cache was called and returned None
        mock_load_from_cache.assert_called_once_with('test_key')

        # Verify load_from_source was called
        mock_load_from_source.assert_called_once_with('test_key')
        self.assertEqual(result, {'data': 'source_data'}, "Cache miss did not load data from the source correctly.")

if __name__ == '__main__':
    unittest.main()