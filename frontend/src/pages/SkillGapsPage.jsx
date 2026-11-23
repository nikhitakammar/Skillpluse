import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import MetricCard from '../components/MetricCard.jsx'
import PageHeading from '../components/PageHeading.jsx'
import PanelHeading from '../components/PanelHeading.jsx'

function SkillGapsPage({ title, description, skills, summary }) {
  const sortedSkills = [...skills].sort((a, b) => a.averageScore - b.averageScore)
  const lowest = sortedSkills[0]
  const totalBelow = sortedSkills.reduce((sum, skill) => sum + skill.learnersBelowBenchmark, 0)

  return (
    <>
      <PageHeading title={title} description={description} />
      <section className="metrics-grid skills-metrics">
        <MetricCard label="Skill areas tracked" value={skills.length} detail="Across the selected batch scope" icon="◇" />
        <MetricCard label="Lowest-scoring skill" value={lowest?.skillArea ?? '—'} detail={`${lowest?.averageScore ?? 0}% average score`} icon="↓" tone="amber" />
        <MetricCard label="Below benchmark" value={totalBelow.toLocaleString()} detail="Learner-skill averages under 70%" icon="◎" tone="violet" />
        <MetricCard label="Benchmark" value="70%" detail={`${summary.activeLearners} learners in the selected scope`} icon="⌖" tone="mint" />
      </section>

      <section className="dashboard-grid skill-grid">
        <article className="panel panel-large">
          <PanelHeading title="Average score by skill area" description="Student averages compared with the review benchmark" />
          <div className="chart-wrap chart-skill" role="img" aria-label="Bar chart of average score for each skill area">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sortedSkills} margin={{ top: 18, right: 24, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#edf0f5" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="skillArea" tickLine={false} axisLine={false} tick={{ fill: '#6f7d93', fontSize: 11 }} dy={10} />
                <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickLine={false} axisLine={false} tick={{ fill: '#9aa5b5', fontSize: 10 }} />
                <Tooltip formatter={(value) => [`${value}%`, 'Average score']} contentStyle={{ border: '1px solid #e7ebf2', borderRadius: 10, fontSize: 12 }} />
                <ReferenceLine y={70} stroke="#e9b24c" strokeDasharray="5 5" label={{ value: '70% benchmark', fill: '#bd8e30', fontSize: 10, position: 'insideTopRight' }} />
                <Bar dataKey="averageScore" fill="#6684e8" radius={[5, 5, 0, 0]} barSize={42} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-caption"><span><i className="legend-dot legend-blue" />Average learner score</span><span><i className="legend-dash" />Review benchmark</span></div>
        </article>

        <article className="panel skill-table-panel">
          <PanelHeading title="Areas to review" description="Ranked by average learner score" />
          <div className="skill-review-list">
            {sortedSkills.map((skill, index) => (
              <div className="skill-review-row" key={skill.skillArea}>
                <span className="skill-rank">{String(index + 1).padStart(2, '0')}</span>
                <div className="skill-review-info"><strong>{skill.skillArea}</strong><span>{skill.learnersBelowBenchmark} learners below 70%</span></div>
                <strong className={skill.averageScore < 70 ? 'score-warn' : 'score-good'}>{skill.averageScore}%</strong>
              </div>
            ))}
          </div>
          <div className="descriptive-note"><span className="notice-mark" aria-hidden="true">i</span><p>This view summarizes assessment results. It does not use the AI support model or determine learner placement.</p></div>
        </article>
      </section>
    </>
  )
}

export default SkillGapsPage
