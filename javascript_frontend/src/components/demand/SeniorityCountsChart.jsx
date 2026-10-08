import { ChartCard, VerticalBarChart } from '../charts/ChartKit.jsx'

/**
 * Jobs by Seniority.
 *
 * Count semantics come straight from the backend: one count per seniority
 * group over the filtered rows. The backend returns them in value_counts
 * order, which is descending by Jobs, and the reference axis is pinned
 * with sort="-x" on the same measure - so the row order is used as-is and
 * no client-side sort is needed.
 *
 * The reference axis title on this chart is "Job Postings", not the
 * "Number of Jobs" used by the other count charts.
 */
export function SeniorityCountsChart({ dataset }) {
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Jobs by Seniority"
      available={Boolean(dataset?.available)}
      isEmpty={!data.length}
      height={360}
    >
      <VerticalBarChart
        data={data}
        categoryKey="Seniority"
        xLabel="Job Postings"
      />
    </ChartCard>
  )
}