import { MeasureTable } from '../MeasureTable.jsx'
import { fmtCurrency, fmtNumber } from '../../utils/format.js'

/**
 * The Salary Summary table.
 *
 * The five measures, their labels and their order are the reference's.
 * Every value is computed by the backend; only the display formatting
 * happens here, using the same formatters as the Overview KPIs.
 */
export function SalarySummaryTable({ summary }) {
  if (!summary?.available) {
    return null
  }

  const rows = [
    {
      measure: 'Jobs with salary data',
      value: fmtNumber(summary.jobs_with_salary_data),
    },
    {
      measure: 'Average salary',
      value: fmtCurrency(summary.average_salary),
    },
    {
      measure: 'Median salary',
      value: fmtCurrency(summary.median_salary),
    },
    {
      measure: 'Minimum salary midpoint',
      value: fmtCurrency(summary.minimum_salary_midpoint),
    },
    {
      measure: 'Maximum salary midpoint',
      value: fmtCurrency(summary.maximum_salary_midpoint),
    },
  ]

  return <MeasureTable rows={rows} />
}