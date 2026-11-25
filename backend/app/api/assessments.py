"""Assessment browsing, creation, score entry and CSV imports."""

import csv
import io
import math
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Assessment, AssessmentResult, Batch, Student, UserAccount
from app.schemas.assessments import AssessmentCreate, AssessmentRead, AssessmentSummary, ResultCreate, ResultImportSummary, ResultRead
from app.security.auth import require_roles
from app.security.scopes import trainer_batch_skill_scope

router = APIRouter(prefix="/assessments", tags=["assessments"], dependencies=[Depends(require_roles("admin", "trainer"))])
MAX_IMPORT_BYTES = 2_000_000
MAX_IMPORT_ROWS = 1_000


@router.get("", response_model=list[AssessmentSummary])
def list_assessments(
    batch_id: str | None = Query(default=None, max_length=20),
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> list[AssessmentSummary]:
    query = select(Assessment, func.avg(AssessmentResult.score / Assessment.max_score * 100), func.count(AssessmentResult.result_id))
    query = query.outerjoin(AssessmentResult, AssessmentResult.assessment_id == Assessment.assessment_id)
    query = trainer_batch_skill_scope(query, user, Assessment.batch_id, Assessment.skill_area)
    if batch_id:
        if db.get(Batch, batch_id) is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        query = query.where(Assessment.batch_id == batch_id)
    query = query.group_by(Assessment.assessment_id).order_by(Assessment.assessment_date, Assessment.title)
    result = []
    for assessment, average, recorded in db.execute(query):
        learners = db.scalar(select(func.count(Student.student_id)).where(Student.batch_id == assessment.batch_id)) or 0
        result.append(AssessmentSummary(
            assessment_id=assessment.assessment_id, batch_id=assessment.batch_id, title=assessment.title,
            skill_area=assessment.skill_area, max_score=assessment.max_score, assessment_date=assessment.assessment_date,
            average_score=round(float(average), 2) if average is not None else None, results_recorded=recorded, learner_count=learners,
        ))
    return result


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: AssessmentCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Assessment:
    batch = db.get(Batch, payload.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if not batch.start_date <= payload.assessment_date <= batch.end_date:
        raise HTTPException(status_code=422, detail="Assessment date must fall within the batch dates")

    assessment = Assessment(
        assessment_id=f"ASM-{uuid4().hex[:10].upper()}",
        batch_id=payload.batch_id,
        title=payload.title.strip(),
        skill_area=payload.skill_area.strip(),
        max_score=payload.max_score,
        assessment_date=payload.assessment_date,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/results", response_model=ResultRead, status_code=status.HTTP_201_CREATED)
def create_assessment_result(
    assessment_id: str,
    payload: ResultCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> AssessmentResult:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.batch_id != assessment.batch_id:
        raise HTTPException(status_code=422, detail="Student and assessment must belong to the same batch")
    if payload.score > assessment.max_score:
        raise HTTPException(status_code=422, detail="Score cannot exceed the assessment maximum")
    existing = db.scalar(
        select(AssessmentResult).where(
            AssessmentResult.student_id == student.student_id,
            AssessmentResult.assessment_id == assessment.assessment_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="A result already exists for this student and assessment")

    result = AssessmentResult(
        result_id=f"RES-{uuid4().hex[:12].upper()}",
        student_id=student.student_id,
        assessment_id=assessment.assessment_id,
        score=payload.score,
    )
    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A result already exists for this student and assessment") from None
    db.refresh(result)
    return result


@router.post(
    "/{assessment_id}/results/import",
    response_model=ResultImportSummary,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "text/csv": {
                    "schema": {"type": "string"},
                    "example": "student_id,score\nSTU-100,82",
                }
            },
        }
    },
)
async def import_assessment_results(
    assessment_id: str,
    request: Request,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> ResultImportSummary:
    """Import score rows from UTF-8 CSV; validation is all-or-nothing."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="CSV file is empty")
    if len(body) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="CSV file must be 2 MB or smaller")
    try:
        content = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="CSV must use UTF-8 text encoding") from None

    reader = csv.DictReader(io.StringIO(content, newline=""))
    source_headers = reader.fieldnames or []
    headers = [header.strip().lower() for header in source_headers]
    if len(headers) != 2 or set(headers) != {"student_id", "score"}:
        raise HTTPException(status_code=422, detail="CSV must have exactly these columns: student_id,score")

    source_rows = []
    too_many_rows = False
    try:
        for source_row in reader:
            if len(source_rows) >= MAX_IMPORT_ROWS:
                too_many_rows = True
                break
            source_rows.append(source_row)
    except csv.Error:
        raise HTTPException(status_code=422, detail="CSV contains a malformed or excessively long field") from None
    if too_many_rows:
        raise HTTPException(status_code=422, detail=f"CSV may contain at most {MAX_IMPORT_ROWS} data rows")

    errors: list[str] = []
    rows: list[tuple[int, str, float]] = []
    seen_student_ids: set[str] = set()
    skipped_blank_scores = 0
    for row_number, source_row in enumerate(source_rows, start=2):
        if None in source_row:
            errors.append(f"Row {row_number}: too many columns")
            continue
        row = {normalized: source_row.get(original) for original, normalized in zip(source_headers, headers)}
        student_id = (row.get(headers[0]) or "").strip()
        score_text = (row.get(headers[1]) or "").strip()
        if not student_id and not score_text:
            continue
        if not score_text:
            skipped_blank_scores += 1
            continue
        if not student_id:
            errors.append(f"Row {row_number}: student_id is required when score is provided")
            continue
        if student_id in seen_student_ids:
            errors.append(f"Row {row_number}: duplicate student_id {student_id} in CSV")
            continue
        seen_student_ids.add(student_id)

        try:
            score = float(score_text)
        except ValueError:
            errors.append(f"Row {row_number}: score must be a number")
            continue
        if not math.isfinite(score) or score < 0 or score > assessment.max_score:
            errors.append(f"Row {row_number}: score must be between 0 and {assessment.max_score:g}")
            continue

        student = db.get(Student, student_id)
        if student is None:
            errors.append(f"Row {row_number}: student {student_id} was not found")
            continue
        if student.batch_id != assessment.batch_id:
            errors.append(f"Row {row_number}: student {student_id} is not in this assessment's batch")
            continue
        existing = db.scalar(select(AssessmentResult.result_id).where(
            AssessmentResult.student_id == student_id,
            AssessmentResult.assessment_id == assessment_id,
        ))
        if existing is not None:
            errors.append(f"Row {row_number}: a result already exists for student {student_id}")
            continue
        rows.append((row_number, student_id, score))

    if errors:
        raise HTTPException(status_code=422, detail={"message": "No scores were imported. Fix the CSV errors and try again.", "errors": errors})
    if not rows:
        raise HTTPException(status_code=422, detail="CSV contains no scores to import")

    db.add_all([
        AssessmentResult(
            result_id=f"RES-{uuid4().hex[:12].upper()}",
            student_id=student_id,
            assessment_id=assessment_id,
            score=score,
        )
        for _row_number, student_id, score in rows
    ])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A score changed during import. Refresh the assessment and try again.") from None

    return ResultImportSummary(
        assessment_id=assessment_id,
        imported_count=len(rows),
        skipped_blank_scores=skipped_blank_scores,
    )
