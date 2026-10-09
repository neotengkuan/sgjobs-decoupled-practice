import { DataTable } from '../DataTable.jsx'

/**
 * Salary by Posting Status.
 *
 * COUNT SEMANTICS, as defined by the backend:
 *   Jobs            - the group size, so it counts every job row in that
 *                     status, including rows that have no salary;
 *   Average Salary  - mean over the rows that DO have a salary_midpoint;
 *   Median Salary   - median over the same rows.
 * Jobs can therefore exceed the number of salary-bearing rows in a group.
 * These are job-row counts, not distinct job_post_id values.
 *
 * ORDERING (deliberately left alone)
 * ---------------------------------
 * These rows come from a groupby, so they arrive in group-key order -
 * unlike the Posting Status chart, whose rows are ordered by descending
 * count. The two are intentionally NOT harmonised, because the reference
 * does not harmonise them either.
 *
 * Values are printed exactly as returned: the reference shows this as a
 * numeric dataframe, so counts stay unformatted and salaries are not
 * rounded or given a currency symbol.
 */
export function SalaryByPostingStatusTable({ dataset }) {
  return (
    <DataTable
      columns={[
        'Posting Status',
        'Jobs',
        'Average Salary',
        'Median Salary',
      ]}
      rows={dataset?.data || []}
      numericColumns={['Jobs', 'Average Salary', 'Median Salary']}
    />
  )
}