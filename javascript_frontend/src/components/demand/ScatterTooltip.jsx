import {
  fmtCurrency,
  fmtDecimal,
  fmtNumber,
  fmtPercent,
} from '../../utils/format.js'

/** Render one tooltip field with the reference's format for its kind. */
function renderValue(value, kind) {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }

  switch (kind) {
    case 'text':
      return String(value)
    case 'number':
      return fmtNumber(value)
    case 'currency':
      return fmtCurrency(value)
    case 'decimal1':
      return fmtDecimal(value, 1)
    case 'decimal2':
      return fmtDecimal(value, 2)
    case 'percent2':
      return fmtPercent(value, 2)
    default:
      return String(value)
  }
}

/**
 * Tooltip for "Salary vs Applications per Vacancy".
 *
 * `fields` comes from activeScatterTooltipFields(), so only the measures
 * the backend actually returned are listed - the same set the reference
 * tooltip shows. The first entry is used as the title, which is the
 * reference's behaviour for a nominal tooltip (the category first, then
 * the measures).
 */
export function ScatterTooltip({ active, payload, fields = [] }) {
  if (!active || !payload?.length) {
    return null
  }

  const row = payload[0]?.payload

  if (!row) {
    return null
  }

  const [heading, ...measures] = fields

  return (
    <div className="tooltip-card">
      {heading && (
        <p className="tooltip-card__title">
          {renderValue(row[heading.field], heading.kind)}
        </p>
      )}

      {measures.map((spec) => (
        <p key={spec.field}>
          {spec.title}: {renderValue(row[spec.field], spec.kind)}
        </p>
      ))}
    </div>
  )
}