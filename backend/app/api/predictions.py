"""Trainer-assist predictions and unsupervised learner groupings."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.ml.inference import (
    ModelUnavailable,
    assign_learning_cluster,
    get_cluster_metrics,
    get_support_metrics,
    historical_features,
    predict_support,
)
from app.models import Student
from app.schemas.predictions import (
    ClusterMetrics,
    StudentCluster,
    StudentSupportPrediction,
    SupportMetrics,
)
from app.security.auth import require_roles

router = APIRouter(prefix="/predictions", tags=["AI support tools"], dependencies=[Depends(require_roles("admin"))])

SUPPORT_NOTICE = (
    "Synthetic demonstration model only; the probability estimate is not calibrated on real learners. This signal assists trainer review and must not make placement or certification decisions."
)
CLUSTER_NOTICE = "Cluster IDs are arbitrary groupings of synthetic demonstration data, not learner quality ratings."


@router.get("/model-metrics", response_model=SupportMetrics)
def support_model_metrics() -> dict:
    try:
        return get_support_metrics()
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/cluster-metrics", response_model=ClusterMetrics)
def learning_cluster_metrics() -> dict:
    try:
        return get_cluster_metrics()
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/students/{student_id}/support", response_model=StudentSupportPrediction)
def support_prediction(student_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    features, reasons, cutoff = historical_features(db, student_id)
    if reasons:
        return {
            "student_id": student_id,
            "status": "insufficient_data",
            "feature_cutoff_date": cutoff,
            "may_need_support": None,
            "support_probability": None,
            "decision_threshold": None,
            "features": None,
            "explanations": [],
            "reasons": reasons,
            "message": "There is not enough historical assessment, attendance and assignment data to estimate a support signal.",
            "notice": SUPPORT_NOTICE,
        }
    try:
        prediction = predict_support(features)
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {
        "student_id": student_id,
        "feature_cutoff_date": cutoff,
        "reasons": [],
        **prediction,
    }


@router.get("/students/{student_id}/learning-cluster", response_model=StudentCluster)
def student_learning_cluster(student_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    features, reasons, _cutoff = historical_features(db, student_id)
    if reasons:
        return {
            "student_id": student_id,
            "status": "insufficient_data",
            "cluster_id": None,
            "cluster_size": None,
            "profile": None,
            "reasons": reasons,
            "notice": CLUSTER_NOTICE,
        }
    try:
        cluster = assign_learning_cluster(features)
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"student_id": student_id, "status": "ready", "reasons": [], **cluster}
