import unittest
from core.indicator_cache import IndicatorCache

class TestIndicatorCacheHit(unittest.TestCase):

    def setUp(self):
        """Set up an IndicatorCache instance for testing."""
        self.cache = IndicatorCache()
        self.cache.store('indicator_1', [1, 2, 3])
        self.cache.store('indicator_2', [4, 5, 6])

    def test_cache_hit(self):
        """Test that a cache hit returns the correct data."""
        result = self.cache.retrieve('indicator_1')
        expected_result = [1, 2, 3]
        self.assertEqual(result, expected_result, "Cache hit did not return the expected data.")

    def test_cache_miss(self):
        """Test that a cache miss returns None."""
        result = self.cache.retrieve('non_existent_indicator')
        self.assertIsNone(result, "Cache miss should return None.")

    def test_cache_overwrite(self):
        """Test that storing an indicator with the same key overwrites the existing data."""
        self.cache.store('indicator_1', [7, 8, 9])
        result = self.cache.retrieve('indicator_1')
        expected_result = [7, 8, 9]
        self.assertEqual(result, expected_result, "Cache overwrite did not update the data correctly.")

if __name__ == '__main__':
    unittest.main()