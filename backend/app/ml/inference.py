"""Model loading, historical feature calculation and trainer-facing results."""

from collections import defaultdict
from datetime import date
import json

import joblib
import numpy as np
import pandas as pd
import sklearn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.config import (
    CLUSTER_METRICS_PATH,
    CLUSTER_MODEL_PATH,
    FEATURE_COLUMNS,
    FEATURE_LABELS,
    SUPPORT_METRICS_PATH,
    SUPPORT_MODEL_PATH,
    dataset_sha256,
)
from app.models import Assessment, AssessmentResult, Assignment, AssignmentSubmission, AttendanceRecord


class ModelUnavailable(RuntimeError):
    """Raised when a model artifact is absent or stale for the current dataset."""


def _load_bundle(path):
    if not path.exists():
        raise ModelUnavailable("The demonstration model has not been trained. Run `python -m app.ml.train` from backend/.")
    try:
        bundle = joblib.load(path)
    except Exception as error:
        raise ModelUnavailable("The saved model could not be loaded; retrain it with `python -m app.ml.train`.") from error
    if bundle.get("scikit_learn_version") != sklearn.__version__:
        raise ModelUnavailable("The model was trained with a different scikit-learn version. Retrain it before predicting.")
    if bundle.get("dataset_sha256") != dataset_sha256():
        raise ModelUnavailable("The synthetic training data changed after training. Retrain the models before predicting.")
    return bundle


def get_support_bundle() -> dict:
    return _load_bundle(SUPPORT_MODEL_PATH)


def get_cluster_bundle() -> dict:
    return _load_bundle(CLUSTER_MODEL_PATH)


def read_metrics(path) -> dict:
    if not path.exists():
        raise ModelUnavailable("Model metrics are unavailable. Run `python -m app.ml.train` from backend/.")
    return json.loads(path.read_text(encoding="utf-8"))


def get_support_metrics() -> dict:
    metrics = read_metrics(SUPPORT_METRICS_PATH)
    if metrics.get("dataset_sha256") != dataset_sha256():
        raise ModelUnavailable("The synthetic training data changed after evaluation. Retrain the models to refresh metrics.")
    return metrics


def get_cluster_metrics() -> dict:
    metrics = read_metrics(CLUSTER_METRICS_PATH)
    if metrics.get("dataset_sha256") != dataset_sha256():
        raise ModelUnavailable("The synthetic training data changed after clustering. Retrain the models to refresh clusters.")
    return metrics


def historical_features(db: Session, student_id: str) -> tuple[dict | None, list[str], date]:
    """Aggregate only recorded activity dated on or before today's cutoff."""
    cutoff = date.today()
    score_rows = db.execute(
        select(Assessment.assessment_date, AssessmentResult.score, Assessment.max_score)
        .join(AssessmentResult, AssessmentResult.assessment_id == Assessment.assessment_id)
        .where(AssessmentResult.student_id == student_id, Assessment.assessment_date <= cutoff)
        .order_by(Assessment.assessment_date)
    ).all()
    scores_by_date: dict[date, list[float]] = defaultdict(list)
    all_scores = []
    for assessment_date, score, max_score in score_rows:
        normalized = float(score) / float(max_score) * 100
        scores_by_date[assessment_date].append(normalized)
        all_scores.append(normalized)

    attendance = db.scalars(
        select(AttendanceRecord.status).where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.session_date <= cutoff,
        )
    ).all()
    assignment_rows = db.execute(
        select(AssignmentSubmission.submitted_at)
        .join(Assignment, Assignment.assignment_id == AssignmentSubmission.assignment_id)
        .where(AssignmentSubmission.student_id == student_id, Assignment.assigned_date <= cutoff)
    ).all()
    submitted = [submitted_at for (submitted_at,) in assignment_rows]
    submitted_count = sum(value is not None and value <= cutoff for value in submitted)

    missing = []
    if len(scores_by_date) < 2:
        missing.append("at least two dated assessment checkpoints")
    if len(attendance) < 2:
        missing.append("at least two attendance sessions")
    if len(submitted) < 1:
        missing.append("at least one assigned task")
    if missing:
        return None, missing, cutoff

    dates = sorted(scores_by_date)
    first_checkpoint_average = float(np.mean(scores_by_date[dates[0]]))
    latest_checkpoint_average = float(np.mean(scores_by_date[dates[-1]]))
    features = {
        "avg_assessment_score": float(np.mean(all_scores)),
        "score_trend": latest_checkpoint_average - first_checkpoint_average,
        "attendance_rate": (attendance.count("present") + 0.5 * attendance.count("late")) / len(attendance),
        "assignment_completion_rate": submitted_count / len(submitted),
    }
    return features, [], cutoff


def predict_support(features: dict) -> dict:
    bundle = get_support_bundle()
    feature_frame = pd.DataFrame([[features[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    pipeline = bundle["pipeline"]
    probability = float(pipeline.predict_proba(feature_frame)[0, 1])
    threshold = float(bundle["decision_threshold"])

    scaler = pipeline.named_steps["scale"]
    classifier = pipeline.named_steps["classifier"]
    standardized = scaler.transform(feature_frame)[0]
    contributions = standardized * classifier.coef_[0]
    explanations = []
    for index in np.argsort(np.abs(contributions))[::-1][:3]:
        column = FEATURE_COLUMNS[int(index)]
        label, unit, display_scale = FEATURE_LABELS[column]
        observed = float(features[column]) * display_scale
        baseline = float(scaler.mean_[index]) * display_scale
        contribution = float(contributions[index])
        direction = "raises" if contribution > 0.05 else "lowers" if contribution < -0.05 else "does not materially change"
        comparison = "above" if observed > baseline else "below" if observed < baseline else "at"
        explanations.append({
            "feature": column,
            "label": label,
            "observed_value": round(observed, 2),
            "training_average": round(baseline, 2),
            "unit": unit,
            "direction": direction,
            "log_odds_contribution": round(contribution, 4),
            "explanation": f"{label} is {comparison} the synthetic training average and {direction} the model's estimate. This is an association, not a cause.",
        })

    may_need_support = probability >= threshold
    return {
        "status": "ready",
        "may_need_support": may_need_support,
        "support_probability": round(probability, 4),
        "decision_threshold": threshold,
        "features": {key: round(float(value), 4) for key, value in features.items()},
        "explanations": explanations,
        "message": (
            "Consider a trainer review and discuss optional learning support."
            if may_need_support
            else "The model did not flag this learner; trainer judgment still applies."
        ),
        "notice": "Synthetic demonstration model only; the probability estimate is not calibrated on real learners. This signal assists trainer review and must not make placement or certification decisions.",
    }


def assign_learning_cluster(features: dict) -> dict:
    bundle = get_cluster_bundle()
    feature_frame = pd.DataFrame([[features[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    cluster_id = int(bundle["pipeline"].predict(feature_frame)[0])
    profile = bundle["metrics"]["centroids"][str(cluster_id)]
    return {
        "cluster_id": cluster_id,
        "cluster_size": bundle["metrics"]["cluster_sizes"][str(cluster_id)],
        "profile": profile,
        "notice": "Cluster IDs are arbitrary groupings of synthetic demonstration data, not learner quality ratings.",
    }
