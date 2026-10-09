import { ChartCard, HorizontalBarChart } from '../charts/ChartKit.jsx'
import { InfoNote } from '../States.jsx'

/**
 * Top Skills by Job Postings.
 *
 * COUNT SEMANTICS and ORDERING are identical to TopCategoriesChart: the
 * backend counted DISTINCT job postings per skill and returned them
 * descending, capped at the top 15. A job with four skills contributes 1 to
 * each of those four skills, and is never counted twice for the same skill.
 * Nothing is counted, joined or deduplicated here.
 */
export function TopSkillsChart({ dataset }) {
  const available = Boolean(dataset?.available)
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Top Skills by Job Postings"
      available={available}
      isEmpty={!data.length}
      height={420}
      unavailableNote={
        <InfoNote>
          Skill bridge is unavailable or expected columns are missing.
        </InfoNote>
      }
    >
      <HorizontalBarChart
        data={data}
        categoryKey="Skill"
        valueKey="Job Postings"
        xLabel="Unique Job Postings"
        labelWidth={300}
      />
    </ChartCard>
  )
}