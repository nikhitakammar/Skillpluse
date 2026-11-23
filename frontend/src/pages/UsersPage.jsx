import { useEffect, useState } from 'react'
import PageHeading from '../components/PageHeading.jsx'
import { createAccount, fetchAccounts, updateAccountStatus } from '../services/api.js'
import '../styles/accountManagement.css'

function UsersPage({ learners, currentUser }) {
  const [accounts, setAccounts] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('trainer')
  const [studentId, setStudentId] = useState('')
  const [status, setStatus] = useState({ type: 'idle', message: '' })
  const availableLearners = learners.filter((learner) => !accounts.some((account) => account.student_id === learner.studentId))

  async function refreshAccounts() {
    setAccounts(await fetchAccounts())
  }

  useEffect(() => { refreshAccounts().catch((error) => setStatus({ type: 'error', message: error.message })) }, [])

  async function submit(event) {
    event.preventDefault()
    setStatus({ type: 'loading', message: '' })
    try {
      await createAccount({ username, password, role, student_id: role === 'student' ? studentId : null })
      setUsername('')
      setPassword('')
      setStudentId('')
      setStatus({ type: 'success', message: `Created ${role} account. Share its password with the user securely.` })
      await refreshAccounts()
    } catch (error) {
      setStatus({ type: 'error', message: error.message })
    }
  }

  async function toggleAccount(account) {
    setStatus({ type: 'loading', message: '' })
    try {
      await updateAccountStatus(account.user_id, !account.is_active)
      await refreshAccounts()
      setStatus({ type: 'success', message: `${account.username} account ${account.is_active ? 'deactivated' : 'activated'}.` })
    } catch (error) {
      setStatus({ type: 'error', message: error.message })
    }
  }

  return (
    <>
      <PageHeading title="User access" description="Create accounts and assign the least access each person needs." />
      <section className="panel account-create-panel">
        <h2>Create an account</h2>
        <p className="page-description">Passwords are stored as Argon2 hashes. Student accounts must link to one learner record.</p>
        <form className="account-create-form" onSubmit={submit}>
          <label><span>Username</span><input required minLength="3" maxLength="40" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" /></label>
          <label><span>Temporary password (12+ characters)</span><input required minLength="12" maxLength="128" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></label>
          <label><span>Role</span><select className="control-select" value={role} onChange={(event) => { setRole(event.target.value); setStudentId('') }}><option value="trainer">Trainer</option><option value="student">Student</option><option value="admin">Admin</option></select></label>
          {role === 'student' && <label><span>Learner record</span><select className="control-select" required value={studentId} onChange={(event) => setStudentId(event.target.value)}><option value="">Select a learner</option>{availableLearners.map((learner) => <option key={learner.studentId} value={learner.studentId}>{learner.fullName} · {learner.studentId}</option>)}</select></label>}
          <button type="submit" className="primary-button" disabled={status.type === 'loading' || (role === 'student' && !studentId)}>{status.type === 'loading' ? 'Saving…' : 'Create account'}</button>
        </form>
        {status.message && <p className={`account-status ${status.type}`} role={status.type === 'error' ? 'alert' : 'status'}>{status.message}</p>}
      </section>
      <section className="panel account-list-panel">
        <div className="panel-heading"><div><h2>Accounts</h2><p>Deactivated accounts lose access on their next request.</p></div><span className="account-count">{accounts.length}</span></div>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Username</th><th>Role</th><th>Learner</th><th>Status</th><th>Access</th></tr></thead><tbody>
          {accounts.map((account) => <tr key={account.user_id}><td><strong className="table-primary">{account.username}</strong></td><td><span className="role-chip">{account.role}</span></td><td>{account.student_id || '—'}</td><td>{account.is_active ? 'Active' : 'Inactive'}</td><td><button className="pagination-button" type="button" disabled={status.type === 'loading' || account.user_id === currentUser?.user_id} onClick={() => toggleAccount(account)}>{account.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}
          {!accounts.length && <tr><td colSpan="5"><div className="empty-state"><strong>No accounts found</strong><span>Provision the first admin account from the backend setup command.</span></div></td></tr>}
        </tbody></table></div>
      </section>
    </>
  )
}

export default UsersPage
