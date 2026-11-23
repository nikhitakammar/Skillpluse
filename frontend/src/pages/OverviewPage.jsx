import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import MetricCard from '../components/MetricCard.jsx'
import PageHeading from '../components/PageHeading.jsx'
import PanelHeading from '../components/PanelHeading.jsx'

function OverviewPage({ description, today, summary, batches, learners, skills, trend, trendPeriod, onTrendPeriodChange, onOpenStudents, onOpenSkillGaps }) {
  const reviewLearners = [...learners]
    .filter((learner) => learner.averageScore < 70)
    .sort((left, right) => left.averageScore - right.averageScore)
    .slice(0, 5)
  const batchNames = new Map(batches.map((batch) => [batch.batchId, batch.name]))
  const trendAction = (
    <div className="segmented-control" role="group" aria-label="Performance time range">
      <button type="button" className={trendPeriod === 'all' ? 'selected' : ''} onClick={() => onTrendPeriodChange('all')}>All</button>
      <button type="button" className={trendPeriod === 'recent' ? 'selected' : ''} onClick={() => onTrendPeriodChange('recent')}>Recent 2</button>
    </div>
  )

  return (
    <>
      <PageHeading eyebrow={today} title="Good morning, Alex" description={description} />

      <section className="metrics-grid" aria-label="Training summary">
        <MetricCard label="Active learners" value={summary.activeLearners.toLocaleString()} detail="Across selected batches" icon="◎" />
        <MetricCard label="Average score" value={summary.averageScore == null ? "N/A" : `${summary.averageScore}%`} detail="Across recorded assessments" icon="◒" tone="mint" />
        <MetricCard label="Attendance rate" value={summary.attendanceRate == null ? "N/A" : `${summary.attendanceRate}%`} detail="Present = 100%, late = 50%" icon="◷" tone="violet" />
        <MetricCard label="Assignment completion" value={summary.completionRate == null ? "N/A" : `${summary.completionRate}%`} detail="Submitted assignments" icon="✓" tone="amber" />
      </section>

      <section className="dashboard-grid overview-grid">
        <article className="panel panel-large">
          <PanelHeading title="Performance trends" description="Average assessment score by checkpoint" action={trendAction} />
          <div className="chart-wrap chart-tall" role="img" aria-label="Area chart showing average assessment score by checkpoint">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
                <defs><linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5578e8" stopOpacity={0.2} /><stop offset="95%" stopColor="#5578e8" stopOpacity={0.01} /></linearGradient></defs>
                <CartesianGrid stroke="#edf0f5" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="checkpoint" tickLine={false} axisLine={false} tick={{ fill: '#9aa5b5', fontSize: 11 }} dy={10} />
                <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickLine={false} axisLine={false} tick={{ fill: '#9aa5b5', fontSize: 10 }} />
                <ReferenceLine y={70} stroke="#e9b24c" strokeDasharray="5 5" label={{ value: '70% benchmark', fill: '#bd8e30', fontSize: 10, position: 'insideTopRight' }} />
                <Area type="monotone" dataKey="averageScore" stroke="#5578e8" strokeWidth={2.6} fill="url(#scoreFill)" activeDot={{ r: 5, fill: '#fff', stroke: '#5578e8', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel">
          <div className="chart-wrap chart-short" role="img" aria-label="Horizontal bar chart comparing average score by batch">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={batches} layout="vertical" margin={{ top: 6, right: 12, left: 5, bottom: 0 }}>
                <CartesianGrid stroke="#edf0f5" strokeDasharray="4 5" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: '#9aa5b5', fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={130} tickLine={false} axisLine={false} tick={{ fill: '#6f7d93', fontSize: 9 }} />
                <ReferenceLine x={70} stroke="#e9b24c" strokeDasharray="4 4" />
                <Bar dataKey="averageScore" fill="#6684e8" radius={[0, 5, 5, 0]} barSize={15} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="panel-footnote">Averages are descriptive and use synthetic assessment records.</div>
        </article>

        <article className="panel">
          <div className="skill-focus-list">
            {[...skills].sort((a, b) => a.averageScore - b.averageScore).map((skill) => (
              <div className="skill-focus-row" key={skill.skillArea}>
                <div className="skill-focus-top"><strong>{skill.skillArea}</strong><span>{skill.averageScore == null ? "N/A" : `${skill.averageScore}%`}</span></div>
                <div className="progress-track"><span className={skill.averageScore < 70 ? 'below' : ''} style={{ width: `${skill.averageScore}%` }} /></div>
                <div className="skill-focus-meta">{skill.learnersBelowBenchmark} learners below 70% benchmark</div>
              </div>
            ))}
          </div>
          <button className="text-button" type="button" onClick={onOpenSkillGaps}>Explore skill gaps <span aria-hidden="true">→</span></button>
        </article>

        <article className="panel review-panel">
          <PanelHeading
            title="Below benchmark"
            description={`${summary.belowBenchmark} learners have an average score under 70%. This is a descriptive review list, not an AI prediction.`}
            action={<button className="text-button" type="button" onClick={onOpenStudents}>View learners <span aria-hidden="true">→</span></button>}
          />
          <div className="review-list">
            {reviewLearners.map((learner) => (
              <div className="review-row" key={learner.studentId}>
                <div className="avatar avatar-small">{learner.fullName.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div>
                <div className="review-learner"><strong>{learner.fullName}</strong><span>{batchNames.get(learner.batchId)?.split(' · ')[0]}</span></div>
                <div className="review-score"><strong>{learner.averageScore}%</strong><span>avg. score</span></div>
              </div>
            ))}
          </div>
          <p className="review-note"><span className="note-dot" />Benchmark rule: average assessment score below 70%.</p>
        </article>
      </section>
    </>
  )
}

export default OverviewPage
