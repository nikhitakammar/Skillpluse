import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import LoginPage from './pages/LoginPage.jsx'
import StudentDashboardPage from './pages/StudentDashboardPage.jsx'
import demoData from './data/demoData.json'
import { getDashboardSnapshot } from './data/dashboardSelectors.js'
import { clearAccessToken, fetchCurrentUser, fetchDashboardData, login, readAccessToken, saveAccessToken } from './services/api.js'

const OverviewPage = lazy(() => import('./pages/OverviewPage.jsx'))
const StudentsPage = lazy(() => import('./pages/StudentsPage.jsx'))
const AssessmentsPage = lazy(() => import('./pages/AssessmentsPage.jsx'))
const SkillGapsPage = lazy(() => import('./pages/SkillGapsPage.jsx'))
const ReportsPage = lazy(() => import('./pages/ReportsPage.jsx'))
const UsersPage = lazy(() => import('./pages/UsersPage.jsx'))

const pages = {
  overview: { label: 'Overview', title: 'Training overview', description: 'A clear picture of learner progress across your programmes.' },
  students: { label: 'Learners', title: 'Learner directory', description: 'Search learner records and review their latest training activity.' },
  assessments: { label: 'Assessments', title: 'Assessment performance', description: 'Review assessment coverage and results by training batch.' },
  skills: { label: 'Skill gaps', title: 'Skill gap analysis', description: 'Find skill areas where learners are below the selected benchmark.' },
  reports: { label: 'Reports', title: 'Reports & model evaluation', description: 'Compare training batches and review the synthetic model evaluation.' },
  users: { label: 'User access', title: 'User access management', description: 'Create accounts and assign the access each person needs.' },
}

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    let active = true
    const onExpired = () => { clearAccessToken(); setCurrentUser(null); setAuthLoading(false) }
    globalThis.addEventListener?.('skillpulse:auth-expired', onExpired)
    if (!readAccessToken()) {
      setAuthLoading(false)
    } else {
      fetchCurrentUser()
        .then((user) => { if (active) setCurrentUser(user) })
        .catch(() => { clearAccessToken(); if (active) setCurrentUser(null) })
        .finally(() => { if (active) setAuthLoading(false) })
    }
    return () => { active = false; globalThis.removeEventListener?.('skillpulse:auth-expired', onExpired) }
  }, [])

  const handleLogin = useCallback(async (username, password) => {
    const result = await login(username, password)
    saveAccessToken(result.access_token)
    setCurrentUser(result.user)
  }, [])

  const handleLogout = useCallback(() => {
    clearAccessToken()
    setCurrentUser(null)
  }, [])

  if (authLoading) return <main className="auth-screen"><p role="status">Checking your sign-in…</p></main>
  if (!currentUser) return <LoginPage onLogin={handleLogin} />
  if (currentUser.role === 'student') return <StudentDashboardPage user={currentUser} onLogout={handleLogout} />
  return <ManagerWorkspace currentUser={currentUser} onLogout={handleLogout} />
}

function ManagerWorkspace({ currentUser, onLogout }) {
  const [activePage, setActivePage] = useState('overview')
  const [batchFilter, setBatchFilter] = useState('all')
  const [trendPeriod, setTrendPeriod] = useState('all')
  const [dashboardData, setDashboardData] = useState(demoData)
  const [apiStatus, setApiStatus] = useState('connecting')
  const [apiError, setApiError] = useState('')
  const connectApi = useCallback(async () => {
    setApiStatus('connecting')
    setApiError('')
    try { setDashboardData(await fetchDashboardData()); setApiStatus('connected') }
    catch (error) { setDashboardData(demoData); setApiStatus('offline'); setApiError(error.message) }
  }, [])
  useEffect(() => { connectApi() }, [connectApi])

  const page = pages[activePage] || pages.overview
  const today = new Intl.DateTimeFormat('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(new Date())
  const pageData = useMemo(
    () => getDashboardSnapshot(dashboardData, batchFilter, trendPeriod),
    [dashboardData, batchFilter, trendPeriod],
  )

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={setActivePage} user={currentUser} onLogout={onLogout} />
      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="breadcrumb-separator">/</span>{page.label}</div>
          <div className="topbar-actions">
            <label className="batch-select-label" htmlFor="global-batch-filter">Batch</label>
            <select id="global-batch-filter" className="control-select topbar-select" value={batchFilter} onChange={(event) => setBatchFilter(event.target.value)}>
              <option value="all">All batches</option>
              {dashboardData.batches.map((batch) => <option value={batch.batchId} key={batch.batchId}>{batch.name}</option>)}
            </select>
            <span className="demo-badge"><span className="demo-dot" /> {apiStatus === 'connected' ? 'API connected' : apiStatus === 'connecting' ? 'Connecting' : 'Offline demo'}</span>
          </div>
        </header>

        <div className="page-body">
          {currentUser.role === 'trainer' && (
            <section className="trainer-workspace-banner" aria-label="Trainer workspace access">
              <div><span className="eyebrow">TRAINER WORKSPACE</span><strong>{currentUser.subject || 'Your subject'} learners, organised by batch</strong><p>Performance, assessments, attendance and assignment progress are limited to your {currentUser.subject || 'assigned'} training subject.</p></div>
              <span className="workspace-lock">🔒 {currentUser.subject || 'Subject'} access</span>
            </section>
          )}
          <div className="demo-notice" role="note">
            <span className="notice-mark" aria-hidden="true">i</span>
            <div><strong>{apiStatus === 'connected' ? 'Synthetic demonstration data' : apiStatus === 'connecting' ? 'Connecting to Skill Pluse API' : 'API unavailable — showing demo data'}</strong><span>{apiStatus === 'connected' ? ' API is connected; seeded records and model are synthetic demonstrations.' : apiStatus === 'connecting' ? ' Loading dashboard data from the local FastAPI service.' : ` ${apiError}`}</span></div>
            {apiStatus === 'offline' && <button className="pagination-button" onClick={connectApi} type="button">Retry</button>}
          </div>

          <Suspense fallback={<div role="status" style={{ minHeight: 360, display: 'grid', placeItems: 'center', color: '#8995a7', fontSize: 11 }}>Loading this workspace view…</div>}>
            {activePage === 'overview' && (
              <OverviewPage
                user={currentUser}
                description={page.description}
                today={today}
                summary={pageData.summary}
                batches={pageData.batches}
                learners={pageData.learners}
                skills={pageData.skills}
                trend={pageData.trend}
                trendPeriod={trendPeriod}
                onTrendPeriodChange={setTrendPeriod}
                onOpenStudents={() => setActivePage('students')}
                onOpenSkillGaps={() => setActivePage('skills')}
              />
            )}
            {activePage === 'students' && <StudentsPage title={page.title} description={page.description} learners={pageData.learners} batches={pageData.batches} apiConnected={apiStatus === 'connected'} currentUser={currentUser} batchFilter={batchFilter} />}
            {activePage === 'assessments' && <AssessmentsPage title={page.title} description={page.description} assessments={pageData.assessments} batches={pageData.batches} learners={pageData.learners} isAdmin={currentUser.role === 'admin'} onRefresh={connectApi} />}
            {activePage === 'skills' && <SkillGapsPage title={page.title} description={page.description} skills={pageData.skills} summary={pageData.summary} />}
            {activePage === 'reports' && <ReportsPage title={page.title} description={page.description} batches={pageData.batches} modelMetrics={dashboardData.modelMetrics} showModelEvaluation={currentUser.role === 'admin'} />}
            {activePage === 'users' && currentUser.role === 'admin' && <UsersPage learners={dashboardData.students} skills={dashboardData.skills} currentUser={currentUser} />}
          </Suspense>

          <footer className="footer-note">Skill Pluse <span>·</span> Training insights that support better learning</footer>
        </div>
      </main>
    </div>
  )
}

export default App
