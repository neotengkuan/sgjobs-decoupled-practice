import { DataTable } from '../DataTable.jsx'

/**
 * One job's bridge rows, rendered under a bold label.
 *
 * The reference prints "All Job Functions from bridge" / "All Skills from
 * bridge" and the matching bridge frame beneath it. Every matching row is
 * shown, exactly as the backend returned it; the backend's own cap and
 * total_matching are carried in meta, and are shown when the cap bites.
 *
 * @param {string} label
 * @param {{columns?: string[], rows?: object[], meta?: object}} data
 */
export function JobBridgeTable({ label, data }) {
  const meta = data?.meta || {}
  const rows = data?.rows || []

  return (
    <>
      <p className="drill__label">
        <strong>{label}</strong>
      </p>

      {meta.truncated && (
        <p className="content__meta">
          Showing {meta.returned} of {meta.total_matching} rows (backend cap{' '}
          {meta.cap}).
        </p>
      )}

      <DataTable columns={data?.columns || []} rows={rows} />
    </>
  )
}