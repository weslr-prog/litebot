import os
import unittest
import subprocess
import pandas as pd

class TestRefreshUniverse(unittest.TestCase):
    """Unit test for the refresh_universe.py script."""

    def setUp(self):
        """Set up test environment."""
        self.universe_file = os.path.join(os.getcwd(), "data", "universe.csv")
        # Ensure the universe file does not exist before the test
        if os.path.exists(self.universe_file):
            os.remove(self.universe_file)

    def test_refresh_universe(self):
        """Test that refresh_universe.py runs without errors and creates the universe file."""
        # Run the refresh_universe.py script
        result = subprocess.run(
            ["python", "core/refresh_universe.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check that the script ran successfully
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")

        # Check that the universe.csv file was created
        self.assertTrue(os.path.exists(self.universe_file), "universe.csv file was not created")

        # Check that the universe.csv file contains valid data
        df = pd.read_csv(self.universe_file)
        self.assertFalse(df.empty, "universe.csv is empty")
        self.assertIn("symbol", df.columns, "universe.csv does not contain 'symbol' column")

    def tearDown(self):
        """Clean up after the test."""
        if os.path.exists(self.universe_file):
            os.remove(self.universe_file)

if __name__ == "__main__":
    unittest.main()