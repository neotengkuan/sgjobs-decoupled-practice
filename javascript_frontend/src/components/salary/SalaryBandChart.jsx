import { useMemo } from 'react'
import { ChartCard, VerticalBarChart } from '../charts/ChartKit.jsx'

/**
 * Axis order for the Salary Band chart.
 *
 * The reference chart pins the category axis to this exact list, which is
 * display order only - it says nothing about the counts, which the backend
 * already computed. Recharts has no equivalent "sort by given list"
 * option, so the rows the backend returned are put in this order here.
 *
 * Bands that are absent from the data simply do not appear; a band the
 * backend returns that is missing from this list keeps its incoming order
 * and is appended at the end.
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

function orderByBandRank(rows) {
  const rank = new Map(
    SALARY_BAND_ORDER.map((band, index) => [band, index]),
  )

  return [...rows].sort((a, b) => {
    const rankA = rank.get(a[SALARY_BAND_LABEL])
    const rankB = rank.get(b[SALARY_BAND_LABEL])

    // Unlisted bands sink to the end, keeping their relative order.
    if (rankA === undefined || rankB === undefined) {
      if (rankA === undefined && rankB === undefined) {
        return 0
      }

      return rankA === undefined ? 1 : -1
    }

    return rankA - rankB
  })
}

/**
 * Jobs by Salary Band.
 *
 * Counts come straight from salary_band_counts; nothing is counted here.
 */
export function SalaryBandChart({ dataset }) {
  const data = useMemo(
    () => orderByBandRank(dataset?.data || []),
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