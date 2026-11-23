# Phase 6: React dashboard

The frontend now has an interactive manager/trainer dashboard built with React, Vite and Recharts. `frontend/src/data/demoData.json` is an offline snapshot derived from the generated synthetic CSVs and synthetic model evaluation. The UI clearly labels that snapshot and does not call the API yet; live integration is Phase 7.

## Dashboard views

- **Overview:** summary cards, assessment trend, batch score comparison, skill focus and a benchmark-based review list.
- **Learners:** search by name or ID, filter active status, paginate the roster, and open a sample learner profile.
- **Assessments:** search and paginate the assessment results.
- **Skill gaps:** compare average scores and below-benchmark counts by skill.
- **Reports:** compare batches, inspect the synthetic support-model confusion matrix, and export the visible batch report to CSV.

The global batch selector affects the overview, learner roster, assessment list, skill analysis and batch report. The overview chart has an all-checkpoints/recent-two filter. The review list is based only on a 70% descriptive score benchmark; it is not a prediction. Individual model predictions are left to the API integration phase.

## Important files

- `frontend/src/App.jsx` owns navigation, global filters and view-level data selection.
- `frontend/src/components/` contains the reusable sidebar, metric cards and headings.
- `frontend/src/pages/` contains each dashboard view.
- `frontend/src/data/demoData.json` contains the synthetic UI snapshot; it excludes student outcome labels.
- `frontend/src/styles/global.css` contains responsive page, table, chart and modal styles.

Run `npm.cmd run dev` from `frontend/` to open the local dashboard and `npm.cmd run build` to create production assets. Page components are lazy-loaded so the entry bundle does not include every dashboard view at once.

Run `npm.cmd test` from `frontend/` for the dependency-free dashboard data tests. They cover global batch and checkpoint selection, learner/assessment search, status filtering, pagination, CSV escaping, and keeping future support labels out of the learner UI fixture.
