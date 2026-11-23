# Phase 5: Machine learning

## Support model

`python -m app.ml.train` reads `data/synthetic/model_snapshots.csv` and trains Logistic Regression. The feature allowlist is limited to average assessment score, score trend, attendance rate, and assignment completion rate. Student IDs, dates, data-origin markers, and `needed_support` are never inputs. Training stops when there are fewer than 40 complete snapshots, fewer than eight examples of either outcome, repeated snapshots for the same learner, invalid dates, or invalid feature values.

The script performs a reproducible stratified 75/25 train/test split. `StandardScaler` and Logistic Regression are kept in one pipeline; the pipeline is fit on the training rows only, then evaluated once on the held-out test rows. The report includes precision, recall, F1-score, and a confusion matrix for `on_track (0)` and `needs_support (1)`.

The current synthetic run used 90 train rows and 30 test rows. Its held-out precision is 0.7143, recall 0.4167, and F1-score 0.5263; confusion matrix rows are actual labels and columns are predicted labels: `[[16, 2], [7, 5]]`. This small synthetic result misses some support outcomes and is not evidence of real-world model quality. The 0.5 probability threshold is a demonstration default, not an operationally validated cutoff, and the probability estimate is not calibrated on real learners.

## Inference and explanations

Student predictions aggregate only dated assessment results, attendance and assignment submissions through the current date. The API never reads `support_outcomes` to make a prediction. It returns the estimated probability, the thresholded support signal, and the three strongest coefficient contributions relative to the training feature averages. Explanations describe associations, not causes.

If a learner has fewer than two dated assessment checkpoints, fewer than two attendance sessions, or no assigned task, the endpoint returns `insufficient_data` with no estimate. An absent, stale, or incompatible model artifact returns HTTP 503 with retraining instructions.

## K-Means groups

The same four historical features are standardized and passed to K-Means with three clusters. The target label is not used. The API reports cluster sizes, feature centroids and silhouette score; cluster IDs are arbitrary descriptive groupings, not rankings or learner-quality ratings. The current synthetic silhouette score is about 0.21, so these groups overlap and should be treated as exploratory.

## Routes

- `GET /api/predictions/model-metrics` returns the held-out Logistic Regression report.
- `GET /api/predictions/students/{student_id}/support` returns a trainer-assist estimate or an insufficient-data response.
- `GET /api/predictions/cluster-metrics` reports the K-Means fit.
- `GET /api/predictions/students/{student_id}/learning-cluster` assigns a learner to a descriptive cluster.

Every AI response identifies the model as synthetic demonstration data. Predictions assist trainers; they must not make placement or certification decisions.
