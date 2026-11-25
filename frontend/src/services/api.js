const API_BASE = (import.meta.env?.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const TOKEN_KEY = 'skillpulse_access_token'

export function readAccessToken() {
  try { return globalThis.sessionStorage?.getItem(TOKEN_KEY) || null }
  catch { return null }
}

export function saveAccessToken(token) {
  try { globalThis.sessionStorage?.setItem(TOKEN_KEY, token) }
  catch { /* session storage may be disabled by browser settings */ }
}

export function clearAccessToken() {
  try { globalThis.sessionStorage?.removeItem(TOKEN_KEY) }
  catch { /* session storage may be disabled by browser settings */ }
}

async function request(path, options) {
  const token = readAccessToken()
  const headers = { ...(options?.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 401 && token) {
    clearAccessToken()
    globalThis.dispatchEvent?.(new Event('skillpulse:auth-expired'))
  }
  if (!response.ok) {
    let message = `API request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((issue) => {
          const field = Array.isArray(issue.loc) ? issue.loc.filter((part) => part !== 'body').join('.') : ''
          const description = issue.msg || 'Invalid value'
          return field ? `${field}: ${description}` : description
        }).join('\n') || message
      } else {
        message = body.detail?.message || body.detail?.errors?.join('\n') || message
      }
    } catch { /* keep status message */ }
    throw new Error(message)
  }
  return response.json()
}

export async function login(username, password) {
  return request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export function fetchCurrentUser() {
  return request('/auth/me')
}

export function createAccount(payload) {
  return request('/auth/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchAccounts() {
  return request('/auth/users')
}

export function updateAccountStatus(userId, isActive) {
  return request(`/auth/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  })
}

export function fetchTrainerScopes() {
  return request('/trainer-scopes')
}

export function fetchMyTrainerScopes() {
  return request('/trainer-scopes/mine')
}

export function createTrainerScope(payload) {
  return request('/trainer-scopes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function deleteTrainerScope(scopeId) {
  return request(`/trainer-scopes/${encodeURIComponent(scopeId)}`, { method: 'DELETE' })
}

export async function fetchStudentPortal(studentId) {
  const id = encodeURIComponent(studentId)
  const [profile, recommendations, assignments] = await Promise.all([
    request(`/students/${id}`),
    request(`/students/${id}/recommendations`),
    request(`/students/${id}/assignments`),
  ])
  return { profile, recommendations, assignments }
}

export async function importAssessmentScores(assessmentId, csvText) {
  const token = readAccessToken()
  const headers = { 'Content-Type': 'text/csv; charset=utf-8' }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/assessments/${encodeURIComponent(assessmentId)}/results/import`, {
    method: 'POST',
    headers,
    body: csvText,
  })
  if (response.status === 401 && token) {
    clearAccessToken()
    globalThis.dispatchEvent?.(new Event('skillpulse:auth-expired'))
  }
  if (!response.ok) {
    let message = `CSV import failed (${response.status})`
    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : [body.detail?.message, ...(body.detail?.errors || [])].filter(Boolean).join('\n') || message
    } catch { /* keep status message */ }
    throw new Error(message)
  }
  return response.json()
}

export function createAssessment(payload) {
  return request('/assessments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

async function allStudents() {
  const first = await request('/students?limit=100&offset=0')
  const pages = await Promise.all(Array.from({ length: Math.ceil(Math.max(0, first.total - first.items.length) / 100) }, (_, i) => request(`/students?limit=100&offset=${(i + 1) * 100}`)))
  return [...first.items, ...pages.flatMap((page) => page.items)]
}

export async function fetchTrainerLearners(skillArea, batchId = 'all') {
  const query = `${skillArea ? `&skill_area=${encodeURIComponent(skillArea)}` : ''}${batchId && batchId !== 'all' ? `&batch_id=${encodeURIComponent(batchId)}` : ''}`
  const first = await request(`/students?limit=100&offset=0${query}`)
  const pages = await Promise.all(Array.from(
    { length: Math.ceil(Math.max(0, first.total - first.items.length) / 100) },
    (_, i) => request(`/students?limit=100&offset=${(i + 1) * 100}${query}`),
  ))
  return [...first.items, ...pages.flatMap((page) => page.items)].map((student) => ({
    studentId: student.student_id, batchId: student.batch_id, fullName: student.full_name,
    enrollmentDate: student.enrollment_date, isActive: student.is_active, dataOrigin: student.data_origin,
    averageScore: student.average_score, scoreTrend: student.score_trend,
    attendanceRate: student.attendance_rate, completionRate: student.assignment_completion_rate,
  }))
}

export async function fetchDashboardData() {
  const [rawBatches, comparisons, overview, rawStudents, rawAssessments, modelMetrics, globalTrend, globalSkills] = await Promise.all([
    request('/batches'), request('/analytics/batch-comparison'), request('/analytics/overview'), allStudents(),
    request('/assessments'), request('/predictions/model-metrics').catch(() => null),
    request('/analytics/performance-trend'), request('/analytics/skill-gaps'),
  ])
  const comparisonById = new Map(comparisons.map((row) => [row.batch_id, row]))
  const batches = rawBatches.map((batch) => {
    const metrics = comparisonById.get(batch.batch_id) || {}
    return { batchId: batch.batch_id, name: batch.name, program: batch.program, startDate: batch.start_date, endDate: batch.end_date,
      status: batch.end_date < new Date().toISOString().slice(0, 10) ? 'completed' : 'in progress', learnerCount: metrics.active_learners ?? 0,
      averageScore: metrics.average_score, attendanceRate: metrics.attendance_rate, completionRate: metrics.assignment_completion_rate }
  })
  const students = rawStudents.map((student) => ({ studentId: student.student_id, batchId: student.batch_id, fullName: student.full_name,
    enrollmentDate: student.enrollment_date, isActive: student.is_active, dataOrigin: student.data_origin, averageScore: student.average_score,
    scoreTrend: student.score_trend, attendanceRate: student.attendance_rate, completionRate: student.assignment_completion_rate }))
  const assessments = rawAssessments.map((assessment) => ({ assessmentId: assessment.assessment_id, batchId: assessment.batch_id,
    title: assessment.title, skillArea: assessment.skill_area, assessmentDate: assessment.assessment_date,
    averageScore: assessment.average_score, submittedCount: assessment.results_recorded, learnerCount: assessment.learner_count, maxScore: assessment.max_score }))
  const trends = globalTrend.map((point) => ({ batchId: 'all', date: point.assessment_date, checkpoint: point.assessment_date,
    averageScore: point.average_score }))
  const skills = globalSkills.map((skill) => ({ batchId: 'all', skillArea: skill.skill_area, averageScore: skill.average_score,
    learnersBelowBenchmark: skill.learners_below_benchmark, benchmark: skill.benchmark }))
  const batchAnalytics = await Promise.all(batches.map(async (batch) => {
    const [trend, gaps] = await Promise.all([request(`/analytics/performance-trend?batch_id=${encodeURIComponent(batch.batchId)}`), request(`/analytics/skill-gaps?batch_id=${encodeURIComponent(batch.batchId)}`)])
    return { trend: trend.map((point) => ({ batchId: batch.batchId, date: point.assessment_date, checkpoint: point.assessment_date, averageScore: point.average_score })),
      skills: gaps.map((skill) => ({ batchId: batch.batchId, skillArea: skill.skill_area, averageScore: skill.average_score, learnersBelowBenchmark: skill.learners_below_benchmark, benchmark: skill.benchmark })) }
  }))
  trends.push(...batchAnalytics.flatMap((value) => value.trend))
  skills.push(...batchAnalytics.flatMap((value) => value.skills))
  return { dataSource: 'api', generatedAt: new Date().toISOString().slice(0, 10), summary: {
    activeLearners: overview.active_learners, averageScore: overview.average_score, attendanceRate: overview.attendance_rate,
    completionRate: overview.assignment_completion_rate, belowBenchmark: students.filter((student) => student.averageScore !== null && student.averageScore < 70).length,
  }, batches, students, assessments, trends, skills, modelMetrics }
}

export async function fetchLearnerInsights(studentId, userRole = 'trainer', skillArea = null) {
  const id = encodeURIComponent(studentId)
  const subjectQuery = skillArea ? `?skill_area=${encodeURIComponent(skillArea)}` : ''
  const [profile, recommendations] = await Promise.all([
    request(`/students/${id}${subjectQuery}`),
    request(`/students/${id}/recommendations${subjectQuery}`),
  ].map((promise) => promise.catch((error) => ({ error: error.message }))))
  let support = null
  let cluster = null
  if (userRole === 'admin') {
    ;[support, cluster] = await Promise.all([
      request(`/predictions/students/${id}/support`),
      request(`/predictions/students/${id}/learning-cluster`),
    ].map((promise) => promise.catch((error) => ({ error: error.message }))))
  }
  return { profile, support, cluster, recommendations }
}
