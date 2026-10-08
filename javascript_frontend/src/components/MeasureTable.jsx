/**
 * Two-column Measure / Value table, the shape the Streamlit reference
 * uses for its summary tables (st.dataframe of a Measure/Value frame).
 *
 * Values arrive pre-formatted as strings, because the reference formats
 * them too - nothing is computed here.
 */
export function MeasureTable({ rows = [] }) {
  if (!rows.length) {
    return null
  }

  return (
    <table className="measure-table">
      <thead>
        <tr>
          <th scope="col">Measure</th>
          <th scope="col">Value</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.measure}>
            <td>{row.measure}</td>
            <td className="measure-table__value">{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}