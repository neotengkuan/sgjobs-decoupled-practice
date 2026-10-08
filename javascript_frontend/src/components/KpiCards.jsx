import { fmtCurrency, fmtNumber } from '../utils/format.js'

/**
 * One metric tile.
 */
export function Metric({ label, value, tone = '' }) {
  return (
    <div className={`metric ${tone ? `metric--${tone}` : ''}`}>
      <span className="metric__label">{label}</span>
      <span className="metric__value">{value}</span>
    </div>
  )
}

/**
 * The five primary KPI cards, in the Streamlit order.
 *
 * Values arrive already computed from /api/overview; this only formats.
 */
export function KpiCards({ primaryKpis = {} }) {
  return (
    <div className="metric-grid metric-grid--5">
      <Metric label="Total Jobs" value={fmtNumber(primaryKpis.total_jobs)} />
      <Metric
        label="Average Salary"
        value={fmtCurrency(primaryKpis.average_salary)}
      />
      <Metric
        label="Median Salary"
        value={fmtCurrency(primaryKpis.median_salary)}
      />
      <Metric
        label="Total Vacancies"
        value={fmtNumber(primaryKpis.total_vacancies)}
      />
      <Metric
        label="Avg Opportunity Score"
        value={
          primaryKpis.avg_opportunity === null ||
          primaryKpis.avg_opportunity === undefined
            ? 'N/A'
            : primaryKpis.avg_opportunity.toFixed(1)
        }
      />
    </div>
  )
}

/**
 * The four bridge KPI cards.
 *
 * The backend measures these on the FULL bridge tables, so they do not
 * move when a Job Function (Bridge) or Skill filter is applied. That is
 * the reference behaviour and is kept as-is.
 */
export function BridgeKpis({ bridgeKpis = {} }) {
  return (
    <div className="metric-grid metric-grid--4">
      <Metric
        label="Distinct Categories"
        value={fmtNumber(bridgeKpis.distinct_categories)}
      />
      <Metric
        label="Category Job Postings"
        value={fmtNumber(bridgeKpis.category_job_postings)}
      />
      <Metric
        label="Distinct Skills"
        value={fmtNumber(bridgeKpis.distinct_skills)}
      />
      <Metric
        label="Skill Job Postings"
        value={fmtNumber(bridgeKpis.skill_job_postings)}
      />
    </div>
  )
}