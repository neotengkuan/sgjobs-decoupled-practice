import { DataTable } from '../DataTable.jsx'

/**
 * The Team 6 review-rule table.
 *
 * Area / Review rule / Matching rows arrive in the reference's order and
 * with the counts already computed by the backend, which owns every
 * threshold. Rows are rendered in the order received - nothing is sorted or
 * recounted here.
 *
 * An empty list keeps the section heading and simply shows no table, which
 * is what the reference does when it collected no outlier measures.
 */
export function OutlierMeasuresTable({ measures = [] }) {
  return (
    <DataTable
      columns={['Area', 'Review rule', 'Matching rows']}
      rows={measures}
      numericColumns={['Matching rows']}
    />
  )
}