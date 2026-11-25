"""
AgriResolve AI - End-to-End Integration Tests (Phase 14)
Simulates and tests the complete operational workflow:
1. Ingestion of raw sensor and agricultural data
2. Cleaning, derived indicator computations, and reliability index
3. Database loading and query execution
4. Routine Monitoring risk detection
5. Reported Issue grievance escalation
6. Combined explainable prioritization and capacity-aware ranking
7. AI Field Assistant RAG query execution with official citations
"""

import unittest
from pathlib import Path
import pandas as pd

from src.ingestion.ingest_villages import ingest_villages
from src.preprocessing.cleaning_and_derivation import clean_and_derive
from src.monitoring.routine import run_routine_monitoring
from src.monitoring.reported import run_reported_monitoring
from src.priority_engine.engine import run_priority_engine
from src.rag_assistant.assistant import query_rag_assistant

class TestEndToEndWorkflow(unittest.TestCase):

    def test_01_data_pipeline_integrity(self):
        """Verify that cleaning and derived pipelines produce valid non-empty files."""
        clean_and_derive()
        self.assertTrue(Path("data/cleaned/villages_cleaned.xlsx").exists())
        self.assertTrue(Path("data/derived/rainfall_anomaly_derived.xlsx").exists())
        self.assertTrue(Path("data/derived/ndvi_trends_derived.xlsx").exists())
        self.assertTrue(Path("data/derived/village_reliability_derived.xlsx").exists())

    def test_02_routine_monitoring_execution(self):
        """Verify that routine monitoring evaluates all 7 villages and assigns risk scores."""
        df_routine = run_routine_monitoring()
        self.assertEqual(len(df_routine), 7)
        self.assertTrue((df_routine["routine_risk_score"] >= 0).all())
        self.assertTrue((df_routine["routine_risk_score"] <= 100).all())
        self.assertIn("explanation", df_routine.columns)

    def test_03_reported_monitoring_execution(self):
        """Verify that reported monitoring correctly aggregates complaints and computes severity."""
        df_reported = run_reported_monitoring()
        self.assertEqual(len(df_reported), 7)
        self.assertTrue((df_reported["reported_severity_score"] >= 0).all())
        self.assertTrue((df_reported["total_complaints"] >= 0).all())

    def test_04_combined_priority_engine(self):
        """Verify that the Combined Priority Engine ranks villages and recommends actions."""
        df_priorities, df_factors = run_priority_engine()
        self.assertEqual(len(df_priorities), 7)
        self.assertEqual(list(df_priorities["rank_order"]), [1, 2, 3, 4, 5, 6, 7])
        self.assertTrue("Inspect First" in df_priorities.iloc[0]["recommendation_action"])
        self.assertTrue(len(df_factors) >= 28)  # 4 factors * 7 villages

    def test_05_rag_assistant_retrieval(self):
        """Verify that the AI Field Assistant returns official UAS Bangalore citations."""
        res_paddy = query_rag_assistant("Paddy", "yellow stem borer control")
        self.assertIn("Yellow Stem Borer", res_paddy["answer"])
        self.assertIn("UAS Bengaluru", res_paddy["citation"])

        res_ragi = query_rag_assistant("Ragi", "drought mitigation")
        self.assertIn("Dryland", res_ragi["citation"])

if __name__ == "__main__":
    unittest.main()
