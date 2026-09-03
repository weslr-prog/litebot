import unittest
from core.tuner import Tuner

class TestEVBucketSampleCountThreshold(unittest.TestCase):

    def setUp(self):
        """Set up a Tuner instance for testing."""
        self.tuner = Tuner()

    def test_sample_count_above_threshold(self):
        """Test that buckets with sample counts above the threshold are retained."""
        data = {
            0.1: 15,
            0.2: 5,
            0.3: 20
        }
        threshold = 10

        expected_result = {
            0.1: 15,
            0.3: 20
        }

        result = self.tuner.filter_buckets_by_sample_count(data, threshold)
        self.assertEqual(result, expected_result, "Buckets above the threshold were not retained correctly.")

    def test_sample_count_below_threshold(self):
        """Test that buckets with sample counts below the threshold are removed."""
        data = {
            0.1: 8,
            0.2: 5,
            0.3: 20
        }
        threshold = 10

        expected_result = {
            0.3: 20
        }

        result = self.tuner.filter_buckets_by_sample_count(data, threshold)
        self.assertEqual(result, expected_result, "Buckets below the threshold were not removed correctly.")

    def test_sample_count_empty_data(self):
        """Test that filtering on empty data returns an empty dictionary."""
        data = {}
        threshold = 10

        expected_result = {}

        result = self.tuner.filter_buckets_by_sample_count(data, threshold)
        self.assertEqual(result, expected_result, "Filtering on empty data should return an empty dictionary.")

if __name__ == '__main__':
    unittest.main()