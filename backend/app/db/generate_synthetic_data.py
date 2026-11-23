"""Generate a reproducible, fictional training dataset and ML snapshots."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261123
STUDENTS_PER_BATCH = 30
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"
SKILLS = ["Python", "SQL", "Problem Solving", "Communication"]
FIRST_NAMES = [
    "Aarav", "Aditi", "Akash", "Anaya", "Arjun", "Diya", "Ishaan", "Kavya",
    "Meera", "Neel", "Nisha", "Pranav", "Riya", "Rohan", "Sara", "Vihaan",
]
LAST_NAMES = [
    "Bose", "Chandra", "Desai", "Gupta", "Iyer", "Kapoor", "Khan", "Kulkarni",
    "Menon", "Nair", "Patel", "Rao", "Shah", "Sharma", "Singh", "Verma",
]
BATCHES = [
    ("BATCH-01", "Python Foundations · Jan 2025", "Python Development", date(2025, 1, 6)),
    ("BATCH-02", "Data Analytics · Jan 2025", "Data Analytics", date(2025, 1, 6)),
    ("BATCH-03", "Web Development · Feb 2025", "Web Development", date(2025, 2, 3)),
    ("BATCH-04", "QA Engineering · Feb 2025", "QA Engineering", date(2025, 2, 3)),
]
ASSESSMENT_WEEKS = [0, 2, 4, 6]
ATTENDANCE_WEEKS = list(range(1, 8))
ASSIGNMENT_WEEKS = [1, 3, 5, 6]
SNAPSHOT_OFFSET_DAYS = 54
OUTCOME_OFFSET_DAYS = 82


def write_csv(name: str, records: list[dict]) -> None:
    pd.DataFrame.from_records(records).to_csv(OUTPUT_DIR / name, index=False)


def sigmoid(value: float) -> float:
    return float(1 / (1 + np.exp(-value)))


def generate() -> None:
    rng = np.random.default_rng(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    batch_rows = []
    student_rows = []
    assessment_rows = []
    result_rows = []
    attendance_rows = []
    assignment_rows = []
    submission_rows = []
    outcome_rows = []
    snapshot_rows = []
    student_factors = {}

    for batch_index, (batch_id, batch_name, program, start_date) in enumerate(BATCHES):
        batch_rows.append({
            "batch_id": batch_id,
            "name": batch_name,
            "program": program,
            "start_date": start_date,
            "end_date": start_date + timedelta(days=77),
            "status": "completed",
            "data_origin": "synthetic_demo",
        })

        batch_students = []
        skill_offsets = {}
        checkpoint_scores = {}
        for local_index in range(STUDENTS_PER_BATCH):
            student_number = batch_index * STUDENTS_PER_BATCH + local_index + 1
            student_id = f"STU-{student_number:03d}"
            first_name = FIRST_NAMES[(student_number * 7 + batch_index) % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(student_number * 11 + batch_index * 3) % len(LAST_NAMES)]
            ability = float(np.clip(rng.normal(0.66 - batch_index * 0.015, 0.15), 0.25, 0.95))
            engagement = float(np.clip(rng.beta(5, 2), 0.2, 0.99))
            growth = float(rng.normal(0.012, 0.009))
            student_factors[student_id] = (ability, engagement, growth)
            skill_offsets[student_id] = rng.normal(0, 0.07, size=len(SKILLS))
            checkpoint_scores[student_id] = {index: [] for index in range(len(ASSESSMENT_WEEKS))}
            student_rows.append({
                "student_id": student_id,
                "batch_id": batch_id,
                "full_name": f"{first_name} {last_name}",
                "enrollment_date": start_date,
                "is_active": True,
                "data_origin": "synthetic_demo",
            })
            batch_students.append(student_id)

        for checkpoint_index, week in enumerate(ASSESSMENT_WEEKS):
            assessment_date = start_date + timedelta(weeks=week)
            for skill_index, skill in enumerate(SKILLS):
                assessment_id = f"ASM-{batch_index + 1:02d}-{checkpoint_index + 1:02d}-{skill_index + 1:02d}"
                assessment_rows.append({
                    "assessment_id": assessment_id,
                    "batch_id": batch_id,
                    "title": f"{skill} Checkpoint {checkpoint_index + 1}",
                    "skill_area": skill,
                    "max_score": 100,
                    "assessment_date": assessment_date,
                })
                for student_id in batch_students:
                    ability, _engagement, growth = student_factors[student_id]
                    score_fraction = np.clip(
                        ability + skill_offsets[student_id][skill_index] + growth * checkpoint_index + rng.normal(0, 0.10),
                        0.20,
                        0.99,
                    )
                    score = round(float(score_fraction * 100), 1)
                    result_rows.append({
                        "result_id": f"RES-{student_id}-{checkpoint_index + 1:02d}-{skill_index + 1:02d}",
                        "student_id": student_id,
                        "assessment_id": assessment_id,
                        "score": score,
                    })
                    checkpoint_scores[student_id][checkpoint_index].append(score)

        session_dates = [start_date + timedelta(weeks=week, days=3) for week in ATTENDANCE_WEEKS]
        for session_index, session_date in enumerate(session_dates, start=1):
            for student_id in batch_students:
                _ability, engagement, _growth = student_factors[student_id]
                p_present = 0.55 + 0.40 * engagement
                p_late = 0.04 + 0.04 * (1 - engagement)
                status = str(rng.choice(["present", "late", "absent"], p=[p_present, p_late, 1 - p_present - p_late]))
                attendance_rows.append({
                    "attendance_id": f"ATT-{student_id}-{session_index:02d}",
                    "student_id": student_id,
                    "session_date": session_date,
                    "status": status,
                })

        for assignment_index, week in enumerate(ASSIGNMENT_WEEKS, start=1):
            assignment_id = f"ASN-{batch_index + 1:02d}-{assignment_index:02d}"
            assigned_date = start_date + timedelta(weeks=week)
            due_date = assigned_date + timedelta(days=7)
            assignment_rows.append({
                "assignment_id": assignment_id,
                "batch_id": batch_id,
                "title": f"{SKILLS[assignment_index - 1]} Practice {assignment_index}",
                "skill_area": SKILLS[assignment_index - 1],
                "assigned_date": assigned_date,
                "due_date": due_date,
            })
            for student_id in batch_students:
                ability, engagement, _growth = student_factors[student_id]
                completed = bool(rng.random() < 0.52 + 0.45 * engagement)
                submitted_at = None
                score = None
                if completed:
                    is_late = bool(rng.random() < 0.12 + 0.20 * (1 - engagement))
                    submitted_at = due_date + timedelta(days=int(rng.integers(1, 4))) if is_late else due_date - timedelta(days=int(rng.integers(0, 4)))
                    score = round(float(np.clip((ability + rng.normal(0.02, 0.12)) * 100, 20, 100)), 1)
                submission_rows.append({
                    "submission_id": f"SUB-{student_id}-{assignment_index:02d}",
                    "student_id": student_id,
                    "assignment_id": assignment_id,
                    "submitted_at": submitted_at,
                    "score": score,
                })

        snapshot_date = start_date + timedelta(days=SNAPSHOT_OFFSET_DAYS)
        outcome_date = start_date + timedelta(days=OUTCOME_OFFSET_DAYS)
        for student_id in batch_students:
            ability, engagement, growth = student_factors[student_id]
            student_results = [row["score"] for row in result_rows if row["student_id"] == student_id]
            student_attendance = [row["status"] for row in attendance_rows if row["student_id"] == student_id]
            student_submissions = [row["submitted_at"] for row in submission_rows if row["student_id"] == student_id]
            avg_score = float(np.mean(student_results))
            first_checkpoint_average = np.mean(checkpoint_scores[student_id][0])
            latest_checkpoint_average = np.mean(checkpoint_scores[student_id][len(ASSESSMENT_WEEKS) - 1])
            trend = float(latest_checkpoint_average - first_checkpoint_average)
            attendance_rate = (student_attendance.count("present") + 0.5 * student_attendance.count("late")) / len(student_attendance)
            completion_rate = sum(value is not None for value in student_submissions) / len(student_submissions)
            probability = sigmoid(6.5 * (0.54 - ability + 0.15 * (0.72 - engagement) - 0.10 * growth))
            needs_support = int(rng.random() < probability)
            outcome_id = f"OUT-{student_id}"
            outcome_rows.append({
                "outcome_id": outcome_id,
                "student_id": student_id,
                "snapshot_date": snapshot_date,
                "outcome_date": outcome_date,
                "needs_support": needs_support,
                "data_origin": "synthetic_demo",
            })
            snapshot_rows.append({
                "snapshot_id": f"SNAP-{student_id}",
                "student_id": student_id,
                "snapshot_date": snapshot_date,
                "avg_assessment_score": round(avg_score, 2),
                "score_trend": round(trend, 2),
                "attendance_rate": round(attendance_rate, 3),
                "assignment_completion_rate": round(completion_rate, 3),
                "needed_support": needs_support,
                "outcome_date": outcome_date,
                "data_origin": "synthetic_demo",
            })

    csv_files = {
        "batches.csv": batch_rows,
        "students.csv": student_rows,
        "assessments.csv": assessment_rows,
        "assessment_results.csv": result_rows,
        "attendance_records.csv": attendance_rows,
        "assignments.csv": assignment_rows,
        "assignment_submissions.csv": submission_rows,
        "support_outcomes.csv": outcome_rows,
        "model_snapshots.csv": snapshot_rows,
    }
    for filename, rows in csv_files.items():
        write_csv(filename, rows)

    positive_count = sum(row["needed_support"] for row in snapshot_rows)
    print(f"Generated {len(student_rows)} fictional students in {len(batch_rows)} batches at {OUTPUT_DIR}")
    print(f"Synthetic follow-up labels: {positive_count} need-support, {len(snapshot_rows) - positive_count} on-track")
    print(f"Reproducible seed: {SEED}")


if __name__ == "__main__":
    generate()
