"""Isolated contract tests for the FastAPI endpoints (stdlib unittest)."""

import unittest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import (
    Assessment,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    AttendanceRecord,
    Batch,
    Student,
    TrainerSubject,
    UserAccount,
)
from app.security.auth import hash_password


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.sessions = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)
        with cls.sessions() as db:
            db.add(Batch(
                batch_id="TEST-01", name="Test Cohort", program="Python",
                start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
                status="in_progress", data_origin="synthetic_demo",
            ))
            db.add(Batch(
                batch_id="TEST-02", name="Other Cohort", program="Analytics",
                start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
                status="completed", data_origin="synthetic_demo",
            ))
            db.add_all([
                Student(student_id="STU-A", batch_id="TEST-01", full_name="Avery Learner", enrollment_date=date(2026, 1, 1), is_active=True, data_origin="synthetic_demo"),
                Student(student_id="STU-B", batch_id="TEST-01", full_name="Blair Learner", enrollment_date=date(2026, 1, 1), is_active=False, data_origin="synthetic_demo"),
                Student(student_id="STU-C", batch_id="TEST-02", full_name="Casey Learner", enrollment_date=date(2025, 1, 1), is_active=True, data_origin="synthetic_demo"),
            ])
            db.add_all([
                Assessment(assessment_id="ASM-A", batch_id="TEST-01", title="Python basics", skill_area="Python", max_score=100, assessment_date=date(2026, 1, 10)),
                Assessment(assessment_id="ASM-B", batch_id="TEST-01", title="Python functions", skill_area="Python", max_score=50, assessment_date=date(2026, 2, 10)),
                Assessment(assessment_id="ASM-C1", batch_id="TEST-02", title="SQL basics", skill_area="SQL", max_score=100, assessment_date=date(2025, 1, 10)),
                Assessment(assessment_id="ASM-C2", batch_id="TEST-02", title="SQL joins", skill_area="SQL", max_score=100, assessment_date=date(2025, 2, 10)),
            ])
            db.add_all([
                AssessmentResult(result_id="RES-A1", student_id="STU-A", assessment_id="ASM-A", score=60),
                AssessmentResult(result_id="RES-A2", student_id="STU-A", assessment_id="ASM-B", score=40),
                AssessmentResult(result_id="RES-B1", student_id="STU-B", assessment_id="ASM-A", score=80),
                AssessmentResult(result_id="RES-C1", student_id="STU-C", assessment_id="ASM-C1", score=50),
                AssessmentResult(result_id="RES-C2", student_id="STU-C", assessment_id="ASM-C2", score=60),
            ])
            db.add_all([
                AttendanceRecord(attendance_id="ATT-A1", student_id="STU-A", session_date=date(2026, 1, 2), status="present"),
                AttendanceRecord(attendance_id="ATT-A2", student_id="STU-A", session_date=date(2026, 1, 3), status="late"),
            ])
            db.add_all([
                Assignment(assignment_id="TASK-PY", batch_id="TEST-01", title="Python practice", skill_area="Python", assigned_date=date(2026, 1, 5), due_date=date(2026, 2, 5)),
                Assignment(assignment_id="TASK-SQL", batch_id="TEST-01", title="SQL practice", skill_area="SQL", assigned_date=date(2026, 1, 6), due_date=date(2026, 2, 6)),
            ])
            db.add(AssignmentSubmission(submission_id="SUB-A-PY", student_id="STU-A", assignment_id="TASK-PY", submitted_at=date(2026, 1, 30), score=9))
            db.add_all([
                UserAccount(user_id="USR-ADMIN", username="admin", password_hash=hash_password("AdminTestPassword!23"), role="admin", is_active=True),
                UserAccount(user_id="USR-TRAINER", username="trainer", password_hash=hash_password("TrainerTestPassword!23"), role="trainer", is_active=True),
                UserAccount(user_id="USR-STUDENT-A", username="student-a", password_hash=hash_password("StudentATestPassword!23"), role="student", student_id="STU-A", is_active=True),
                UserAccount(user_id="USR-STUDENT-B", username="student-b", password_hash=hash_password("StudentBTestPassword!23"), role="student", student_id="STU-B", is_active=True),
            ])
            db.add(TrainerSubject(assignment_id="SUBJECT-PY", trainer_user_id="USR-TRAINER", skill_area="Python"))
            db.commit()

        def override_db():
            with cls.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        cls.client = TestClient(app)
        login = cls.client.post("/api/auth/login", json={"username": "admin", "password": "AdminTestPassword!23"})
        if login.status_code != 200:
            raise RuntimeError(f"Could not initialize authenticated API tests: {login.text}")
        cls.client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
        cls.trainer_client = TestClient(app)
        trainer_login = cls.trainer_client.post("/api/auth/login", json={"username": "trainer", "password": "TrainerTestPassword!23"})
        cls.trainer_client.headers.update({"Authorization": f"Bearer {trainer_login.json()['access_token']}"})
        cls.student_client = TestClient(app)
        student_login = cls.student_client.post("/api/auth/login", json={"username": "student-a", "password": "StudentATestPassword!23"})
        cls.student_client.headers.update({"Authorization": f"Bearer {student_login.json()['access_token']}"})
        cls.anonymous_client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)
        cls.engine.dispose()

    def test_health_and_batch_list(self):
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")
        response = self.client.get("/api/batches")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["batch_id"], "TEST-01")

    def test_csv_import_is_documented_as_raw_csv(self):
        openapi = self.client.get("/openapi.json").json()
        operation = openapi["paths"]["/api/assessments/{assessment_id}/results/import"]["post"]
        self.assertIn("text/csv", operation["requestBody"]["content"])

    def test_login_me_and_invalid_password(self):
        me = self.student_client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["role"], "student")
        self.assertEqual(me.json()["student_id"], "STU-A")
        invalid = self.anonymous_client.post("/api/auth/login", json={"username": "admin", "password": "wrong password"})
        self.assertEqual(invalid.status_code, 401)
        unknown = self.anonymous_client.post("/api/auth/login", json={"username": "missing", "password": "wrong password"})
        self.assertEqual(unknown.status_code, 401)

    def test_role_access_blocks_anonymous_and_limits_student_to_self(self):
        self.assertEqual(self.anonymous_client.get("/api/students").status_code, 401)
        self.assertEqual(self.student_client.get("/api/students?limit=10").status_code, 403)
        self.assertEqual(self.student_client.get("/api/analytics/overview").status_code, 403)
        self.assertEqual(self.student_client.get("/api/students/STU-A").status_code, 200)
        self.assertEqual(self.student_client.get("/api/students/STU-B").status_code, 403)
        self.assertEqual(self.student_client.get("/api/students/STU-A/recommendations").status_code, 200)
        self.assertEqual(self.student_client.get("/api/students/STU-B/recommendations").status_code, 403)
        self.assertEqual(self.student_client.get("/api/predictions/students/STU-A/support").status_code, 403)

    def test_admin_manages_accounts_and_trainer_cannot(self):
        payload = {"username": "new.trainer", "password": "NewTrainerPassword!23", "role": "trainer", "subject": "Python"}
        forbidden = self.trainer_client.post("/api/auth/users", json=payload)
        self.assertEqual(forbidden.status_code, 403)
        created = self.client.post("/api/auth/users", json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertNotIn("password", created.json())
        with self.sessions() as db:
            stored = db.get(UserAccount, created.json()["user_id"])
            self.assertTrue(stored.password_hash.startswith("$argon2"))
            self.assertNotEqual(stored.password_hash, payload["password"])
        duplicate = self.client.post("/api/auth/users", json=payload)
        self.assertEqual(duplicate.status_code, 409)
        invalid_student = self.client.post("/api/auth/users", json={
            "username": "unlinked.student", "password": "StudentPassword!234", "role": "student",
        })
        self.assertEqual(invalid_student.status_code, 422)

    def test_trainer_access_is_automatically_scoped_to_their_subject_batches(self):
        roster = self.trainer_client.get("/api/students?limit=10")
        self.assertEqual(roster.status_code, 200)
        self.assertEqual([row["student_id"] for row in roster.json()["items"]], ["STU-A", "STU-B"])

        detail = self.trainer_client.get("/api/students/STU-A")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual({item["skill_area"] for item in detail.json()["recent_assessments"]}, {"Python"})
        self.assertEqual(self.trainer_client.get("/api/students/STU-B").status_code, 200)
        scoped_recommendations = self.trainer_client.get("/api/students/STU-A/recommendations?benchmark=71")
        self.assertEqual(scoped_recommendations.status_code, 200)
        self.assertEqual([item["skill_area"] for item in scoped_recommendations.json()["recommendations"]], ["Python"])
        self.assertEqual(self.trainer_client.get("/api/students/STU-B/recommendations").status_code, 200)

        batches = self.trainer_client.get("/api/batches")
        self.assertEqual([batch["batch_id"] for batch in batches.json()], ["TEST-01"])
        assessments = self.trainer_client.get("/api/assessments")
        self.assertEqual({item["skill_area"] for item in assessments.json()}, {"Python"})
        gaps = self.trainer_client.get("/api/analytics/skill-gaps")
        self.assertEqual({item["skill_area"] for item in gaps.json()}, {"Python"})
        overview = self.trainer_client.get("/api/analytics/overview")
        self.assertEqual(overview.json()["active_learners"], 1)
        self.assertEqual(overview.json()["average_score"], 73.33)
        comparisons = self.trainer_client.get("/api/analytics/batch-comparison")
        self.assertEqual([row["batch_id"] for row in comparisons.json()], ["TEST-01"])
        self.assertEqual(comparisons.json()[0]["active_learners"], 1)
        trainer_assignments = self.trainer_client.get("/api/students/STU-A/assignments")
        self.assertEqual([row["assignment_id"] for row in trainer_assignments.json()], ["TASK-PY"])
        self.assertEqual(self.trainer_client.get("/api/predictions/model-metrics").status_code, 403)
        self.assertEqual(self.trainer_client.post("/api/assessments", json={}).status_code, 403)

    def test_trainer_cannot_access_another_subject_batch(self):
        self.assertEqual(self.trainer_client.get("/api/students/STU-C").status_code, 403)
        self.assertEqual(self.trainer_client.get("/api/students?limit=10&skill_area=SQL").status_code, 403)

    def test_student_sees_only_their_own_batch_assignments(self):
        assignments = self.student_client.get("/api/students/STU-A/assignments")
        self.assertEqual(assignments.status_code, 200)
        self.assertEqual({item["assignment_id"] for item in assignments.json()}, {"TASK-PY", "TASK-SQL"})
        self.assertEqual(self.student_client.get("/api/students/STU-B/assignments").status_code, 403)

    def test_student_activity_metrics_and_detail(self):
        response = self.client.get("/api/students?batch_id=TEST-01&limit=10")
        self.assertEqual(response.status_code, 200)
        learner = next(row for row in response.json()["items"] if row["student_id"] == "STU-A")
        self.assertEqual(learner["average_score"], 70.0)
        self.assertEqual(learner["score_trend"], 20.0)
        self.assertEqual(learner["attendance_rate"], 75.0)
        self.assertEqual(learner["assignment_completion_rate"], 100.0)
        detail = self.client.get("/api/students/STU-A")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["recent_assessments"]), 2)

    def test_assessment_summary_uses_normalized_scores_and_batch_size(self):
        response = self.client.get("/api/assessments?batch_id=TEST-01")
        self.assertEqual(response.status_code, 200)
        first = next(row for row in response.json() if row["assessment_id"] == "ASM-A")
        self.assertEqual(first["average_score"], 70.0)
        self.assertEqual(first["results_recorded"], 2)
        self.assertEqual(first["learner_count"], 2)

    def test_assessment_creation_checks_batch_dates(self):
        valid = self.client.post("/api/assessments", json={
            "batch_id": "TEST-01", "title": "New checkpoint", "skill_area": "Python",
            "assessment_date": "2026-03-01", "max_score": 50,
        })
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(valid.json()["max_score"], 50)
        outside_batch = self.client.post("/api/assessments", json={
            "batch_id": "TEST-01", "title": "Out of range", "skill_area": "Python",
            "assessment_date": "2027-03-01", "max_score": 100,
        })
        self.assertEqual(outside_batch.status_code, 422)

    def test_batch_and_result_validation(self):
        result = self.client.post("/api/assessments/ASM-A/results", json={"student_id": "STU-A", "score": 101})
        self.assertEqual(result.status_code, 422)
        wrong_batch = self.client.post("/api/assessments/ASM-B/results", json={"student_id": "NO-STUDENT", "score": 10})
        self.assertEqual(wrong_batch.status_code, 404)
        missing_batch = self.client.get("/api/students?batch_id=NO-BATCH")
        self.assertEqual(missing_batch.status_code, 404)

    def test_prediction_reports_insufficient_history_instead_of_guessing(self):
        response = self.client.get("/api/predictions/students/STU-B/support")
        self.assertEqual(response.status_code, 200)
        prediction = response.json()
        self.assertEqual(prediction["status"], "insufficient_data")
        self.assertIsNone(prediction["may_need_support"])
        self.assertIsNone(prediction["support_probability"])
        self.assertTrue(prediction["reasons"])

    def test_personalized_practice_suggestion_uses_skill_history_and_handles_sparse_data(self):
        response = self.client.get("/api/students/STU-C/recommendations")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["recommendations"][0]["skill_area"], "SQL")
        self.assertEqual(result["recommendations"][0]["average_score"], 55.0)
        self.assertIn("trainer", result["recommendations"][0]["suggestion"])
        self.assertIn("not generated by the prediction model", result["notice"])

        sparse = self.client.get("/api/students/STU-B/recommendations")
        self.assertEqual(sparse.status_code, 200)
        self.assertEqual(sparse.json()["status"], "insufficient_data")
        self.assertEqual(sparse.json()["recommendations"], [])

    def test_csv_score_import_is_validated_and_all_or_nothing(self):
        invalid = self.client.post(
            "/api/assessments/ASM-B/results/import",
            content="student_id,score\nSTU-B,35\nSTU-A,60\nSTU-C,20\n",
            headers={"Content-Type": "text/csv"},
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("No scores were imported", invalid.json()["detail"]["message"])
        self.assertTrue(any("not in this assessment's batch" in error for error in invalid.json()["detail"]["errors"]))
        with self.sessions() as db:
            self.assertIsNone(db.scalar(select(AssessmentResult.result_id).where(
                AssessmentResult.student_id == "STU-B", AssessmentResult.assessment_id == "ASM-B"
            )))

        valid = self.client.post(
            "/api/assessments/ASM-B/results/import",
            content="student_id,score\nSTU-B,35\nSTU-A,\n",
            headers={"Content-Type": "text/csv"},
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["imported_count"], 1)
        self.assertEqual(valid.json()["skipped_blank_scores"], 1)

        try:
            duplicate = self.client.post(
                "/api/assessments/ASM-B/results/import",
                content="student_id,score\nSTU-B,35\n",
                headers={"Content-Type": "text/csv"},
            )
            self.assertEqual(duplicate.status_code, 422)
        finally:
            with self.sessions() as db:
                imported = db.scalar(select(AssessmentResult).where(
                    AssessmentResult.student_id == "STU-B", AssessmentResult.assessment_id == "ASM-B"
                ))
                if imported:
                    db.delete(imported)
                    db.commit()


if __name__ == "__main__":
    unittest.main()
