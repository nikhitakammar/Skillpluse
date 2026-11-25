const managerNavigation = [
  { id: 'overview', icon: '◫' },
  { id: 'students', icon: '◎' },
  { id: 'assessments', icon: '▤' },
  { id: 'skills', icon: '◇' },
  { id: 'reports', icon: '▥' },
]

const labels = {
  overview: 'Overview',
  students: 'Learners',
  assessments: 'Assessments',
  skills: 'Skill gaps',
  reports: 'Reports',
  users: 'User access',
}

function Sidebar({ activePage, onNavigate, user, onLogout }) {
  const navigation = user?.role === 'admin' ? [...managerNavigation, { id: 'users', icon: '♙' }] : managerNavigation
  return (
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => onNavigate('overview')} aria-label="Skill Pluse home">
        <span className="brand-mark">S</span>
        <span>Skill Pluse</span>
      </button>
      <p className="nav-label">WORKSPACE</p>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigation.map(({ id, icon }) => (
          <button
            className={`nav-item ${activePage === id ? 'active' : ''}`}
            type="button"
            aria-current={activePage === id ? 'page' : undefined}
            onClick={() => onNavigate(id)}
            key={id}
          >
            <span className="nav-icon" aria-hidden="true">{icon}</span>
            <span>{labels[id]}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="avatar">{user?.username?.slice(0, 2).toUpperCase()}</div>
        <div><strong>{user?.username}</strong><span>{user?.role === 'trainer' && user?.subject ? `${user.subject} trainer` : user?.role}</span></div>
        <button className="sidebar-logout" type="button" onClick={onLogout}>Sign out</button>
      </div>
    </aside>
  )
}

export default Sidebar
