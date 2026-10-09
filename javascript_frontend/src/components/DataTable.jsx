/**
 * Plain semantic table driven by a payload's own column list.
 *
 * Used where the reference renders st.dataframe: the review-rule table and
 * the flagged-records table. No table library is involved.
 *
 * Cells are rendered exactly as the API returned them - numbers stay
 * numbers, and a missing value shows as an empty cell, the way a dataframe
 * renders a null. Nothing is formatted or computed here.
 */
export function DataTable({ columns = [], rows = [], numericColumns = [] }) {
  if (!columns.length || !rows.length) {
    return null
  }

  const numeric = new Set(numericColumns)

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className={numeric.has(column) ? 'data-table__num' : undefined}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            // Rows have no stable key in the payload, so the position is
            // used; the tables here are short and replaced wholesale.
            // eslint-disable-next-line react/no-array-index-key
            <tr key={`${columns[0]}-${index}`}>
              {columns.map((column) => {
                const value = row?.[column]

                return (
                  <td
                    key={column}
                    className={
                      numeric.has(column) ? 'data-table__num' : undefined
                    }
                  >
                    {value === null || value === undefined ? '' : String(value)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}