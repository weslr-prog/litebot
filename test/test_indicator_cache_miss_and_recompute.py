import unittest
from core.indicator_cache import IndicatorCache
from core.indicator_calculator import IndicatorCalculator

class TestIndicatorCacheMissAndRecompute(unittest.TestCase):

    def setUp(self):
        """Set up an IndicatorCache and IndicatorCalculator instance for testing."""
        self.cache = IndicatorCache()
        self.calculator = IndicatorCalculator()

    def test_cache_miss_and_recompute(self):
        """Test that a cache miss triggers recomputation of the indicator."""
        indicator_key = 'indicator_3'
        input_data = [10, 20, 30]

        # Simulate recomputation
        expected_result = self.calculator.compute(indicator_key, input_data)
        result = self.cache.retrieve_or_compute(indicator_key, input_data, self.calculator.compute)

        self.assertEqual(result, expected_result, "Cache miss did not trigger recomputation correctly.")

    def test_cache_hit_after_recompute(self):
        """Test that after recomputation, the result is stored in the cache."""
        indicator_key = 'indicator_4'
        input_data = [5, 15, 25]

        # Simulate recomputation and store in cache
        self.cache.retrieve_or_compute(indicator_key, input_data, self.calculator.compute)

        # Retrieve from cache
        result = self.cache.retrieve(indicator_key)
        expected_result = self.calculator.compute(indicator_key, input_data)

        self.assertEqual(result, expected_result, "Recomputed result was not stored in the cache correctly.")

if __name__ == '__main__':
    unittest.main()