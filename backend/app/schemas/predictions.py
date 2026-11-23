"""API response models for synthetic model evaluation and inference."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class SupportMetrics(BaseModel):
    model: str
    data_origin: str
    sample_count: int
    train_sample_count: int
    test_sample_count: int
    positive_label: str
    class_counts: dict[str, dict[str, int]]
    feature_columns: list[str]
    decision_threshold: float
    metrics: dict[str, float]
    confusion_matrix: dict[str, list]
    split: str
    scikit_learn_version: str
    dataset_sha256: str
    trained_at_utc: str
    notice: str


class FeatureExplanation(BaseModel):
    feature: str
    label: str
    observed_value: float
    training_average: float
    unit: str
    direction: str
    log_odds_contribution: float
    explanation: str


class StudentSupportPrediction(BaseModel):
    student_id: str
    status: Literal["ready", "insufficient_data"]
    feature_cutoff_date: date
    may_need_support: bool | None
    support_probability: float | None
    decision_threshold: float | None
    features: dict[str, float] | None
    explanations: list[FeatureExplanation]
    reasons: list[str]
    message: str
    notice: str


class ClusterMetrics(BaseModel):
    model: str
    data_origin: str
    sample_count: int
    feature_columns: list[str]
    cluster_count: int
    cluster_sizes: dict[str, int]
    centroids: dict[str, dict[str, float]]
    silhouette_score: float
    scikit_learn_version: str
    dataset_sha256: str
    notice: str


class StudentCluster(BaseModel):
    student_id: str
    status: Literal["ready", "insufficient_data"]
    cluster_id: int | None
    cluster_size: int | None
    profile: dict[str, float] | None
    reasons: list[str]
    notice: str
