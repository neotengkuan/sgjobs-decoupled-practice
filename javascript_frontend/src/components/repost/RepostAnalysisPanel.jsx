import { Metric } from '../KpiCards.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'
import { PostingStatusChart } from './PostingStatusChart.jsx'
import { SalaryByPostingStatusTable } from './SalaryByPostingStatusTable.jsx'
import { fmtNumber, fmtPercent } from '../../utils/format.js'

/**
 * Repost Analysis tab body.
 *
 * Layout follows the reference: the descriptive caption, three metric
 * cards, the Posting Status chart, then the salary-by-status table (which
 * the reference renders without a heading).
 *
 * Repost Rate is passed in from the Overview payload - the reference
 * computes it once and reuses it, and so does this app. Nothing here
 * recalculates is_reposted, any row count, or the rate.
 */
export function RepostAnalysisPanel({
  repost,
  repostRate,
  loading,
  error,
  stale = false,
  onRetry,
}) {
  if (loading && !repost) {
    return <LoadingState label="Loading Repost Analysis…" />
  }

  if (error && !repost) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Repost Analysis"
      />
    )
  }

  if (!repost) {
    return null
  }

  const kpis = repost.kpis || {}

  return (
    <>
      <StaleBanner show={stale} />

      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <p className="content__meta">
        Repost analysis is descriptive. A repost flag identifies repeat
        posting behaviour; it does not by itself explain why the job was
        reposted.
      </p>

      {/* Counts are job rows, so they are formatted with separators like
          the reference. They are NOT distinct job_post_id counts. */}
      <div className="metric-grid metric-grid--4">
        <Metric
          label="Reposted Rows"
          value={fmtNumber(kpis.reposted_rows)}
        />
        <Metric label="Repost Rate" value={fmtPercent(repostRate)} />
        <Metric
          label="Non-Reposted Rows"
          value={fmtNumber(kpis.non_reposted_rows)}
        />
      </div>

      <PostingStatusChart dataset={repost.posting_status_counts} />

      <SalaryByPostingStatusTable dataset={repost.salary_by_posting_status} />
    </>
  )
}