import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  buildBatchReportCsv,
  filterAssessmentRows,
  filterStudentRows,
  getDashboardSnapshot,
  paginateRows,
} from '../src/data/dashboardSelectors.js'

const dataPath = fileURLToPath(new URL('../src/data/demoData.json', import.meta.url))
const demoData = JSON.parse(readFileSync(dataPath, 'utf8'))

test('dashboard snapshot scopes batch metrics and recent checkpoints', () => {
  const all = getDashboardSnapshot(demoData)
  assert.equal(all.learners.length, 120)
  assert.equal(all.batches.length, 4)
  assert.equal(all.assessments.length, 64)
  assert.equal(all.trend.length, 4)
  assert.equal(all.summary.activeLearners, 120)

  const selected = getDashboardSnapshot(demoData, 'BATCH-01', 'recent')
  assert.equal(selected.learners.length, 30)
  assert.equal(selected.batches.length, 1)
  assert.equal(selected.assessments.length, 16)
  assert.deepEqual(selected.trend.map((point) => point.checkpoint), ['Checkpoint 3', 'Checkpoint 4'])
  assert.equal(selected.skills.length, 4)
})

test('learner search and status filter work together', () => {
  const sample = demoData.students[0]
  assert.deepEqual(filterStudentRows(demoData.students, ` ${sample.studentId.toLowerCase()} `), [sample])
  assert.equal(filterStudentRows(demoData.students, 'not-a-learner').length, 0)
  const withInactive = [...demoData.students, { ...sample, studentId: 'STU-INACTIVE', fullName: 'Inactive Sample', isActive: false }]
  assert.deepEqual(filterStudentRows(withInactive, 'inactive', 'inactive').map((student) => student.studentId), ['STU-INACTIVE'])
})

test('assessment search filters title, skill and batch fields', () => {
  assert.equal(filterAssessmentRows(demoData.assessments, 'sql').length, 16)
  assert.equal(filterAssessmentRows(demoData.assessments, 'BATCH-01').length, 16)
  assert.equal(filterAssessmentRows(demoData.assessments, 'no such assessment').length, 0)
})

test('pagination clamps pages and reports an empty result range cleanly', () => {
  const secondPage = paginateRows(demoData.assessments, 2, 12)
  assert.equal(secondPage.items.length, 12)
  assert.equal(secondPage.start, 13)
  assert.equal(secondPage.end, 24)
  assert.equal(secondPage.totalPages, 6)
  const clamped = paginateRows(demoData.assessments, 99, 12)
  assert.equal(clamped.safePage, 6)
  assert.equal(clamped.end, 64)
  assert.deepEqual(paginateRows([], 5, 10), { items: [], totalPages: 1, safePage: 1, start: 0, end: 0, total: 0 })
})

test('CSV report escapes quotes and protects formula-like text cells', () => {
  const csv = buildBatchReportCsv([{
    name: 'Test, "Cohort"',
    program: '=HYPERLINK("https://example.invalid")',
    learnerCount: 4,
    averageScore: 72,
    attendanceRate: 88,
    completionRate: 90,
    status: 'completed',
  }])
  assert.ok(csv.startsWith('\uFEFF"Batch","Program"'))
  assert.ok(csv.includes('"Test, ""Cohort"""'))
  assert.ok(csv.includes("\"'=HYPERLINK("))
})

test('the learner fixture does not contain future support outcome labels', () => {
  assert.equal(demoData.students.every((student) => !('needed_support' in student)), true)
  assert.equal(demoData.dataOrigin, 'synthetic_demo')
})
