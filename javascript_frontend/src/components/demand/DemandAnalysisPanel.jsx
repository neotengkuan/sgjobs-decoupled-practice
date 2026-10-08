import { SeniorityCountsChart } from './SeniorityCountsChart.jsx'
import { AverageSalaryBySeniorityChart } from './AverageSalaryBySeniorityChart.jsx'
import { DemandScatterSection } from './DemandScatterSection.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'

/**
 * Demand & Seniority tab body.
 *
 * Layout follows the reference: the descriptive caption, the two seniority
 * charts side by side, then the full-width scatter with its sample note.
 *
 * Availability flags come straight from the payload.
 */
export function DemandAnalysisPanel({
  demand,
  loading,
  error,
  stale = false,
  onRetry,
}) {
  if (loading && !demand) {
    return <LoadingState label="Loading Demand & Seniority…" />
  }

  if (error && !demand) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Demand & Seniority"
      />
    )
  }

  if (!demand) {
    return null
  }

  return (
    <>
      <StaleBanner show={stale} />

      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <p className="content__meta">
        Demand measures mirror the Power BI business view. The scatter plot
        is descriptive; it does not imply causation.
      </p>

      <div className="chart-grid">
        <SeniorityCountsChart dataset={demand.seniority_counts} />
        <AverageSalaryBySeniorityChart
          dataset={demand.average_salary_by_seniority}
        />
      </div>

      <DemandScatterSection dataset={demand.salary_vs_applications} />
    </>
  )
}