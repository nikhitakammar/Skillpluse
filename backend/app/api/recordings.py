"""Recorded-class library for batches and training subjects."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Assessment, Batch, ClassRecording, Student, UserAccount
from app.schemas.recordings import RecordingCreate, RecordingRead
from app.security.auth import current_user, require_roles
from app.security.scopes import trainer_batch_ids, trainer_subjects

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=list[RecordingRead])
def list_recordings(
    batch_id: str | None = Query(default=None, max_length=20),
    user: UserAccount = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ClassRecording]:
    query = select(ClassRecording).where(ClassRecording.is_published.is_(True))
    if user.role == "student":
        learner = db.get(Student, user.student_id)
        if learner is None:
            return []
        query = query.where(ClassRecording.batch_id == learner.batch_id)
    elif user.role == "trainer":
        batch_ids = trainer_batch_ids(db, user) or set()
        query = query.where(
            ClassRecording.batch_id.in_(batch_ids),
            func.lower(ClassRecording.skill_area).in_(trainer_subjects(user)),
        )
    if batch_id:
        query = query.where(ClassRecording.batch_id == batch_id)
    return list(db.scalars(query.order_by(ClassRecording.recorded_on.desc(), ClassRecording.title)))


@router.post("", response_model=RecordingRead, status_code=status.HTTP_201_CREATED)
def create_recording(
    payload: RecordingCreate,
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> ClassRecording:
    if db.get(Batch, payload.batch_id) is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if user.role == "trainer":
        assigned = set(db.scalars(trainer_subjects(user)).all())
        batch_ids = trainer_batch_ids(db, user) or set()
        if payload.skill_area.casefold() not in assigned or payload.batch_id not in batch_ids:
            raise HTTPException(status_code=403, detail="You can publish recordings only for your assigned subject and batches")
    recording = ClassRecording(
        recording_id=str(uuid4()), batch_id=payload.batch_id, skill_area=payload.skill_area.strip(),
        title=payload.title.strip(), recorded_on=payload.recorded_on,
        duration_minutes=payload.duration_minutes, recording_url=str(payload.recording_url),
        is_published=payload.is_published, data_origin="manual",
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    return recording
