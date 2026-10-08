import { useDashboardData } from './hooks/useDashboardData.js'
import { FilterSidebar } from './components/FilterSidebar.jsx'
import { BridgeKpis, KpiCards } from './components/KpiCards.jsx'
import { DaxPanel } from './components/DaxPanel.jsx'
import { OverviewCharts } from './components/charts/OverviewCharts.jsx'
import { ErrorBanner, LoadingState } from './components/States.jsx'
import { fmtNumber } from './utils/format.js'
import { API_BASE_URL } from './api/client.js'

/**
 * SGJobs Overview page.
 *
 * This component and its children only:
 *   - hold the sidebar selections in component state,
 *   - call the three Overview endpoints,
 *   - render whatever JSON comes back.
 *
 * There is no filtering, aggregation or scoring here. The 10 filters, the
 * KPI values and the chart datasets are all decided by FastAPI.
 */
export default function App() {
  const {
    descriptors,
    selections,
    filtersState,
    overview,
    charts,
    overviewState,
    chartsState,
    isLoading,
    setFilterValues,
    resetFilters,
    refresh,
  } = useDashboardData()

  const meta = overview?.meta || {}
  const primaryKpis = overview?.primary_kpis || {}
  const bridgeKpis = overview?.bridge_kpis || {}
  const daxMeasures = overview?.dax_measures || {}

  return (
    <div className="layout">
      <header className="layout__header">
        <h1>💼 SGJobs Interactive Dashboard</h1>
        <p className="layout__subtitle">
          V3 baseline: 1,044,597 validated logical records | Expanded Power
          BI-equivalent analysis + multi-label bridges
        </p>
        <p className="layout__subtitle">
          React client. Filters, KPIs and chart data come from the FastAPI
          backend at <code>{API_BASE_URL || 'the Vite dev proxy'}</code>.
        </p>
      </header>

      <div className="layout__body">
        <FilterSidebar
          descriptors={descriptors}
          selections={selections}
          onChange={setFilterValues}
          onReset={resetFilters}
          onRefresh={refresh}
          loading={isLoading}
        />

        <main className="content">
          <ErrorBanner
            error={filtersState.error}
            onRetry={refresh}
            retryLabel="Reload filters"
          />

          {filtersState.loading && !descriptors.length && (
            <LoadingState label="Loading filters…" />
          )}

          {overview && (
            <p className="content__meta">
              Optimized source: {meta.data_file} ({meta.source_type}) | Rows
              loaded: {fmtNumber(meta.rows_total)} | Columns loaded:{' '}
              {fmtNumber(meta.columns_loaded?.length)}
            </p>
          )}

          <ErrorBanner
            error={overviewState.error}
            onRetry={refresh}
            retryLabel="Retry KPIs"
          />

          {overviewState.loading && !overview && (
            <LoadingState label="Loading Overview KPIs…" />
          )}

          {overview && (
            <>
              <KpiCards primaryKpis={primaryKpis} />

              <p className="content__meta">
                Showing {fmtNumber(meta.rows_filtered)} of{' '}
                {fmtNumber(meta.rows_total)} job records
              </p>
              <p className="content__meta">{meta.filter_context}</p>

              <BridgeKpis bridgeKpis={bridgeKpis} />

              <DaxPanel daxMeasures={daxMeasures} />
            </>
          )}

          <ErrorBanner
            error={chartsState.error}
            onRetry={refresh}
            retryLabel="Retry charts"
          />

          {chartsState.loading && !charts && (
            <LoadingState label="Loading Overview charts…" />
          )}

          {charts && <OverviewCharts charts={charts.charts || {}} />}
        </main>
      </div>
    </div>
  )
}