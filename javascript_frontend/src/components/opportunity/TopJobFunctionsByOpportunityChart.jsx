import { ChartCard, HorizontalBarChart } from '../charts/ChartKit.jsx'
import { OpportunityTooltip } from './OpportunityTooltip.jsx'
import { fmtNumber } from '../../utils/format.js'

/**
 * The ranking caption.
 *
 * Which of the reference's two captions applies is decided entirely by the
 * backend: fallback_applied means no job function reached the sample-size
 * floor, so every available function is listed instead. Otherwise min_jobs
 * is the floor that was applied and is reported back verbatim.
 */
function RankingCaption({ minJobs, fallbackApplied }) {
  if (fallbackApplied) {
    return (
      <p className="chart-card__caption">
        No job function met the minimum sample-size rule for this filter
        selection, so all available functions are shown.
      </p>
    )
  }

  return (
    <p className="chart-card__caption">
      Ranking uses job functions with at least {fmtNumber(minJobs)} matching
      jobs.
    </p>
  )
}

/**
 * Top Job Functions by Opportunity Score.
 *
 * The backend already restricted this to the top 15 job functions and
 * returned them ordered by average score, descending. Recharts draws a
 * category axis in data order, so that ordering appears as-is: no
 * scoring, ranking or averaging happens here.
 */
export function TopJobFunctionsByOpportunityChart({ dataset }) {
  const available = Boolean(dataset?.available)
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Top Job Functions by Opportunity Score"
      available={available}
      isEmpty={!data.length}
      height={420}
      caption={
        available ? (
          <RankingCaption
            minJobs={dataset?.min_jobs}
            fallbackApplied={Boolean(dataset?.fallback_applied)}
          />
        ) : null
      }
    >
      <HorizontalBarChart
        data={data}
        categoryKey="Job Function"
        valueKey="Average Opportunity Score"
        xLabel="Average Opportunity Score"
        tooltip={{ content: OpportunityTooltip }}
      />
    </ChartCard>
  )
}