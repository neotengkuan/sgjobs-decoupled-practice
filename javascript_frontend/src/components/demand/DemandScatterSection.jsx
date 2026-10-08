import { useMemo } from 'react'
import { ScatterChart } from '../charts/ChartKit.jsx'
import { ScatterTooltip } from './ScatterTooltip.jsx'
import { activeScatterTooltipFields } from './tooltipFields.js'
import { fmtNumber } from '../../utils/format.js'

/**
 * Colour encoding for the seniority levels, matching the reference's
 * categorical colour scale (Vega's "tableau10" first six entries, which
 * is where its #4C78A8 default comes from). The flat colour is the
 * reference's fallback when no seniority column is present.
 */
const SERIES_COLOURS = [
  '#4C78A8',
  '#F58518',
  '#E45756',
  '#72B7B2',
  '#54A24B',
  '#EECA3B',
  '#B279A2',
  '#FF9DA6',
  '#9D755D',
  '#BAB0AC',
]

const DEFAULT_COLOUR = '#4C78A8'
const DEFAULT_SERIES_NAME = 'Jobs'

/**
 * Split the returned rows into one series per seniority level, purely so
 * each level gets its own colour and legend entry - the way the
 * reference's colour encoding works. No value is counted or aggregated:
 * each row is passed through untouched.
 */
function buildSenioritySeries(rows, colourField) {
  if (!colourField) {
    return [{ name: DEFAULT_SERIES_NAME, rows, color: DEFAULT_COLOUR }]
  }

  const groups = new Map()

  for (const row of rows) {
    const key = row?.[colourField] ?? 'N/A'

    if (!groups.has(key)) {
      groups.set(key, [])
    }

    groups.get(key).push(row)
  }

  return [...groups.entries()].map(([name, groupRows], index) => ({
    name,
    rows: groupRows,
    color: SERIES_COLOURS[index % SERIES_COLOURS.length],
  }))
}

/**
 * Salary vs Applications per Vacancy, full width.
 *
 * Only the rows the backend returned are rendered. It already applied the
 * 25,000-row cap with a fixed seed, so nothing is sampled again here and
 * the sample stays reproducible across filter changes.
 *
 * The reference notes the sample in a caption; it says so only when a
 * sample was actually taken, and the number it quotes is the number of
 * rows plotted.
 */
export function DemandScatterSection({ dataset }) {
  const available = Boolean(dataset?.available)

  const fields = useMemo(() => dataset?.fields || [], [dataset])
  const data = useMemo(() => dataset?.data || [], [dataset])
  const sampled = Boolean(dataset?.sampled)
  const rowsBeforeSample = dataset?.rows_before_sample ?? 0
  const rowsSampled = dataset?.rows_sampled ?? 0

  const tooltipFields = useMemo(
    () => activeScatterTooltipFields(fields),
    [fields],
  )

  // The reference colours by seniority and falls back to a flat colour
  // when the column is absent; fields[] tells us which case we are in.
  const colourField = fields.includes('seniority_group')
    ? 'seniority_group'
    : null

  const series = useMemo(
    () => buildSenioritySeries(data, colourField),
    [data, colourField],
  )

  return (
    <section className="chart-card chart-card--wide">
      <h3 className="chart-card__title">Salary vs Applications per Vacancy</h3>

      {sampled && (
        <>
          <p className="chart-card__caption">
            Scatter plot displays a reproducible {fmtNumber(rowsSampled)}-row
            sample for browser performance; dashboard measures still use all
            filtered rows.
          </p>
          <p className="chart-card__caption">
            Sample drawn from {fmtNumber(rowsBeforeSample)} matching rows.
          </p>
        </>
      )}

      {!available ? null : !data.length ? (
        <div className="chart-card__empty" style={{ height: 500 }}>
          No data for the current filter selection.
        </div>
      ) : (
        <div className="chart-card__plot" style={{ height: 500 }}>
          <ScatterChart
            series={series}
            xKey="applications_per_vacancy"
            yKey="salary_midpoint"
            sizeKey="number_of_vacancies"
            xLabel="Applications per Vacancy"
            yLabel="Salary Midpoint (S$)"
            sizeLabel="Vacancies"
            tooltip={{
              content: (props) => (
                <ScatterTooltip {...props} fields={tooltipFields} />
              ),
            }}
            showLegend={Boolean(colourField)}
          />
        </div>
      )}
    </section>
  )
}