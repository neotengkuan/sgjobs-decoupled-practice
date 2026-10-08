import { OpportunityBandChart } from './OpportunityBandChart.jsx'
import { TopJobFunctionsByOpportunityChart } from './TopJobFunctionsByOpportunityChart.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'

/**
 * Opportunity Analysis tab body.
 *
 * Layout follows the reference: the exploratory-score note, then the two
 * charts side by side.
 *
 * Availability flags come straight from the payload, so a chart is
 * omitted exactly when the backend marked it unavailable - including the
 * ranking caption, which the reference also keeps inside that branch.
 */
export function OpportunityAnalysisPanel({
  opportunity,
  loading,
  error,
  onRetry,
}) {
  if (loading && !opportunity) {
    return <LoadingState label="Loading Opportunity Analysis…" />
  }

  if (error && !opportunity) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Opportunity Analysis"
      />
    )
  }

  if (!opportunity) {
    return null
  }

  return (
    <>
      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <p className="content__meta">
        Opportunity Score is exploratory/indicative, not a validated
        predictive model.
      </p>

      <div className="chart-grid">
        <OpportunityBandChart dataset={opportunity.opportunity_band_counts} />
        <TopJobFunctionsByOpportunityChart
          dataset={opportunity.top_job_functions}
        />
      </div>
    </>
  )
}