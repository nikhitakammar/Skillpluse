import { useMemo, useState } from 'react'
import PageHeading from '../components/PageHeading.jsx'
import { filterStudentRows, paginateRows } from '../data/dashboardSelectors.js'
import { fetchLearnerInsights } from '../services/api.js'

const PAGE_SIZE = 10

function StudentsPage({ title, description, learners, batches, apiConnected }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [insights, setInsights] = useState(null)
  const [insightsLoading, setInsightsLoading] = useState(false)
  const batchNames = new Map(batches.map((batch) => [batch.batchId, batch.name]))
  const filteredLearners = useMemo(
    () => filterStudentRows(learners, search, statusFilter),
    [learners, search, statusFilter],
  )
  const pagination = useMemo(
    () => paginateRows(filteredLearners, currentPage, PAGE_SIZE),
    [filteredLearners, currentPage],
  )
  const { items: visibleLearners, totalPages, safePage, start, end } = pagination

  function changeSearch(value) {
    setSearch(value)
    setCurrentPage(1)
  }

  function changeStatus(value) {
    setStatusFilter(value)
    setCurrentPage(1)
  }

  async function openProfile(learner) {
    setSelectedStudent(learner)
    setInsights(null)
    if (!apiConnected) return
    setInsightsLoading(true)
    try { setInsights(await fetchLearnerInsights(learner.studentId)) }
    catch (error) { setInsights({ error: error.message }) }
    finally { setInsightsLoading(false) }
  }

  return (
    <>
      <PageHeading title={title} description={description} />
      <section className="panel table-panel">
        <div className="table-toolbar">
          <div className="table-count"><strong>{filteredLearners.length}</strong><span>learners in this view</span></div>
          <div className="table-controls">
            <label className="search-control">
              <span className="search-icon" aria-hidden="true">⌕</span>
              <input type="search" value={search} onChange={(event) => changeSearch(event.target.value)} placeholder="Search learners" aria-label="Search learners" />
            </label>
            <label className="visually-hidden" htmlFor="learner-status-filter">Filter by status</label>
            <select id="learner-status-filter" className="control-select" value={statusFilter} onChange={(event) => changeStatus(event.target.value)}>
              <option value="all">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>Learner</th><th>Training batch</th><th>Average score</th><th>Trend</th><th>Attendance</th><th>Assignments</th><th>Status</th></tr></thead>
            <tbody>
              {visibleLearners.map((learner) => (
                <tr key={learner.studentId}>
                  <td><button className="student-link" type="button" onClick={() => openProfile(learner)}>{learner.fullName}<span>{learner.studentId}</span></button></td>
                  <td><span className="batch-name-cell">{batchNames.get(learner.batchId)?.split(' · ')[0]}</span></td>
                  <td><div className="score-cell"><strong>{learner.averageScore == null ? '—' : `${learner.averageScore}%`}</strong><span className="mini-progress"><i className={learner.averageScore < 70 ? 'below' : ''} style={{ width: `${learner.averageScore || 0}%` }} /></span></div></td>
                  <td><span className={`trend-value ${learner.scoreTrend >= 0 ? 'positive' : 'negative'}`}>{learner.scoreTrend == null ? '—' : `${learner.scoreTrend >= 0 ? '+' : ''}${learner.scoreTrend} pts`}</span></td>
                  <td>{learner.attendanceRate == null ? '—' : `${learner.attendanceRate}%`}</td>
                  <td>{learner.completionRate == null ? '—' : `${learner.completionRate}%`}</td>
                  <td><span className={`status-pill ${learner.isActive ? 'status-active' : 'status-inactive'}`}><i />{learner.isActive ? 'Active' : 'Inactive'}</span></td>
                </tr>
              ))}
              {!visibleLearners.length && <tr><td colSpan="7"><div className="empty-state"><strong>No learners match your search</strong><span>Try a different name or clear the status filter.</span></div></td></tr>}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <span>Showing {start}–{end} of {filteredLearners.length}</span>
          <div><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={safePage === 1}>Previous</button><span className="page-number">{safePage} / {totalPages}</span><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))} disabled={safePage === totalPages}>Next</button></div>
        </div>
      </section>

      {selectedStudent && (
        <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedStudent(null) }}>
          <section className="student-modal" role="dialog" aria-modal="true" aria-labelledby="student-modal-title">
            <div className="modal-heading"><div><span className="eyebrow">LEARNER PROFILE</span><h2 id="student-modal-title">{selectedStudent.fullName}</h2><p>{selectedStudent.studentId} · {batchNames.get(selectedStudent.batchId)}</p></div><button type="button" className="icon-button" onClick={() => setSelectedStudent(null)} aria-label="Close learner profile">×</button></div>
            <div className="modal-stats">
              <div><span>Average score</span><strong>{selectedStudent.averageScore == null ? '—' : `${selectedStudent.averageScore}%`}</strong></div>
              <div><span>Score trend</span><strong className={selectedStudent.scoreTrend >= 0 ? 'positive' : 'negative'}>{selectedStudent.scoreTrend == null ? '—' : `${selectedStudent.scoreTrend >= 0 ? '+' : ''}${selectedStudent.scoreTrend} pts`}</strong></div>
              <div><span>Attendance</span><strong>{selectedStudent.attendanceRate == null ? '—' : `${selectedStudent.attendanceRate}%`}</strong></div>
              <div><span>Assignments</span><strong>{selectedStudent.completionRate == null ? '—' : `${selectedStudent.completionRate}%`}</strong></div>
            </div>
            {insightsLoading && <p className="modal-note" role="status">Loading assessment history and trainer-assist signals…</p>}
            {insights?.error && <p className="modal-note" role="alert">Learner insights unavailable: {insights.error}</p>}
            {insights?.support && <div className="modal-note"><strong>Trainer-assist support signal</strong><p>{insights.support.error ? `Signal unavailable: ${insights.support.error}` : insights.support.status === 'insufficient_data' ? insights.support.message : `${insights.support.may_need_support ? 'Review may be helpful' : 'No additional support signal'} · ${Math.round(insights.support.support_probability * 100)}% estimated probability`}</p>{insights.support.explanations?.map((item) => <p key={item.feature}>{item.explanation}</p>)}{insights.support.notice && <p>{insights.support.notice}</p>}</div>}
            {insights?.recommendations && <div className="modal-note"><strong>Suggested practice (score-based)</strong><p>{insights.recommendations.error ? `Suggestions unavailable: ${insights.recommendations.error}` : insights.recommendations.message}</p>{insights.recommendations.recommendations?.map((item) => <p key={item.skill_area}><strong>{item.skill_area} · {item.average_score}%</strong><br />{item.suggestion}<br /><span>{item.reason}</span></p>)}{insights.recommendations.notice && <p>{insights.recommendations.notice}</p>}</div>}
            {insights?.cluster && <p className="modal-note">{insights.cluster.error ? `Learning group unavailable: ${insights.cluster.error}` : `Learning group: ${insights.cluster.status === 'ready' ? `Group ${insights.cluster.cluster_id} (similarity grouping only)` : insights.cluster.reasons?.join(' ')}. ${insights.cluster.notice}`}</p>}
            {insights?.profile?.recent_assessments?.length > 0 && <div className="modal-note"><strong>Recent assessment history</strong>{insights.profile.recent_assessments.slice(0, 5).map((item) => <p key={item.assessment_id}>{item.title} · {item.score_percent}%</p>)}</div>}
            {!apiConnected && <p className="modal-note">Preview profile from synthetic demo records. Connect FastAPI to load trainer-assist signals.</p>}
          </section>
        </div>
      )}
    </>
  )
}

export default StudentsPage
