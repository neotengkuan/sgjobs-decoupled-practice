import { fmtDecimal, fmtNumber } from '../../utils/format.js'

/**
 * Custom tooltip for "Top Job Functions by Opportunity Score".
 *
 * The reference tooltip carries three fields - Job Function, Average
 * Opportunity Score with one decimal, and Jobs with thousands separators
 * - while the bar series only encodes the score. So it is rendered here
 * from the full row Recharts hands over in payload[0].payload.
 *
 * Both numbers are already computed by the backend; only formatting is
 * done here, matching the reference's d3 formats (.1f and ,).
 */
export function OpportunityTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null
  }

  const row = payload[0]?.payload

  if (!row) {
    return null
  }

  return (
    <div className="tooltip-card">
      <p className="tooltip-card__title">{row['Job Function']}</p>
      <p>
        Average Opportunity Score:{' '}
        {fmtDecimal(row['Average Opportunity Score'], 1)}
      </p>
      <p>Jobs: {fmtNumber(row['Jobs'])}</p>
    </div>
  )
}