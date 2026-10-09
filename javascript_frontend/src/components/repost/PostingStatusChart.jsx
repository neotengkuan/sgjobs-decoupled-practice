import { ChartCard, VerticalBarChart } from '../charts/ChartKit.jsx'

/**
 * Jobs by Posting Status.
 *
 * ORDERING (deliberately left alone)
 * ---------------------------------
 * The backend built these counts with value_counts, so the rows arrive
 * ordered by descending Jobs, and the reference chart sets no axis sort -
 * it draws them in data order. So the bar order follows the counts and will
 * flip between filters when the larger group changes. That is inherited
 * behaviour, so no client-side ordering is applied.
 *
 * COUNT SEMANTICS: Jobs are job ROWS, not distinct job_post_id values.
 *
 * The reference gives this axis no title, and its two labels are short, so
 * the category axis is drawn horizontally here rather than rotated.
 */
export function PostingStatusChart({ dataset }) {
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Posting Status"
      available={Boolean(dataset?.available)}
      isEmpty={!data.length}
      height={350}
    >
      <VerticalBarChart
        data={data}
        categoryKey="Posting Status"
        xAngle={0}
        yLabel="Job Postings"
      />
    </ChartCard>
  )
}