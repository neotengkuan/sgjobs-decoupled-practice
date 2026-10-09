import { useState } from 'react'
import { useDashboardData } from './hooks/useDashboardData.js'
import { useSalaryAnalysis } from './hooks/useSalaryAnalysis.js'
import { useOpportunityAnalysis } from './hooks/useOpportunityAnalysis.js'
import { useDemandAnalysis } from './hooks/useDemandAnalysis.js'
import { useSkillsCategoriesAnalysis } from './hooks/useSkillsCategoriesAnalysis.js'
import { FilterSidebar } from './components/FilterSidebar.jsx'
import { BridgeKpis, KpiCards } from './components/KpiCards.jsx'
import { DaxPanel } from './components/DaxPanel.jsx'
import { OverviewCharts } from './components/charts/OverviewCharts.jsx'
import { SalaryAnalysisPanel } from './components/salary/SalaryAnalysisPanel.jsx'
import { OpportunityAnalysisPanel } from './components/opportunity/OpportunityAnalysisPanel.jsx'
import { DemandAnalysisPanel } from './components/demand/DemandAnalysisPanel.jsx'
import { BridgeAnalysisPanel } from './components/bridge/BridgeAnalysisPanel.jsx'
import { TabPanel, Tabs } from './components/Tabs.jsx'
import { ErrorBanner, LoadingState } from './components/States.jsx'
import { StaleBanner } from './components/StaleBanner.jsx'
import { fmtNumber } from './utils/format.js'
import { API_BASE_URL } from './api/client.js'

const TABS = [
  { id: 'overview', label: '📊 Overview' },
  { id: 'salary', label: '💰 Salary Analysis' },
  { id: 'opportunity', label: '🎯 Opportunity Analysis' },
  { id: 'demand', label: '📈 Demand & Seniority' },
  { id: 'bridge', label: '🧩 Skills & Categories' },
]

/**
 * SGJobs dashboard shell.
 *
 * This component and its children only:
 *   - hold the sidebar selections in component state,
 *   - call the endpoints of the ACTIVE tab,
 *   - render whatever JSON comes back.
 *
 * There is no filtering, aggregation or scoring here. The 10 filters, the
 * KPI values, the chart datasets and the salary summary measures are all
 * decided by FastAPI.
 *
 * FETCH STRATEGY
 * --------------
 * `activeTab` is passed down as each tab's `enabled` flag, so only the
 * visible page fetches. Changing a filter therefore costs one request per
 * visible page instead of one per tab, which matters most for Demand &
 * Seniority: its scatter can carry the backend's 25,000-row sample.
 *
 * Inactive tabs keep their last successful payload on screen, flagged
 * stale, and reload as soon as they are activated. Refresh bumps the
 * shared token, so it reloads the descriptors plus whichever tab is open.
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('overview')

  const isOverview = activeTab === 'overview'
  const isSalary = activeTab === 'salary'
  const isOpportunity = activeTab === 'opportunity'
  const isDemand = activeTab === 'demand'
  const isBridge = activeTab === 'bridge'

  const {
    descriptors,
    selections,
    filtersReady,
    filtersState,
    overview,
    charts,
    overviewState,
    chartsState,
    overviewStale,
    chartsStale,
    isLoading,
    // Exposed so the active tab's hook can refetch in step with Refresh.
    refreshToken,
    setFilterValues,
    resetFilters,
    refresh,
    refetchOverview,
  } = useDashboardData({ enabled: isOverview })

  const {
    salary,
    loading: salaryLoading,
    error: salaryError,
    stale: salaryStale,
    refetch: refetchSalary,
  } = useSalaryAnalysis(selections, {
    ready: filtersReady,
    enabled: isSalary,
    refreshToken,
  })

  const {
    opportunity,
    loading: opportunityLoading,
    error: opportunityError,
    stale: opportunityStale,
    refetch: refetchOpportunity,
  } = useOpportunityAnalysis(selections, {
    ready: filtersReady,
    enabled: isOpportunity,
    refreshToken,
  })

  const {
    demand,
    loading: demandLoading,
    error: demandError,
    stale: demandStale,
    refetch: refetchDemand,
  } = useDemandAnalysis(selections, {
    ready: filtersReady,
    enabled: isDemand,
    refreshToken,
  })

  const {
    bridge,
    loading: bridgeLoading,
    error: bridgeError,
    stale: bridgeStale,
    refetch: refetchBridge,
  } = useSkillsCategoriesAnalysis(selections, {
    ready: filtersReady,
    enabled: isBridge,
    refreshToken,
  })

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
          <Tabs tabs={TABS} activeId={activeTab} onChange={setActiveTab} />

          <TabPanel id="overview" active={activeTab === 'overview'}>
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

            <StaleBanner show={overviewStale || chartsStale} />

            <ErrorBanner
              error={overviewState.error}
              onRetry={refetchOverview}
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
              onRetry={refetchOverview}
              retryLabel="Retry charts"
            />

            {chartsState.loading && !charts && (
              <LoadingState label="Loading Overview charts…" />
            )}

            {charts && <OverviewCharts charts={charts.charts || {}} />}
          </TabPanel>

          <TabPanel id="salary" active={isSalary}>
            <SalaryAnalysisPanel
              salary={salary}
              loading={salaryLoading}
              error={salaryError}
              stale={salaryStale}
              onRetry={refetchSalary}
            />
          </TabPanel>

          <TabPanel id="opportunity" active={isOpportunity}>
            <OpportunityAnalysisPanel
              opportunity={opportunity}
              loading={opportunityLoading}
              error={opportunityError}
              stale={opportunityStale}
              onRetry={refetchOpportunity}
            />
          </TabPanel>

          <TabPanel id="demand" active={isDemand}>
            <DemandAnalysisPanel
              demand={demand}
              loading={demandLoading}
              error={demandError}
              stale={demandStale}
              onRetry={refetchDemand}
            />
          </TabPanel>

          <TabPanel id="bridge" active={isBridge}>
            <BridgeAnalysisPanel
              bridge={bridge}
              loading={bridgeLoading}
              error={bridgeError}
              stale={bridgeStale}
              onRetry={refetchBridge}
            />
          </TabPanel>
        </main>
      </div>
    </div>
  )
}