import { useMemo, useState } from 'react'
import PageHeading from '../components/PageHeading.jsx'
import { filterAssessmentRows, paginateRows } from '../data/dashboardSelectors.js'
import { createAssessment as createAssessmentRequest, importAssessmentScores } from '../services/api.js'
import '../styles/assessmentImport.css'

const PAGE_SIZE = 12

function AssessmentsPage({ title, description, assessments, batches, learners, isAdmin, onRefresh }) {
  const [search, setSearch] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedAssessmentId, setSelectedAssessmentId] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [importState, setImportState] = useState({ status: 'idle', message: '' })
  const [assessmentBatchId, setAssessmentBatchId] = useState('')
  const [assessmentTitle, setAssessmentTitle] = useState('')
  const [assessmentSkill, setAssessmentSkill] = useState('')
  const [assessmentDate, setAssessmentDate] = useState('')
  const [assessmentMaxScore, setAssessmentMaxScore] = useState('100')
  const [createState, setCreateState] = useState({ status: 'idle', message: '' })
  const batchNames = new Map(batches.map((batch) => [batch.batchId, batch.name]))
  const selectedAssessment = assessments.find((assessment) => assessment.assessmentId === selectedAssessmentId)
  const createBatchId = batches.some((batch) => batch.batchId === assessmentBatchId) ? assessmentBatchId : batches[0]?.batchId || ''
  const createBatch = batches.find((batch) => batch.batchId === createBatchId)
  const filtered = useMemo(() => filterAssessmentRows(assessments, search), [assessments, search])
  const pagination = useMemo(() => paginateRows(filtered, currentPage, PAGE_SIZE), [filtered, currentPage])
  const { items: rows, totalPages, safePage, start, end } = pagination

  function downloadTemplate() {
    if (!selectedAssessment) return
    const csvRows = [['student_id', 'score'], ...learners
      .filter((learner) => learner.batchId === selectedAssessment.batchId)
      .map((learner) => [learner.studentId, ''])]
    const csv = `\uFEFF${csvRows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\r\n')}`
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedAssessment.assessmentId.toLowerCase()}-scores-template.csv`
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  async function submitImport() {
    if (!selectedAssessment || !selectedFile) return
    setImportState({ status: 'loading', message: '' })
    try {
      const result = await importAssessmentScores(selectedAssessment.assessmentId, await selectedFile.text())
      setImportState({ status: 'success', message: `Imported ${result.imported_count} score${result.imported_count === 1 ? '' : 's'}${result.skipped_blank_scores ? `; skipped ${result.skipped_blank_scores} blank score row(s)` : ''}.` })
      setSelectedFile(null)
      setFileInputKey((key) => key + 1)
      await onRefresh?.()
    } catch (error) {
      setImportState({ status: 'error', message: error.message })
    }
  }

  async function submitAssessment(event) {
    event.preventDefault()
    if (!createBatch) return
    setCreateState({ status: 'loading', message: '' })
    try {
      const created = await createAssessmentRequest({
        batch_id: createBatchId,
        title: assessmentTitle,
        skill_area: assessmentSkill,
        assessment_date: assessmentDate || createBatch.startDate,
        max_score: Number(assessmentMaxScore),
      })
      setSelectedAssessmentId(created.assessment_id)
      setAssessmentTitle('')
      setAssessmentSkill('')
      setCreateState({ status: 'success', message: `Created ${created.title}. It is now available for score import.` })
      await onRefresh?.()
    } catch (error) {
      setCreateState({ status: 'error', message: error.message })
    }
  }

  return (
    <>
      <PageHeading title={title} description={description} />
      {isAdmin && <details className="assessment-create-panel">
        <summary>Create an assessment</summary>
        <form className="assessment-create-form" onSubmit={submitAssessment}>
          <label><span>Batch</span><select className="control-select" required value={createBatchId} onChange={(event) => { setAssessmentBatchId(event.target.value); setAssessmentDate('') }}>
            {batches.map((batch) => <option key={batch.batchId} value={batch.batchId}>{batch.name}</option>)}
          </select></label>
          <label><span>Assessment title</span><input required minLength="2" maxLength="120" value={assessmentTitle} onChange={(event) => setAssessmentTitle(event.target.value)} placeholder="e.g. Functions checkpoint" /></label>
          <label><span>Skill area</span><input required maxLength="80" value={assessmentSkill} onChange={(event) => setAssessmentSkill(event.target.value)} placeholder="e.g. Python" /></label>
          <label><span>Assessment date</span><input type="date" required min={createBatch?.startDate} max={createBatch?.endDate} value={assessmentDate || createBatch?.startDate || ''} onChange={(event) => setAssessmentDate(event.target.value)} /></label>
          <label><span>Maximum score</span><input type="number" required min="0.01" max="10000" step="any" value={assessmentMaxScore} onChange={(event) => setAssessmentMaxScore(event.target.value)} /></label>
          <button className="primary-button" type="submit" disabled={!createBatch || createState.status === 'loading'}>{createState.status === 'loading' ? 'Creating…' : 'Create assessment'}</button>
        </form>
        {createState.message && <p className={`score-import-message ${createState.status}`} role={createState.status === 'error' ? 'alert' : 'status'}>{createState.message}</p>}
      </details>}
      {isAdmin && <section className="score-import-panel" aria-labelledby="score-import-title">
        <div className="score-import-heading"><div><h2 id="score-import-title">Import assessment scores</h2><p>Upload a UTF-8 CSV with <code>student_id</code> and <code>score</code> columns. Blank scores are skipped; every populated row must pass validation before any scores are saved.</p></div></div>
        <div className="score-import-controls">
          <label><span>Assessment</span><select className="control-select" value={selectedAssessmentId} onChange={(event) => { setSelectedAssessmentId(event.target.value); setImportState({ status: 'idle', message: '' }) }}>
            <option value="">Select an assessment</option>
            {assessments.map((assessment) => <option key={assessment.assessmentId} value={assessment.assessmentId}>{assessment.title} · {batchNames.get(assessment.batchId)?.split(' · ')[0]}</option>)}
          </select></label>
          <label><span>CSV file</span><input key={fileInputKey} type="file" accept=".csv,text/csv" onChange={(event) => { setSelectedFile(event.target.files?.[0] || null); setImportState({ status: 'idle', message: '' }) }} /></label>
          <div className="score-import-actions"><button className="primary-button" type="button" disabled={!selectedAssessment || !selectedFile || importState.status === 'loading'} onClick={submitImport}>{importState.status === 'loading' ? 'Importing…' : 'Import scores'}</button><button className="pagination-button" type="button" disabled={!selectedAssessment} onClick={downloadTemplate}>Download template</button></div>
        </div>
        {selectedAssessment && <p className="score-import-hint">Maximum score: {selectedAssessment.maxScore ?? 100}. Imports allow up to 1,000 data rows and 2 MB per file.</p>}
        {importState.message && <p className={`score-import-message ${importState.status}`} role={importState.status === 'error' ? 'alert' : 'status'}>{importState.message}</p>}
      </section>}
      <section className="panel table-panel">
        <div className="table-toolbar">
          <div className="table-count"><strong>{filtered.length}</strong><span>assessments in this view</span></div>
          <label className="search-control"><span className="search-icon" aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1) }} placeholder="Search assessments or skills" aria-label="Search assessments or skills" /></label>
        </div>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Assessment</th><th>Batch</th><th>Skill area</th><th>Date</th><th>Average score</th><th>Results recorded</th></tr></thead>
          <tbody>
            {rows.map((assessment) => (
              <tr key={assessment.assessmentId}>
                <td><strong className="table-primary">{assessment.title}</strong><span className="table-secondary">{assessment.assessmentId}</span></td>
                <td>{batchNames.get(assessment.batchId)?.split(' · ')[0]}</td>
                <td><span className="skill-tag">{assessment.skillArea}</span></td>
                <td>{new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${assessment.assessmentDate}T00:00:00`))}</td>
                <td><div className="score-cell"><strong>{assessment.averageScore == null ? "N/A" : `${assessment.averageScore}%`}</strong><span className="mini-progress"><i className={assessment.averageScore < 70 ? "below" : ""} style={{ width: `${assessment.averageScore || 0}%` }} /></span></div></td>
                <td><span>{assessment.submittedCount == null ? "N/A" : `${assessment.submittedCount} / ${assessment.learnerCount}`}</span><span className="table-secondary">{assessment.submittedCount == null ? "no results" : "learners"}</span></td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan="6"><div className="empty-state"><strong>No assessments found</strong><span>Try another search term.</span></div></td></tr>}
          </tbody>
        </table></div>
        <div className="pagination"><span>Showing {start}–{end} of {filtered.length}</span><div><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.max(1, page - 1))} disabled={safePage === 1}>Previous</button><span className="page-number">{safePage} / {totalPages}</span><button type="button" className="pagination-button" onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))} disabled={safePage === totalPages}>Next</button></div></div>
      </section>
    </>
  )
}

export default AssessmentsPage
