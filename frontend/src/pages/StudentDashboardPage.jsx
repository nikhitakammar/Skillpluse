import { useEffect, useState } from 'react'
import { clearAccessToken, fetchStudentPortal } from '../services/api.js'
import '../styles/auth.css'

function StudentDashboardPage({ user, onLogout }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchStudentPortal(user.student_id)
      .then((result) => { if (active) setData(result) })
      .catch((reason) => { if (active) setError(reason.message) })
    return () => { active = false }
  }, [user.student_id])

  const student = data?.profile?.student
  const recommendations = data?.recommendations

  return (
    <div className="student-portal">
      <header className="portal-header"><div className="auth-brand"><span className="brand-mark">S</span><span>Skill Pluse</span></div><div><span className="role-chip">Student</span><button className="pagination-button" type="button" onClick={() => { clearAccessToken(); onLogout() }}>Sign out</button></div></header>
      <main className="portal-main">
        <div className="demo-notice" role="note"><span className="notice-mark">i</span><div><strong>Synthetic demonstration data</strong><span> These are fictional training records and practice prompts.</span></div></div>
        <div className="portal-heading"><span className="eyebrow">MY LEARNING</span><h1>{student?.full_name ? `Welcome, ${student.full_name}` : 'Your learning overview'}</h1><p>Your assessment history and trainer-reviewed practice suggestions.</p></div>
        {error && <p className="auth-error" role="alert">Could not load your learning overview: {error}</p>}
        {!data && !error && <p role="status">Loading your learning overview…</p>}
        {data && <>
          <section className="metrics-grid portal-metrics" aria-label="My training summary">
            <div className="metric-card"><span className="metric-heading">Average score</span><strong className="metric-value">{data.profile.average_score == null ? 'N/A' : `${data.profile.average_score}%`}</strong></div>
            <div className="metric-card"><span className="metric-heading">Score trend</span><strong className="metric-value">{data.profile.score_trend == null ? 'N/A' : `${data.profile.score_trend > 0 ? '+' : ''}${data.profile.score_trend} pts`}</strong></div>
            <div className="metric-card"><span className="metric-heading">Attendance</span><strong className="metric-value">{data.profile.attendance_rate == null ? 'N/A' : `${data.profile.attendance_rate}%`}</strong></div>
            <div className="metric-card"><span className="metric-heading">Assignments</span><strong className="metric-value">{data.profile.assignment_completion_rate == null ? 'N/A' : `${data.profile.assignment_completion_rate}%`}</strong></div>
          </section>
          <section className="portal-grid">
            <article className="panel"><h2>Practice suggestions</h2><p className="page-description">Score-based ideas to discuss with your trainer. They are not automated decisions.</p>
              <p>{recommendations?.error || recommendations?.message}</p>
              {recommendations?.recommendations?.map((item) => <div className="portal-recommendation" key={item.skill_area}><div><strong>{item.skill_area}</strong><span>{item.average_score}% average · {item.assessment_count} assessments</span></div><p>{item.suggestion}</p></div>)}
              {recommendations?.notice && <p className="report-footnote">{recommendations.notice}</p>}
            </article>
            <article className="panel"><h2>Recent assessments</h2>
              {data.profile.recent_assessments.length ? data.profile.recent_assessments.map((item) => <div className="portal-assessment" key={item.assessment_id}><div><strong>{item.title}</strong><span>{item.skill_area} · {item.assessment_date}</span></div><b>{item.score_percent}%</b></div>) : <p>No assessment results are recorded yet.</p>}
            </article>
          </section>
        </>}
      </main>
    </div>
  )
}

export default StudentDashboardPage
