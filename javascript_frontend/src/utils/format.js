/**
 * Display formatters.
 *
 * These mirror the Streamlit frontend's fmt_* helpers so both frontends
 * render identical strings from identical numbers. Formatting only: no
 * measure is computed here.
 */

const NUMBER_FORMAT = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
})

function isMissing(value) {
  return (
    value === null ||
    value === undefined ||
    (typeof value === 'number' && Number.isNaN(value))
  )
}

/** 1234567 -> "1,234,567"; null -> "N/A" */
export function fmtNumber(value) {
  return isMissing(value) ? 'N/A' : NUMBER_FORMAT.format(value)
}

/** 5123.4 -> "S$5,123"; null -> "N/A" */
export function fmtCurrency(value) {
  return isMissing(value) ? 'N/A' : `S$${NUMBER_FORMAT.format(value)}`
}

/** 0.0834 -> "8.3%"; null -> "N/A" */
export function fmtPercent(value) {
  return isMissing(value) ? 'N/A' : `${(value * 100).toFixed(1)}%`
}

/** 61.24 -> "61.2", 2 decimals -> "61.24"; null -> "N/A" */
export function fmtDecimal(value, places = 1, suffix = '') {
  return isMissing(value) ? 'N/A' : `${value.toFixed(places)}${suffix}`
}

/**
 * Note on fmtPercent: Python's f"{x:.1f}" rounds half-to-even while JS
 * toFixed() rounds half-away-from-zero on the exact binary value. They
 * can differ in the last displayed digit when a rate lands exactly on a
 * .x5 boundary, which is vanishingly rare for a ratio of this kind.
 */