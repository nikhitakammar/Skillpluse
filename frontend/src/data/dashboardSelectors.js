function mean(values) {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0
}

export function getDashboardSnapshot(data, batchFilter = 'all', trendPeriod = 'all') {
  const learners = data.students.filter((student) => batchFilter === 'all' || student.batchId === batchFilter)
  const batches = data.batches.filter((batch) => batchFilter === 'all' || batch.batchId === batchFilter)
  const checkpoints = data.dataSource === 'api'
    ? data.trends.filter((point) => point.batchId === batchFilter).map(({ checkpoint, averageScore }) => ({ checkpoint, averageScore }))
    : batchFilter === 'all'
    ? Array.from({ length: 4 }, (_, index) => {
      const checkpoint = `Checkpoint ${index + 1}`
      const points = data.trends.filter((point) => point.checkpoint === checkpoint)
      return { checkpoint, averageScore: Number(mean(points.map((point) => point.averageScore)).toFixed(1)) }
    })
    : data.trends.filter((point) => point.batchId === batchFilter)
      .map(({ checkpoint, averageScore }) => ({ checkpoint, averageScore }))
  const skills = data.skills.filter((skill) => skill.batchId === batchFilter)
  const assessments = data.assessments.filter((assessment) => batchFilter === 'all' || assessment.batchId === batchFilter)
  const summary = data.dataSource === 'api' ? {
    activeLearners: batchFilter === 'all' ? data.summary.activeLearners : learners.filter((student) => student.isActive).length,
    averageScore: batchFilter === 'all' ? data.summary.averageScore : Number(mean(learners.map((student) => student.averageScore).filter(Number.isFinite)).toFixed(1)),
    attendanceRate: batchFilter === 'all' ? data.summary.attendanceRate : Number(mean(learners.map((student) => student.attendanceRate).filter(Number.isFinite)).toFixed(1)),
    completionRate: batchFilter === 'all' ? data.summary.completionRate : Number(mean(learners.map((student) => student.completionRate).filter(Number.isFinite)).toFixed(1)),
    belowBenchmark: learners.filter((student) => Number.isFinite(student.averageScore) && student.averageScore < 70).length,
  } : {
    activeLearners: learners.filter((student) => student.isActive).length,
    averageScore: Number(mean(learners.map((student) => student.averageScore)).toFixed(1)),
    attendanceRate: Number(mean(learners.map((student) => student.attendanceRate)).toFixed(1)),
    completionRate: Number(mean(learners.map((student) => student.completionRate)).toFixed(1)),
    belowBenchmark: learners.filter((student) => student.averageScore < 70).length,
  }

  return {
    learners,
    batches,
    skills,
    assessments,
    summary,
    trend: trendPeriod === 'recent' ? checkpoints.slice(-2) : checkpoints,
  }
}

export function filterStudentRows(learners, search = '', statusFilter = 'all') {
  const query = search.trim().toLowerCase()
  return learners.filter((learner) => {
    const matchesSearch = `${learner.fullName} ${learner.studentId}`.toLowerCase().includes(query)
    const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' ? learner.isActive : !learner.isActive)
    return matchesSearch && matchesStatus
  })
}

export function filterAssessmentRows(assessments, search = '') {
  const query = search.trim().toLowerCase()
  return assessments.filter((assessment) =>
    `${assessment.title} ${assessment.skillArea} ${assessment.batchId}`.toLowerCase().includes(query),
  )
}

export function paginateRows(rows, currentPage, pageSize) {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const safePage = Math.min(Math.max(1, currentPage), totalPages)
  const start = rows.length ? (safePage - 1) * pageSize + 1 : 0
  const end = Math.min(safePage * pageSize, rows.length)
  return {
    items: rows.slice((safePage - 1) * pageSize, safePage * pageSize),
    totalPages,
    safePage,
    start,
    end,
    total: rows.length,
  }
}

function csvCell(value) {
  let safeValue = String(value ?? '')
  if (/^[=+@\-]/.test(safeValue)) safeValue = `'${safeValue}`
  return `"${safeValue.replaceAll('"', '""')}"`
}

export function buildBatchReportCsv(batches) {
  const columns = ['Batch', 'Program', 'Learners', 'Average score (%)', 'Attendance (%)', 'Assignment completion (%)', 'Status']
  const rows = batches.map((batch) => [batch.name, batch.program, batch.learnerCount, batch.averageScore, batch.attendanceRate, batch.completionRate, batch.status])
  return `\uFEFF${[columns, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')}`
}
