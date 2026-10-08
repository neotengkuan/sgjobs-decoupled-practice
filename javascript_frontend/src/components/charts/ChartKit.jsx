/**
 * Shared Recharts plumbing.
 *
 * The data always arrives pre-aggregated from /api/overview/charts, so
 * these components never group, sum or count anything - they only render
 * the rows the backend produced, in the order it produced them.
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
 * A chart block: optional subtitle, a fixed-height plot area, or nothing
 * at all when the backend marked the dataset unavailable.
 */
export function ChartCard({
  title,
  available = true,
  isEmpty = false,
  height = 340,
  children,
}) {
  return (
    <section className="chart-card">
      <h3 className="chart-card__title">{title}</h3>

      {!available ? null : isEmpty ? (
        <div className="chart-card__empty" style={{ height }}>
          No data for the current filter selection.
        </div>
      ) : (
        <div style={{ width: '100%', height }}>
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}

/**
 * Vertical bar chart, used by "Jobs by Employment Type".
 *
 * Rows arrive in value_counts order, which is descending by Jobs, so the
 * left-to-right order matches the reference chart's descending sort.
 */
export function VerticalBarChart({ data, categoryKey, valueKey = 'Jobs' }) {
  return (
    <BarChart data={data} margin={{ top: 8, right: 16, bottom: 72, left: 8 }}>
      <CartesianGrid strokeDasharray="3 3" vertical={false} />
      <XAxis
        dataKey={categoryKey}
        interval={0}
        angle={-30}
        textAnchor="end"
        height={70}
        tick={{ fontSize: 12 }}
      />
      <YAxis tick={{ fontSize: 12 }} />
      <Tooltip formatter={valueFormatter} />
      <Bar dataKey={valueKey} fill="#4C78A8" />
    </BarChart>
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
  height = 400,
  labelWidth = 260,
}) {
  return (
    <BarChart
      data={data}
      layout="vertical"
      margin={{ top: 8, right: 24, bottom: 8, left: 8 }}
    >
      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
      <XAxis type="number" tick={{ fontSize: 12 }} />
      <YAxis
        type="category"
        dataKey={categoryKey}
        width={labelWidth}
        tick={{ fontSize: 12 }}
        interval={0}
      />
      <Tooltip formatter={valueFormatter} />
      <Bar dataKey={valueKey} fill="#4C78A8" />
    </BarChart>
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
    <LineChart data={data} margin={{ top: 8, right: 16, bottom: 72, left: 8 }}>
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
  )
}