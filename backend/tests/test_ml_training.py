"""ML training contract tests for leakage prevention and evaluation outputs."""

import unittest

from app.ml.config import FEATURE_COLUMNS
from app.ml.train import load_and_validate_dataset, train_learning_clusters, train_support_model


class ModelTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features, cls.labels = load_and_validate_dataset()

    def test_feature_allowlist_excludes_future_outcome_and_identifiers(self):
        self.assertEqual(list(self.features.columns), FEATURE_COLUMNS)
        self.assertNotIn("needed_support", self.features.columns)
        self.assertNotIn("student_id", self.features.columns)
        self.assertEqual(len(self.features), len(self.labels))

    def test_logistic_regression_uses_holdout_and_reports_metrics(self):
        bundle, report = train_support_model(self.features, self.labels, "test-hash")
        self.assertEqual(report["data_origin"], "synthetic_demo")
        self.assertEqual(report["train_sample_count"] + report["test_sample_count"], len(self.features))
        self.assertEqual(report["test_sample_count"], sum(sum(row) for row in report["confusion_matrix"]["values"]))
        self.assertEqual(set(report["metrics"]), {"precision", "recall", "f1_score"})
        self.assertEqual(bundle["feature_columns"], FEATURE_COLUMNS)

    def test_kmeans_reports_three_clusters_without_outcome_feature(self):
        bundle, report = train_learning_clusters(self.features, "test-hash")
        self.assertEqual(report["cluster_count"], 3)
        self.assertEqual(sum(report["cluster_sizes"].values()), len(self.features))
        self.assertNotIn("needed_support", bundle["feature_columns"])


if __name__ == "__main__":
    unittest.main()
