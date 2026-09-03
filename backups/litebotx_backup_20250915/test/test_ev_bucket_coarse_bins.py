import unittest
from core.tuner import Tuner

class TestEVBucketCoarseBins(unittest.TestCase):

    def setUp(self):
        """Set up a Tuner instance for testing."""
        self.tuner = Tuner()

    def test_ev_bucket_coarse_bins(self):
        """Test that EV bucket coarse binning works as expected."""
        # Define test cases
        test_cases = [
            (0.03, 0.05),
            (0.07, 0.1),
            (0.15, 0.2),
            (0.25, 0.3),
            (0.35, 0.4),
            (0.45, 0.5),
        ]

        for ev, expected_bin in test_cases:
            with self.subTest(ev=ev):
                result = self.tuner.coarse_bin_ev(ev)
                self.assertEqual(result, expected_bin, f"EV {ev} did not map to expected bin {expected_bin}")

    def test_ev_bucket_out_of_range(self):
        """Test that out-of-range EV values raise an exception."""
        with self.assertRaises(ValueError):
            self.tuner.coarse_bin_ev(-0.1)  # Negative EV

        with self.assertRaises(ValueError):
            self.tuner.coarse_bin_ev(1.1)  # EV greater than 1

if __name__ == '__main__':
    unittest.main()