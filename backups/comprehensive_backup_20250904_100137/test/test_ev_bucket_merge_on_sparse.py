import unittest
from core.tuner import Tuner

class TestEVBucketMergeOnSparse(unittest.TestCase):

    def setUp(self):
        """Set up a Tuner instance for testing."""
        self.tuner = Tuner()

    def test_ev_bucket_merge_sparse(self):
        """Test merging EV buckets on sparse data."""
        # Define sparse data test case
        sparse_data = {
            0.05: 10,
            0.15: 5,
            0.35: 2,
            0.55: 1
        }

        # Expected result after merging
        expected_result = {
            0.1: 15,  # Merged 0.05 and 0.15
            0.4: 3,   # Merged 0.35 and 0.55
        }

        result = self.tuner.merge_sparse_ev_buckets(sparse_data)
        self.assertEqual(result, expected_result, "Sparse EV bucket merging did not produce the expected result.")

    def test_ev_bucket_merge_empty(self):
        """Test merging EV buckets on empty data."""
        sparse_data = {}
        expected_result = {}

        result = self.tuner.merge_sparse_ev_buckets(sparse_data)
        self.assertEqual(result, expected_result, "Merging on empty data should return an empty dictionary.")

if __name__ == '__main__':
    unittest.main()