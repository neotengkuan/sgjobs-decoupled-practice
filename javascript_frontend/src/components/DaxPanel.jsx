import { fmtDecimal, fmtNumber, fmtPercent } from '../utils/format.js'
import { Metric } from './KpiCards.jsx'

/**
 * The Power BI / DAX-equivalent measures, collapsible like the Streamlit
 * expander.
 *
 * In the Streamlit app these sit above the tabs, so they belong to the
 * always-visible Overview area rather than to a tab. They are rendered
 * from dax_measures, which /api/overview already returns.
 */
export function DaxPanel({ daxMeasures = {} }) {
  const measures = [
    ['Unique Job Postings', fmtNumber(daxMeasures.unique_job_postings)],
    ['Total Applications', fmtNumber(daxMeasures.total_applications)],
    [
      'Overall Applications / Vacancy',
      fmtDecimal(daxMeasures.overall_applications_per_vacancy, 2),
    ],
    ['High Opportunity Jobs', fmtNumber(daxMeasures.high_opportunity_jobs)],
    [
      'Average Application Rate',
      fmtPercent(daxMeasures.average_application_rate),
    ],
    [
      'Average Applications / Vacancy',
      fmtDecimal(daxMeasures.average_applications_per_vacancy, 2),
    ],
    [
      'Average Views / Vacancy',
      fmtDecimal(daxMeasures.average_views_per_vacancy, 2),
    ],
    [
      'Average Minimum Experience',
      fmtDecimal(daxMeasures.average_minimum_experience, 1, ' years'),
    ],
    [
      'Data Quality Issue Rate',
      fmtPercent(daxMeasures.data_quality_issue_rate),
    ],
    ['Repost Rate', fmtPercent(daxMeasures.repost_rate)],
  ]

  return (
    <details className="panel">
      <summary className="panel__summary">Power BI / DAX-equivalent measures</summary>

      <div className="metric-grid metric-grid--4">
        {measures.map(([label, value]) => (
          <Metric key={label} label={label} value={value} />
        ))}
      </div>
    </details>
  )
}