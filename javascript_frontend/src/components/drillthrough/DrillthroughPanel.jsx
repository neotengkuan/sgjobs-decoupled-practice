import { RecordsTable } from './RecordsTable.jsx'
import { JobDetailBlock } from './JobDetailBlock.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'
import { ROWS_TO_DISPLAY_OPTIONS } from '../../hooks/useDrillthrough.js'

/**
 * Detail Drillthrough tab body.
 *
 * Layout follows the reference: the "Filtered Job Records" heading with its
 * rows selector and record table, a divider, then "Job Drillthrough" with
 * the job-id selector and the selected job's detail.
 *
 * The Job Drillthrough section appears only when the backend reports job
 * ids available, which is the reference's guard that a job-id column exists
 * and the filtered selection has rows.
 */
export function DrillthroughPanel({ drill }) {
  const {
    rowsToDisplay,
    setRowsToDisplay,
    selectedJobId,
    selectJobId,
    records,
    ids,
    detail,
    categories,
    skills,
  } = drill

  const jobIds = ids.data?.job_ids
  const idsAvailable = Boolean(ids.data?.meta?.available)

  return (
    <>
      <h2 className="section-title">Filtered Job Records</h2>

      <label className="field">
        <span className="field__label">Rows to display</span>
        <select
          className="field__control"
          value={rowsToDisplay}
          onChange={(event) => setRowsToDisplay(Number(event.target.value))}
        >
          {ROWS_TO_DISPLAY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <StaleBanner show={records.stale} />
      <ErrorBanner error={records.error} onRetry={records.refetch} />

      {records.loading && !records.data && (
        <LoadingState label="Loading job records…" />
      )}

      <RecordsTable data={records.data} />

      <hr className="divider" />

      <h2 className="section-title">Job Drillthrough</h2>

      <StaleBanner show={ids.stale} />
      <ErrorBanner error={ids.error} onRetry={ids.refetch} />

      {ids.loading && !ids.data && (
        <LoadingState label="Loading job ids…" />
      )}

      {idsAvailable ? (
        <>
          <label className="field">
            <span className="field__label">Select Job ID</span>
            <select
              className="field__control"
              value={selectedJobId || ''}
              onChange={(event) => selectJobId(event.target.value)}
            >
              {/* Duplicates are kept exactly as the backend returned them:
                  a job with several rows appears several times, which is
                  what the reference selector does. */}
              {jobIds.map((jobId, index) => (
                // Duplicate ids share a value, so the position is the only
                // stable key here.
                // eslint-disable-next-line react/no-array-index-key
                <option key={`${jobId}-${index}`} value={jobId}>
                  {jobId}
                </option>
              ))}
            </select>
          </label>

          {detail.loading && !detail.data && (
            <LoadingState label="Loading job detail…" />
          )}

          <JobDetailBlock
            detail={detail}
            categories={categories}
            skills={skills}
          />
        </>
      ) : null}

      {!idsAvailable && !ids.loading && !ids.error && (
        <p className="content__meta">
          No job id available for the current filter selection.
        </p>
      )}
    </>
  )
}