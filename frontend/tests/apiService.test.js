import test from 'node:test'
import assert from 'node:assert/strict'
import { createAssessment, fetchDashboardData, fetchLearnerInsights, importAssessmentScores } from '../src/services/api.js'

test('dashboard API payloads map backend fields into the view model', async () => {
  const originalFetch = globalThis.fetch
  const batch = { batch_id: 'BATCH-01', name: 'Python · Jan 2026', program: 'Python', start_date: '2026-01-01', end_date: '2026-12-31', status: 'in_progress', data_origin: 'synthetic_demo' }
  const student = { student_id: 'STU-1', batch_id: 'BATCH-01', full_name: 'Alex Learner', enrollment_date: '2026-01-01', is_active: true, data_origin: 'synthetic_demo', average_score: 68, score_trend: 4, attendance_rate: 90, assignment_completion_rate: 80 }
  globalThis.fetch = async (url) => {
    const path = new URL(url, 'http://localhost').pathname + new URL(url, 'http://localhost').search
    const payloads = {
      '/api/batches': [batch],
      '/api/analytics/batch-comparison': [{ batch_id: 'BATCH-01', name: batch.name, active_learners: 1, average_score: 68, attendance_rate: 90, assignment_completion_rate: 80 }],
      '/api/analytics/overview': { active_learners: 1, total_batches: 1, average_score: 68, attendance_rate: 90, assignment_completion_rate: 80 },
      '/api/students?limit=100&offset=0': { items: [student], total: 1, limit: 100, offset: 0 },
      '/api/assessments': [{ assessment_id: 'ASM-1', batch_id: 'BATCH-01', title: 'Functions', skill_area: 'Python', assessment_date: '2026-02-01', average_score: 68, results_recorded: 1, learner_count: 1 }],
      '/api/predictions/model-metrics': { metrics: { precision: 0.8 }, confusion_matrix: { values: [[2, 0], [1, 2]] } },
      '/api/analytics/performance-trend': [{ assessment_date: '2026-02-01', average_score: 68 }],
      '/api/analytics/skill-gaps': [{ skill_area: 'Python', average_score: 68, learners_below_benchmark: 1, benchmark: 70 }],
      '/api/analytics/performance-trend?batch_id=BATCH-01': [{ assessment_date: '2026-02-01', average_score: 68 }],
      '/api/analytics/skill-gaps?batch_id=BATCH-01': [{ skill_area: 'Python', average_score: 68, learners_below_benchmark: 1, benchmark: 70 }],
    }
    if (!(path in payloads)) throw new Error(`Unexpected request: ${path}`)
    return { ok: true, json: async () => payloads[path] }
  }

  try {
    const data = await fetchDashboardData()
    assert.equal(data.dataSource, 'api')
    assert.equal(data.students[0].studentId, 'STU-1')
    assert.equal(data.students[0].completionRate, 80)
    assert.equal(data.assessments[0].submittedCount, 1)
    assert.equal(data.trends.filter((point) => point.batchId === 'all').length, 1)
    assert.equal(data.skills.find((skill) => skill.batchId === 'BATCH-01').learnersBelowBenchmark, 1)
    assert.equal(data.summary.averageScore, 68)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('score CSV import sends raw CSV and reports API validation errors', async () => {
  const originalFetch = globalThis.fetch
  const originalStorage = globalThis.sessionStorage
  globalThis.sessionStorage = { getItem: () => 'demo-token' }
  let capturedRequest
  globalThis.fetch = async (url, options) => {
    capturedRequest = { url, options }
    return { ok: true, json: async () => ({ imported_count: 2, skipped_blank_scores: 0 }) }
  }
  try {
    const imported = await importAssessmentScores('ASM-1', 'student_id,score\nSTU-1,80\n')
    assert.equal(imported.imported_count, 2)
    assert.equal(capturedRequest.url, '/api/assessments/ASM-1/results/import')
    assert.equal(capturedRequest.options.headers['Content-Type'], 'text/csv; charset=utf-8')
    assert.equal(capturedRequest.options.headers.Authorization, 'Bearer demo-token')
    assert.match(capturedRequest.options.body, /STU-1,80/)

    globalThis.fetch = async () => ({ ok: false, status: 422, json: async () => ({ detail: { message: 'No scores were imported.', errors: ['Row 2: invalid score'] } }) })
    await assert.rejects(() => importAssessmentScores('ASM-1', 'student_id,score\nSTU-1,bad'), /Row 2: invalid score/)
  } finally {
    globalThis.fetch = originalFetch
    if (originalStorage === undefined) delete globalThis.sessionStorage
    else globalThis.sessionStorage = originalStorage
  }
})

test('assessment creation sends validated form fields as JSON', async () => {
  const originalFetch = globalThis.fetch
  let captured
  globalThis.fetch = async (url, options) => {
    captured = { url, options }
    return { ok: true, json: async () => ({ assessment_id: 'ASM-NEW', title: 'Checkpoint' }) }
  }
  try {
    const result = await createAssessment({ batch_id: 'BATCH-01', title: 'Checkpoint', skill_area: 'Python', assessment_date: '2026-01-01', max_score: 50 })
    assert.equal(result.assessment_id, 'ASM-NEW')
    assert.equal(captured.url, '/api/assessments')
    assert.equal(captured.options.method, 'POST')
    assert.deepEqual(JSON.parse(captured.options.body), { batch_id: 'BATCH-01', title: 'Checkpoint', skill_area: 'Python', assessment_date: '2026-01-01', max_score: 50 })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('learner insight requests include score-based practice suggestions', async () => {
  const originalFetch = globalThis.fetch
  const urls = []
  globalThis.fetch = async (url) => {
    urls.push(url)
    return { ok: true, json: async () => ({ recommendations: [{ skill_area: 'SQL', average_score: 55, suggestion: 'Practice joins.' }] }) }
  }
  try {
    const insights = await fetchLearnerInsights('STU/1')
    assert.equal(insights.recommendations.recommendations[0].skill_area, 'SQL')
    assert.ok(urls.includes('/api/students/STU%2F1/recommendations'))
  } finally {
    globalThis.fetch = originalFetch
  }
})
