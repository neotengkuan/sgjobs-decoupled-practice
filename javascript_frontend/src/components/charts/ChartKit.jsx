/**
 * Shared Recharts plumbing.
 *
 * The data always arrives pre-aggregated from the API, so these components
 * never group, sum or count anything - they only render the rows the
 * backend produced, in the order it produced them.
 *
 * RESPONSIVE SIZING
 * -----------------
 * Each chart component below puts ResponsiveContainer DIRECTLY around its
 * own Recharts chart. That is required: ResponsiveContainer measures its
 * parent and clones its immediate child with the computed width/height, so
 * only a Recharts chart component can receive them. A wrapper component in
 * between swallows the props and the chart renders at 0x0.
 *
 * ChartCard therefore does NOT contain a ResponsiveContainer. It only
 * supplies the fixed-height plot area, and each chart fills that box.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtNumber } from '../../utils/format.js'

/** Thousands-separated tooltip values, as the reference tooltips show. */
function valueFormatter(value) {
  return fmtNumber(value)
}

/**
 * Build a Recharts axis-label prop, or undefined when there is no title.
 * The reference leaves the category axis of the horizontal charts
 * untitled, so that axis keeps getting no label.
 */
function axisLabel(value, position, angle, offset) {
  if (!value) {
    return undefined
  }

  return { value, position, angle, offset, fontSize: 12 }
}

/**
 * Build the tooltip element for a bar chart.
 *
 * `tooltip` is optional and defaults to the existing behaviour, so the
 * Overview and Salary charts are unaffected:
 *   - tooltip.formatValue -> value formatter (default: thousands separated)
 *   - tooltip.content     -> custom renderer, for a reference tooltip that
 *                            shows more than a label and one value
 */
function barTooltip(tooltip) {
  if (tooltip?.content) {
    return <Tooltip content={tooltip.content} />
  }

  if (tooltip?.formatValue) {
    return <Tooltip formatter={tooltip.formatValue} />
  }

  return <Tooltip formatter={valueFormatter} />
}

/**
 * A chart block: title, an optional note, and a fixed-height plot area
 * for the child chart.
 *
 * Renders nothing but the title when the backend marked the dataset
 * unavailable, and a placeholder when it returned no rows - matching the
 * reference, which shows a heading and no chart in those cases.
 *
 * `caption` is rendered between the title and the plot area, so a note
 * about the ranking sits above the chart the way it does in the
 * reference rather than inside the plot box.
 *
 * Sizing note: this element gives the box a definite width and height; the
 * chart inside fills it via its own ResponsiveContainer.
 */
export function ChartCard({
  title,
  available = true,
  isEmpty = false,
  height = 340,
  caption,
  children,
}) {
  return (
    <section className="chart-card">
      <h3 className="chart-card__title">{title}</h3>

      {!available ? null : isEmpty ? (
        <>
          {caption}
          <div className="chart-card__empty" style={{ height }}>
            No data for the current filter selection.
          </div>
        </>
      ) : (
        <>
          {caption}
          <div className="chart-card__plot" style={{ height }}>
            {children}
          </div>
        </>
      )}
    </section>
  )
}

/**
 * Vertical bar chart, used by "Jobs by Employment Type" and
 * "Jobs by Salary Band".
 *
 * Rows arrive in value_counts order, which is descending by Jobs, so the
 * left-to-right order matches the reference chart's descending sort.
 */
export function VerticalBarChart({
  data,
  categoryKey,
  valueKey = 'Jobs',
  xLabel,
  yLabel,
  tooltip,
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 8, right: 16, bottom: 78, left: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey={categoryKey}
          interval={0}
          angle={-30}
          textAnchor="end"
          height={70}
          tick={{ fontSize: 12 }}
          label={axisLabel(xLabel, 'insideBottom', 0, 58)}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          label={axisLabel(yLabel, 'insideLeft', -90, 0)}
        />
        {barTooltip(tooltip)}
        <Bar dataKey={valueKey} fill="#4C78A8" />
      </BarChart>
    </ResponsiveContainer>
  )
}

/**
 * Horizontal bar chart, used by the two "Top N job function" charts.
 *
 * Recharts ellipsises tick labels that exceed the axis width, so
 * labelWidth is generous for long job-function names.
 */
export function HorizontalBarChart({
  data,
  categoryKey,
  valueKey = 'Jobs',
  labelWidth = 260,
  xLabel,
  yLabel,
  tooltip,
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 24, bottom: 22, left: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 12 }}
          label={axisLabel(xLabel, 'insideBottom', 0, -2)}
        />
        <YAxis
          type="category"
          dataKey={categoryKey}
          width={labelWidth}
          tick={{ fontSize: 12 }}
          interval={0}
          label={axisLabel(yLabel, 'insideLeft', -90, 0)}
        />
        {barTooltip(tooltip)}
        <Bar dataKey={valueKey} fill="#4C78A8" />
      </BarChart>
    </ResponsiveContainer>
  )
}

/**
 * Monthly line chart, used by "Jobs Over Time".
 *
 * No sorting is applied here on purpose: the backend returns the months
 * already ordered, which is what the reference chart relies on.
 */
export function MonthlyLineChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, bottom: 72, left: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="month_year"
          angle={-45}
          textAnchor="end"
          height={70}
          interval="preserveStartEnd"
          tick={{ fontSize: 12 }}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip formatter={valueFormatter} />
        <Line
          type="monotone"
          dataKey="Jobs"
          stroke="#4C78A8"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}