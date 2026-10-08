import {
  ChartCard,
  HorizontalBarChart,
  MonthlyLineChart,
  VerticalBarChart,
} from './ChartKit.jsx'

/**
 * The four Overview charts.
 *
 * Each block reads one dataset out of the /api/overview/charts payload.
 * `available` comes straight from the backend and reproduces the
 * reference's render condition, so a chart disappears exactly when the
 * Streamlit version would not draw it.
 */
export function OverviewCharts({ charts = {} }) {
  const employmentType = charts.employment_type || {}
  const topJobFunctions = charts.top_job_functions || {}
  const jobsOverTime = charts.jobs_over_time || {}
  const topVacancies = charts.top_job_functions_by_vacancies || {}

  return (
    <div className="chart-grid">
      {/* Jobs by Employment Type */}
      <ChartCard
        title="Jobs by Employment Type"
        available={Boolean(employmentType.available)}
        isEmpty={!employmentType.data?.length}
        height={340}
      >
        <VerticalBarChart
          data={employmentType.data || []}
          categoryKey="Employment Type"
        />
      </ChartCard>

      {/* Top 15 Job Functions */}
      <ChartCard
        title="Top 15 Job Functions"
        available={Boolean(topJobFunctions.available)}
        isEmpty={!topJobFunctions.data?.length}
        height={400}
      >
        <HorizontalBarChart
          data={topJobFunctions.data || []}
          categoryKey="Job Function"
        />
      </ChartCard>

      {/* Jobs Over Time */}
      <ChartCard
        title="Jobs Over Time"
        available={Boolean(jobsOverTime.available)}
        isEmpty={!jobsOverTime.data?.length}
        height={340}
      >
       <MonthlyLineChart data={jobsOverTime.data || []} />
      </ChartCard>

      {/* Top 10 Job Functions by Vacancies */}
      <ChartCard
        title="Top 10 Job Functions by Vacancies"
        available={Boolean(topVacancies.available)}
        isEmpty={!topVacancies.data?.length}
        height={400}
      >
        <HorizontalBarChart
          data={topVacancies.data || []}
          categoryKey="Job Function"
          valueKey="Vacancies"
        />
      </ChartCard>
    </div>
  )
}
