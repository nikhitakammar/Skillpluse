import { useState } from 'react'
import MetricCard from '../components/MetricCard.jsx'
import PageHeading from '../components/PageHeading.jsx'
import PanelHeading from '../components/PanelHeading.jsx'
import { buildBatchReportCsv } from '../data/dashboardSelectors.js'
import '../styles/reports.css'

function downloadBatchReport(batches) {
  const csv = buildBatchReportCsv(batches)
  const objectUrl = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = 'skillpulse-synthetic-batch-report.csv'
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
}

function ReportsPage({ title, description, batches, modelMetrics }) {
  const [exportMessage, setExportMessage] = useState('')
  const metrics = modelMetrics?.metrics
  const matrix = modelMetrics?.confusion_matrix?.values

  function handleExport() {
    downloadBatchReport(batches)
    setExportMessage('Synthetic batch report downloaded.')
  }

  return (
    <>
      <PageHeading
        title={title}
        description={description}
        action={<button className="primary-button" type="button" onClick={handleExport}><span aria-hidden="true">↓</span> Export batch report</button>}
      />
      <section className="metrics-grid report-metrics">
        <MetricCard label="Model precision" value={metrics ? `${(metrics.precision * 100).toFixed(1)}%` : 'Unavailable'} detail="Held-out synthetic test set" icon="◎" />
        <MetricCard label="Model recall" value={metrics ? `${(metrics.recall * 100).toFixed(1)}%` : 'Unavailable'} detail="Support examples correctly flagged" icon="↗" tone="amber" />
        <MetricCard label="Model F1-score" value={metrics ? `${(metrics.f1_score * 100).toFixed(1)}%` : 'Unavailable'} detail="Precision and recall balance" icon="◒" tone="violet" />
        <MetricCard label="Test examples" value={modelMetrics?.test_sample_count ?? '�'} detail="From a stratified 75/25 split" icon="▤" tone="mint" />
      </section>

      <section className="dashboard-grid reports-grid">
        <article className="panel panel-large">
          <PanelHeading title="Batch comparison" description="Cohort-level training indicators from the synthetic dataset" />
          <div className="table-scroll"><table className="data-table report-table">
            <thead><tr><th>Batch</th><th>Programme</th><th>Learners</th><th>Avg. score</th><th>Attendance</th><th>Assignments</th><th>Status</th></tr></thead>
            <tbody>{batches.map((batch) => (
              <tr key={batch.batchId}>
                <td><strong className="table-primary">{batch.name.split(' · ')[0]}</strong><span className="table-secondary">{batch.batchId}</span></td>
                <td>{batch.program}</td><td>{batch.learnerCount}</td><td>{batch.averageScore == null ? "N/A" : `${batch.averageScore}%`}</td><td>{batch.attendanceRate == null ? "N/A" : `${batch.attendanceRate}%`}</td><td>{batch.completionRate == null ? "N/A" : `${batch.completionRate}%`}</td>
                <td><span className="status-pill status-complete"><i />{batch.status}</span></td>
              </tr>
            ))}</tbody>
          </table></div>
          {exportMessage && <p className="export-feedback" role="status">{exportMessage}</p>}
        </article>

        <article className="panel model-panel">
          <div className="model-panel-kicker"><span className="model-icon">✦</span><span>LOGISTIC REGRESSION</span><span className="synthetic-chip">SYNTHETIC</span></div>
          <h2>Support model evaluation</h2>
          <p className="model-description">One held-out evaluation from the generated demonstration dataset.</p>
          <div className="confusion-title"><strong>Confusion matrix</strong><span>Actual rows · predicted columns</span></div>
          {matrix ? <table className="confusion-matrix" aria-label="Confusion matrix: actual rows and predicted columns">
            <thead><tr><th scope="col">Actual \ Predicted</th><th scope="col">On track</th><th scope="col">Needs support</th></tr></thead>
            <tbody>
              <tr><th scope="row">On track</th><td className="matrix-true">{matrix[0][0]}<span>correct</span></td><td className="matrix-false">{matrix[0][1]}<span>false alarms</span></td></tr>
              <tr><th scope="row">Needs support</th><td className="matrix-false">{matrix[1][0]}<span>missed</span></td><td className="matrix-true">{matrix[1][1]}<span>correct</span></td></tr>
            </tbody>
          </table> : <p className="model-description">Model evaluation is unavailable. Restore or train the synthetic model artifact.</p>}
          {modelMetrics && <div className="model-caveat"><strong>Demo limitation</strong><p>{modelMetrics.notice}</p></div>}
        </article>
      </section>
      <p className="report-footnote">All displayed data is synthetic. These model results are not evidence of real-world accuracy and must not be used for placement or certification decisions.</p>
    </>
  )
}

export default ReportsPage
