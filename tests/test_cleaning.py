"""
Unit tests for data cleaning and preprocessing in AgriResolve AI.
Verifies data integrity, bound constraints, null checks, and synthetic flags.
"""

import unittest
from pathlib import Path
import pandas as pd
import numpy as np

class TestDataCleaning(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.clean_dir = Path("data/cleaned")
        cls.derived_dir = Path("data/derived")
        cls.synthetic_dir = Path("data/synthetic")
        
        # Load cleaned & derived files
        cls.df_villages = pd.read_excel(cls.clean_dir / "villages_cleaned.xlsx")
        cls.df_rain = pd.read_excel(cls.derived_dir / "rainfall_anomaly_derived.xlsx")
        cls.df_ndvi = pd.read_excel(cls.derived_dir / "ndvi_trends_derived.xlsx")
        cls.df_complaints = pd.read_excel(cls.clean_dir / "complaints_cleaned.xlsx")
        cls.df_reliability = pd.read_excel(cls.derived_dir / "village_reliability_derived.xlsx")

    def test_villages_integrity(self):
        """Ensure all 7 villages have valid LGD codes and coordinates within Mandya bounds."""
        self.assertEqual(len(self.df_villages), 7)
        self.assertFalse(self.df_villages["lgd_code"].isnull().any())
        self.assertTrue((self.df_villages["latitude"].between(12.4, 12.8)).all())
        self.assertTrue((self.df_villages["longitude"].between(76.8, 77.2)).all())

    def test_rainfall_bounds(self):
        """Ensure rainfall values are strictly non-negative and anomalies are computed."""
        self.assertTrue((self.df_rain["actual_rainfall_mm"] >= 0.0).all())
        self.assertIn("rainfall_anomaly_percent", self.df_rain.columns)
        self.assertFalse(self.df_rain["rainfall_anomaly_percent"].isnull().any())

    def test_ndvi_ranges(self):
        """Ensure NDVI is strictly bounded within [-1.0, 1.0], specifically positive agricultural vegetation."""
        self.assertTrue((self.df_ndvi["mean_ndvi"] >= 0.0).all())
        self.assertTrue((self.df_ndvi["mean_ndvi"] <= 1.0).all())
        self.assertIn("vegetation_stress_flag", self.df_ndvi.columns)

    def test_synthetic_flags(self):
        """Ensure every synthetic record carries is_synthetic=True and data_type='Synthetic'."""
        self.assertTrue(self.df_complaints["is_synthetic"].all())
        self.assertTrue((self.df_complaints["data_type"] == "Synthetic").all())

    def test_reliability_scores(self):
        """Ensure reliability scores are between 0.0 and 1.0."""
        self.assertEqual(len(self.df_reliability), 7)
        self.assertTrue((self.df_reliability["overall_reliability_score"].between(0.0, 1.0)).all())

if __name__ == "__main__":
    unittest.main()
