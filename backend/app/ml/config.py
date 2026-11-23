"""Shared paths and strict feature allowlist for the demo models."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = Path(os.environ.get("SKILLPULSE_DATASET_PATH", PROJECT_ROOT / "data" / "synthetic" / "model_snapshots.csv"))
ARTIFACT_DIR = Path(os.environ.get("SKILLPULSE_ARTIFACT_DIR", Path(__file__).resolve().parents[2] / "artifacts"))
SUPPORT_MODEL_PATH = ARTIFACT_DIR / "support_model.joblib"
CLUSTER_MODEL_PATH = ARTIFACT_DIR / "learning_clusters.joblib"
SUPPORT_METRICS_PATH = ARTIFACT_DIR / "support_model_metrics.json"
CLUSTER_METRICS_PATH = ARTIFACT_DIR / "learning_cluster_metrics.json"

# Explicit allowlist: IDs, timestamps, source markers and the future outcome
# label are never passed to either estimator.
FEATURE_COLUMNS = [
    "avg_assessment_score",
    "score_trend",
    "attendance_rate",
    "assignment_completion_rate",
]
TARGET_COLUMN = "needed_support"
MIN_TRAINING_ROWS = 40
MIN_CLASS_ROWS = 8
TEST_SIZE = 0.25
RANDOM_STATE = 42
DECISION_THRESHOLD = 0.5

FEATURE_LABELS = {
    "avg_assessment_score": ("Average assessment score", "%", 1.0),
    "score_trend": ("Change from first to latest checkpoint", "percentage points", 1.0),
    "attendance_rate": ("Attendance rate", "%", 100.0),
    "assignment_completion_rate": ("Assignment completion", "%", 100.0),
}


def dataset_sha256() -> str:
    import hashlib

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Synthetic training data not found: {DATASET_PATH}")
    return hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
