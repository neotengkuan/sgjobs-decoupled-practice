import { ChartCard, HorizontalBarChart } from '../charts/ChartKit.jsx'
import { InfoNote } from '../States.jsx'

/**
 * Top Categories by Job Postings.
 *
 * COUNT SEMANTICS (decided by the backend, not here)
 * ------------------------------------------------
 * "Job Postings" is the number of DISTINCT job_post_id values attached to
 * a category, not the number of bridge rows. The bridges are multi-label,
 * so one job can carry several categories and several skills - it adds 1 to
 * each of its categories, and never more than 1 to any single category.
 * The backend does that counting; this component only plots the result.
 *
 * ORDERING
 * --------
 * The backend returned these already sorted descending by Job Postings and
 * capped at the top 15, which is what the reference axis produces with
 * sort="-x" on the same measure. The rows are therefore used in the order
 * received - no client-side ranking.
 *
 * Axis label width is generous because official Job Function names are
 * often long; Recharts ellipsises anything wider.
 */
export function TopCategoriesChart({ dataset }) {
  const available = Boolean(dataset?.available)
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Top Categories by Job Postings"
      available={available}
      isEmpty={!data.length}
      height={420}
      unavailableNote={
        <InfoNote>
          Category bridge is unavailable or expected columns are missing.
        </InfoNote>
      }
    >
      <HorizontalBarChart
        data={data}
        categoryKey="Category"
        valueKey="Job Postings"
        xLabel="Unique Job Postings"
        labelWidth={300}
      />
    </ChartCard>
  )
}