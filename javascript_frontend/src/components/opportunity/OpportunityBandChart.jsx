import { useMemo } from 'react'
import { ChartCard, VerticalBarChart } from '../charts/ChartKit.jsx'
import { orderByRank } from '../../utils/orderByRank.js'

/**
 * Axis order for the Opportunity Band chart: the reference pins the Vega
 * axis to exactly this list, so the band order never depends on the
 * counts. Recharts has no sort list, so orderByRank applies it to the
 * rows the backend already produced.
 */
const OPPORTUNITY_BAND_ORDER = ['Low', 'Moderate', 'Good', 'High']

const BAND_LABEL = 'Opportunity Band'

/**
 * Jobs by Opportunity Band.
 *
 * Counts come straight from opportunity_band_counts; nothing is counted
 * or classified here.
 */
export function OpportunityBandChart({ dataset }) {
  const data = useMemo(
    () => orderByRank(dataset?.data || [], BAND_LABEL, OPPORTUNITY_BAND_ORDER),
    [dataset],
  )

  return (
    <ChartCard
      title="Jobs by Opportunity Band"
      available={Boolean(dataset?.available)}
      isEmpty={!data.length}
      height={340}
    >
      <VerticalBarChart
        data={data}
        categoryKey={BAND_LABEL}
        xLabel={BAND_LABEL}
        yLabel="Number of Jobs"
      />
    </ChartCard>
  )
}