"""Train and evaluate the support model and unsupervised learning clusters."""

from datetime import datetime, timezone
import json

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.config import (
    ARTIFACT_DIR,
    CLUSTER_METRICS_PATH,
    CLUSTER_MODEL_PATH,
    DATASET_PATH,
    DECISION_THRESHOLD,
    FEATURE_COLUMNS,
    MIN_CLASS_ROWS,
    MIN_TRAINING_ROWS,
    RANDOM_STATE,
    SUPPORT_METRICS_PATH,
    SUPPORT_MODEL_PATH,
    TARGET_COLUMN,
    TEST_SIZE,
    dataset_sha256,
)


class InsufficientTrainingData(ValueError):
    """Raised when the current dataset cannot support a defensible split."""


def validate_dataset_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN, "student_id", "snapshot_date", "outcome_date", "data_origin"])
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise InsufficientTrainingData(f"Training data is missing required columns: {', '.join(missing)}")
    if frame.empty or len(frame) < MIN_TRAINING_ROWS:
        raise InsufficientTrainingData(
            f"At least {MIN_TRAINING_ROWS} complete learner snapshots are required; found {len(frame)}."
        )
    if frame["student_id"].duplicated().any():
        raise InsufficientTrainingData(
            "This demo trainer expects one snapshot per learner. Repeated snapshots need a learner-grouped split."
        )
    if not (frame["data_origin"] == "synthetic_demo").all():
        raise InsufficientTrainingData("This demo model only trains on data marked synthetic_demo.")

    snapshot_dates = pd.to_datetime(frame["snapshot_date"], errors="coerce")
    outcome_dates = pd.to_datetime(frame["outcome_date"], errors="coerce")
    if snapshot_dates.isna().any() or outcome_dates.isna().any() or not (snapshot_dates < outcome_dates).all():
        raise InsufficientTrainingData("Every historical snapshot must have a later follow-up outcome date.")

    # Select only this allowlist. Metadata and the target are never features.
    features = frame.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    if features.isna().any().any() or not np.isfinite(features.to_numpy(dtype=float)).all():
        raise InsufficientTrainingData("Historical feature columns contain missing or non-finite values.")
    if not features["avg_assessment_score"].between(0, 100).all():
        raise InsufficientTrainingData("Average assessment scores must be between 0 and 100.")
    for column in ("attendance_rate", "assignment_completion_rate"):
        if not features[column].between(0, 1).all():
            raise InsufficientTrainingData(f"{column} must be a fraction between 0 and 1.")
    if not features["score_trend"].between(-100, 100).all():
        raise InsufficientTrainingData("Score trend must be between -100 and 100 percentage points.")
    labels = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise InsufficientTrainingData("The support outcome must contain only binary 0/1 labels.")
    labels = labels.astype(int)
    counts = labels.value_counts()
    if len(counts) != 2 or int(counts.min()) < MIN_CLASS_ROWS:
        raise InsufficientTrainingData(
            f"At least {MIN_CLASS_ROWS} examples of both outcome classes are required for a stratified evaluation."
        )
    return features, labels


def load_and_validate_dataset() -> tuple[pd.DataFrame, pd.Series]:
    if not DATASET_PATH.exists():
        raise InsufficientTrainingData(
            f"Training data is missing at {DATASET_PATH}. Regenerate the synthetic dataset first."
        )
    return validate_dataset_frame(pd.read_csv(DATASET_PATH))


def train_support_model(features: pd.DataFrame, labels: pd.Series, source_hash: str) -> tuple[dict, dict]:
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    pipeline = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        ]
    )
    # The scaler is fitted only on the training partition as part of the pipeline.
    pipeline.fit(x_train, y_train)
    y_pred = (pipeline.predict_proba(x_test)[:, 1] >= DECISION_THRESHOLD).astype(int)
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])
    metrics = {
        "model": "Logistic Regression",
        "data_origin": "synthetic_demo",
        "sample_count": int(len(features)),
        "train_sample_count": int(len(x_train)),
        "test_sample_count": int(len(x_test)),
        "positive_label": "needed_support",
        "class_counts": {
            "train": {str(key): int(value) for key, value in y_train.value_counts().sort_index().items()},
            "test": {str(key): int(value) for key, value in y_test.value_counts().sort_index().items()},
        },
        "feature_columns": list(FEATURE_COLUMNS),
        "decision_threshold": DECISION_THRESHOLD,
        "metrics": {
            "precision": round(float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        },
        "confusion_matrix": {
            "labels": ["on_track (0)", "needs_support (1)"],
            "values": matrix.astype(int).tolist(),
        },
        "split": f"stratified {int((1 - TEST_SIZE) * 100)}/{int(TEST_SIZE * 100)} train/test split; random_state={RANDOM_STATE}",
        "scikit_learn_version": sklearn.__version__,
        "dataset_sha256": source_hash,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "notice": "Synthetic demonstration evaluation only; not validated or calibrated on real learners and not a placement or certification decision.",
    }
    bundle = {
        "pipeline": pipeline,
        "feature_columns": list(FEATURE_COLUMNS),
        "decision_threshold": DECISION_THRESHOLD,
        "dataset_sha256": source_hash,
        "scikit_learn_version": sklearn.__version__,
    }
    return bundle, metrics


def train_learning_clusters(features: pd.DataFrame, source_hash: str) -> tuple[dict, dict]:
    if len(features) < 12:
        raise InsufficientTrainingData("At least 12 complete learner snapshots are required to form three clusters.")

    pipeline = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            ("cluster", KMeans(n_clusters=3, n_init=20, random_state=RANDOM_STATE)),
        ]
    )
    # This clustering is unsupervised: the future support label is not passed in.
    cluster_ids = pipeline.fit_predict(features)
    if len(set(cluster_ids)) < 2:
        raise InsufficientTrainingData("The synthetic features did not form distinct clusters; no cluster model was saved.")

    counts = np.bincount(cluster_ids, minlength=3)
    scaler = pipeline.named_steps["scale"]
    estimator = pipeline.named_steps["cluster"]
    centroids = scaler.inverse_transform(estimator.cluster_centers_)
    metrics = {
        "model": "K-Means",
        "data_origin": "synthetic_demo",
        "sample_count": int(len(features)),
        "feature_columns": list(FEATURE_COLUMNS),
        "cluster_count": 3,
        "cluster_sizes": {str(index): int(count) for index, count in enumerate(counts)},
        "centroids": {
            str(index): {name: round(float(value), 4) for name, value in zip(FEATURE_COLUMNS, centroid)}
            for index, centroid in enumerate(centroids)
        },
        "silhouette_score": round(float(silhouette_score(scaler.transform(features), cluster_ids, n_jobs=1)), 4),
        "scikit_learn_version": sklearn.__version__,
        "dataset_sha256": source_hash,
        "notice": "Cluster IDs are arbitrary descriptive groupings of synthetic demonstration data, not learner quality ratings.",
    }
    bundle = {
        "pipeline": pipeline,
        "feature_columns": list(FEATURE_COLUMNS),
        "dataset_sha256": source_hash,
        "scikit_learn_version": sklearn.__version__,
        "metrics": metrics,
    }
    return bundle, metrics


def train_models() -> tuple[dict, dict]:
    features, labels = load_and_validate_dataset()
    source_hash = dataset_sha256()
    support_bundle, support_metrics = train_support_model(features, labels, source_hash)
    cluster_bundle, cluster_metrics = train_learning_clusters(features, source_hash)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(support_bundle, SUPPORT_MODEL_PATH)
    joblib.dump(cluster_bundle, CLUSTER_MODEL_PATH)
    SUPPORT_METRICS_PATH.write_text(json.dumps(support_metrics, indent=2), encoding="utf-8")
    CLUSTER_METRICS_PATH.write_text(json.dumps(cluster_metrics, indent=2), encoding="utf-8")
    return support_metrics, cluster_metrics


if __name__ == "__main__":
    try:
        support_report, cluster_report = train_models()
    except InsufficientTrainingData as error:
        raise SystemExit(f"Model training stopped: {error}") from error
    print(json.dumps({"support_model": support_report, "learning_clusters": cluster_report}, indent=2))
