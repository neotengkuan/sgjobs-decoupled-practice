import { ChartCard, HorizontalBarChart } from '../charts/ChartKit.jsx'

/**
 * Average Salary by Job Function.
 *
 * The backend already restricted this to the top 15 job functions by job
 * count and returned them ordered by average salary, descending. Recharts
 * draws a category axis in data order, so that ordering is what appears
 * here - no client-side sorting, and no averaging.
 */
export function AverageSalaryByFunctionChart({ dataset }) {
  const data = dataset?.data || []

  return (
    <ChartCard
      title="Average Salary by Job Function"
      available={Boolean(dataset?.available)}
      isEmpty={!data.length}
      height={420}
    >
      <HorizontalBarChart
        data={data}
        categoryKey="Job Function"
        valueKey="Average Salary"
        xLabel="Average Salary (S$)"
      />
    </ChartCard>
  )
}