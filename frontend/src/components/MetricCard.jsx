function MetricCard({ label, value, detail, icon, tone = 'blue' }) {
  return (
    <article className="metric-card">
      <div className="metric-heading"><span>{label}</span><span className={`metric-icon ${tone}`} aria-hidden="true">{icon}</span></div>
      <strong className="metric-value">{value}</strong>
      <p className="metric-detail">{detail}</p>
    </article>
  )
}

export default MetricCard
