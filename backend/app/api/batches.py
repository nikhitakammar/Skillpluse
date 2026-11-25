"""Read endpoints for training batches."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Batch, UserAccount
from app.schemas.batches import BatchRead
from app.security.auth import require_roles
from app.security.scopes import trainer_batch_ids

router = APIRouter(prefix="/batches", tags=["batches"], dependencies=[Depends(require_roles("admin", "trainer"))])


@router.get("", response_model=list[BatchRead])
def list_batches(
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> list[Batch]:
    query = select(Batch)
    allowed = trainer_batch_ids(db, user)
    if allowed is not None:
        query = query.where(Batch.batch_id.in_(allowed))
    return list(db.scalars(query.order_by(Batch.start_date.desc(), Batch.name)))


@router.get("/{batch_id}", response_model=BatchRead)
def get_batch(
    batch_id: str,
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> Batch:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    allowed = trainer_batch_ids(db, user)
    if allowed is not None and batch_id not in allowed:
        raise HTTPException(status_code=403, detail="This trainer is not assigned to the batch")
    return batch
