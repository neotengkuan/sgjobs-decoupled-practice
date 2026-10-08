import { ChartCard, HorizontalBarChart } from '../charts/ChartKit.jsx'
import { fmtNumber } from '../../utils/format.js'

/**
 * Tooltip for "Average Salary by Seniority".
 *
 * The reference tooltip lists the seniority plus three measures
 * (Average Salary and Median Salary at ,.0f, Jobs at ,) while the bar
 * only encodes the average, so it is rendered from the full row.
 */
function SenioritySalaryTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null
  }

  const row = payload[0]?.payload

  if (!row) {
    return null
  }

  return (
    <div className="tooltip-card">
      <p className="tooltip-card__title">{row['Seniority']}</p>
      <p>Average Salary: {fmtNumber(row['Average Salary'])}</p>
      <p>Median Salary: {fmtNumber(row['Median Salary'])}</p>
      <p>Jobs: {fmtNumber(row['Jobs'])}</p>
    </div>
  )
}

/**
 * Average Salary by Seniority.
 *
 * The backend grouped by seniority and returned the mean, the median and
 * the job count per row; none of it is recomputed here.
 *
 * Ordering: the backend returns rows in its groupby order, while the
 * reference chart's axis is pinned with sort="-x", i.e. descending by the
 * encoded value. So the rows are put in descending Average Salary order
 * to reproduce the reference's visible order. This is a display sort of
 * values the backend already computed - no averaging, no ranking rule.
 */
export function AverageSalaryBySeniorityChart({ dataset }) {
  const rows = [...(dataset?.data || [])].sort(
    (a, b) => (b['Average Salary'] ?? 0) - (a['Average Salary'] ?? 0),
  )

  return (
    <ChartCard
      title="Average Salary by Seniority"
      available={Boolean(dataset?.available)}
      isEmpty={!rows.length}
      height={360}
    >
      <HorizontalBarChart
        data={rows}
        categoryKey="Seniority"
        valueKey="Average Salary"
        xLabel="Average Salary (S$)"
        tooltip={{ content: SenioritySalaryTooltip }}
      />
    </ChartCard>
  )
}