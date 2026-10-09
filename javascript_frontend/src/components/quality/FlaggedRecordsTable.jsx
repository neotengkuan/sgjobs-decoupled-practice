import { DataTable } from '../DataTable.jsx'
import { fmtNumber } from '../../utils/format.js'

/**
 * The flagged-records table and its caption.
 *
 * CAPPING: only the rows in flagged_records.data are rendered, which the
 * backend already capped (meta.flagged_record_cap, default 500) after
 * filtering by the selected review population. No uncapped request is ever
 * made and nothing is sampled here.
 *
 * The caption quotes the backend's own cap and the true matching total, so
 * the wording stays correct even if the cap changes.
 */
export function FlaggedRecordsTable({ records = {} }) {
  const cap = records.cap
  const totalMatching = records.total_matching

  return (
    <>
      <p className="content__meta">
        Showing up to {fmtNumber(cap)} records from{' '}
        {fmtNumber(totalMatching)} matching rows in the current filter
        context.
      </p>

      <DataTable columns={records.columns || []} rows={records.data || []} />
    </>
  )
}