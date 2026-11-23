# Synthetic demonstration data

Every person, score, attendance record, assignment and support outcome in this folder is fictional and generated for software demonstration. Do not treat these values as real student records or evidence of model performance on real learners.

Regenerate the CSV files from `backend/` with:

```powershell
python -m app.db.generate_synthetic_data
```

The generator uses NumPy seed `20261123`, so repeated runs produce the same records. It creates four training batches with 30 fictional learners each, 16 assessment results per learner (four skill areas at four checkpoints), four assignments per learner, seven attendance sessions, and a follow-up support label.

`model_snapshots.csv` is an ML-ready demonstration table. Its score average, score trend, attendance rate and assignment completion rate describe activity up to `snapshot_date`. `needed_support` and `outcome_date` are follow-up labels dated after that snapshot. Future model training must select only the four historical feature columns and the label; `student_id`, dates and `data_origin` are identifiers/metadata, not model features. These synthetic labels are illustrative and do not represent validated educational outcomes.

## CSV files

- `batches.csv`, `students.csv`: fictional cohort and learner records.
- `assessments.csv`, `assessment_results.csv`: assessment definitions and scores.
- `attendance_records.csv`: dated present, late or absent status.
- `assignments.csv`, `assignment_submissions.csv`: assignment definitions and completion/score records; a blank submission date means not submitted.
- `support_outcomes.csv`: separate follow-up labels, recorded after the snapshot date.
- `model_snapshots.csv`: pre-outcome features joined to a later synthetic label for future ML exercises.
