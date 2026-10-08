import { SalaryBandChart } from './SalaryBandChart.jsx'
import { AverageSalaryByFunctionChart } from './AverageSalaryByFunctionChart.jsx'
import { SalarySummaryTable } from './SalarySummaryTable.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'

/**
 * Salary Analysis tab body.
 *
 * Layout follows the reference: two charts side by side, then the Salary
 * Summary heading with its table underneath (the table is outside the
 * two-column row in the reference too).
 *
 * Availability flags come straight from the payload, so a chart is
 * omitted exactly when the backend marked it unavailable.
 */
export function SalaryAnalysisPanel({
  salary,
  loading,
  error,
  stale = false,
  onRetry,
}) {
  if (loading && !salary) {
    return <LoadingState label="Loading Salary Analysis…" />
  }

  if (error && !salary) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Salary Analysis"
      />
    )
  }

  if (!salary) {
    return null
  }

  return (
    <>
      <StaleBanner show={stale} />

      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <div className="chart-grid">
        <SalaryBandChart dataset={salary.salary_band_counts} />
        <AverageSalaryByFunctionChart
          dataset={salary.average_salary_by_job_function}
        />
      </div>

      <h2 className="section-title">Salary Summary</h2>

      <SalarySummaryTable summary={salary.summary} />
    </>
  )
}