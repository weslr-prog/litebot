import unittest
from core.indicator_cache import IndicatorCache
from core.indicator_calculator import IndicatorCalculator

class TestIndicatorCacheInputChangeTriggersRecompute(unittest.TestCase):

    def setUp(self):
        """Set up an IndicatorCache and IndicatorCalculator instance for testing."""
        self.cache = IndicatorCache()
        self.calculator = IndicatorCalculator()

    def test_input_change_triggers_recompute(self):
        """Test that changing the input data triggers recomputation."""
        indicator_key = 'indicator_5'
        initial_input = [1, 2, 3]
        updated_input = [4, 5, 6]

        # Compute with initial input
        self.cache.retrieve_or_compute(indicator_key, initial_input, self.calculator.compute)
        initial_result = self.cache.retrieve(indicator_key)

        # Compute with updated input
        updated_result = self.cache.retrieve_or_compute(indicator_key, updated_input, self.calculator.compute)

        self.assertNotEqual(initial_result, updated_result, "Input change did not trigger recomputation.")

    def test_same_input_does_not_trigger_recompute(self):
        """Test that using the same input does not trigger recomputation."""
        indicator_key = 'indicator_6'
        input_data = [7, 8, 9]

        # Compute with input data
        first_result = self.cache.retrieve_or_compute(indicator_key, input_data, self.calculator.compute)
        second_result = self.cache.retrieve_or_compute(indicator_key, input_data, self.calculator.compute)

        self.assertEqual(first_result, second_result, "Same input should not trigger recomputation.")

if __name__ == '__main__':
    unittest.main()