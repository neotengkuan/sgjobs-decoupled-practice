import { DataTable } from '../DataTable.jsx'

/**
 * Filtered Job Records.
 *
 * Columns and row order come from the backend (it returns the reference's
 * display columns, in its order, filtered to those that exist). Nothing is
 * sorted, filtered or re-ordered here, and no paging controls are offered -
 * the reference shows only the first N matching rows.
 *
 * @param {{columns?: string[], rows?: object[]}} data
 */
export function RecordsTable({ data }) {
  return <DataTable columns={data?.columns || []} rows={data?.rows || []} />
}