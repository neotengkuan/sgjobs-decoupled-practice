import { useMemo } from 'react'
import { ChartCard, VerticalBarChart } from '../charts/ChartKit.jsx'
import { orderByRank } from '../../utils/orderByRank.js'

/**
 * Axis order for the Salary Band chart.
 *
 * The reference pins the Vega category axis to exactly this list, which is
 * display order only - it says nothing about the counts, which the backend
 * already computed. The ordering algorithm lives in the shared
 * orderByRank helper, also used by the Opportunity Band chart.
 */
const SALARY_BAND_ORDER = [
  '< 3K',
  '3K–5K',
  '5K–7K',
  '7K–10K',
  '10K+',
  'Unknown',
]

const SALARY_BAND_LABEL = 'Salary Band'

/**
 * Jobs by Salary Band.
 *
 * Counts come straight from salary_band_counts; nothing is counted here.
 */
export function SalaryBandChart({ dataset }) {
  const data = useMemo(
    () =>
      orderByRank(dataset?.data || [], SALARY_BAND_LABEL, SALARY_BAND_ORDER),
    [dataset],
  )

  return (
    <ChartCard
      title="Jobs by Salary Band"
      available={Boolean(dataset?.available)}
      isEmpty={!data.length}
      height={340}
    >
      <VerticalBarChart
        data={data}
        categoryKey={SALARY_BAND_LABEL}
        xLabel={SALARY_BAND_LABEL}
        yLabel="Number of Jobs"
      />
    </ChartCard>
  )
}