import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchFilterDescriptors,
  fetchOverview,
  fetchOverviewCharts,
} from '../api/overviewApi.js'
import { pruneSelections } from '../api/query.js'

/**
 * Owns the shared sidebar state (descriptors + selections) and the Overview
 * page's own data.
 *
 * Other tabs receive `selections` from here and fetch only while they are
 * active, so a filter change costs one request per visible page instead of
 * one per tab.
 *
 * @param {{enabled?: boolean}} options
 *   enabled - the Overview tab is currently active. Overview requests are
 *             skipped while another tab is on screen; the payload stays
 *             visible and is flagged stale.
 */
export function useDashboardData({ enabled = true } = {}) {
  const [refreshToken, setRefreshToken] = useState(0)
  const [overviewToken, setOverviewToken] = useState(0)

  const [descriptors, setDescriptors] = useState([])
  const [selections, setSelections] = useState({})
  const [filtersReady, setFiltersReady] = useState(false)

  const [overview, setOverview] = useState(null)
  const [overviewKey, setOverviewKey] = useState(null)
  const [charts, setCharts] = useState(null)
  const [chartsKey, setChartsKey] = useState(null)

  const [filtersState, setFiltersState] = useState({
    loading: true,
    error: null,
  })
  const [overviewState, setOverviewState] = useState({
    loading: true,
    error: null,
  })
  const [chartsState, setChartsState] = useState({
    loading: true,
    error: null,
  })

  const selectionKey = useMemo(
    () => JSON.stringify(selections),
    [selections],
  )

  // ---- Sidebar descriptors -------------------------------------------------
  // Not gated on `enabled`: the sidebar is always on screen, so the filters
  // are always required. Loaded once, then only on Refresh.

  useEffect(() => {
    const controller = new AbortController()

    setFiltersState({ loading: true, error: null })

    fetchFilterDescriptors({ signal: controller.signal })
      .then((payload) => {
        setDescriptors(payload?.filters || [])
        setFiltersReady(true)
        setFiltersState({ loading: false, error: null })

        // Drop anything the new option lists no longer contain.
        setSelections((current) =>
          pruneSelections(current, payload?.filters || []),
        )
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setFiltersState({ loading: false, error })
      })

    return () => controller.abort()
  }, [refreshToken])

  // ---- Overview KPIs + Overview chart datasets ----------------------------
  // Gated on `enabled`: both requests belong to the Overview page only.

  useEffect(() => {
    if (!filtersReady || !enabled) {
      return undefined
    }

    const controller = new AbortController()

    setOverviewState({ loading: true, error: null })
    setChartsState({ loading: true, error: null })

    fetchOverview(selections, { signal: controller.signal })
      .then((payload) => {
        setOverview(payload)
        setOverviewKey(selectionKey)
        setOverviewState({ loading: false, error: null })
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setOverviewState({ loading: false, error })
      })

    fetchOverviewCharts(selections, { signal: controller.signal })
      .then((payload) => {
        setCharts(payload)
        setChartsKey(selectionKey)
        setChartsState({ loading: false, error: null })
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setChartsState({ loading: false, error })
      })

    return () => controller.abort()
    // selectionKey serialises the selection, so a new object with equal
    // contents does not trigger a refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersReady, enabled, selectionKey, refreshToken, overviewToken])

  // ---- Handlers ------------------------------------------------------------

  const setFilterValues = useCallback((param, values) => {
    setSelections((current) => {
      const next = { ...current }

      if (!values || values.length === 0) {
        delete next[param]
      } else {
        next[param] = values
      }

      return next
    })
  }, [])

  const resetFilters = useCallback(() => {
    setSelections({})
  }, [])

  const refresh = useCallback(() => {
    setRefreshToken((token) => token + 1)
  }, [])

  /**
   * Reload only the Overview datasets, leaving the shared filter
   * vocabulary alone. Used by the Overview page's own Retry buttons so
   * they behave like the other tabs' per-tab retry.
   */
  const refetchOverview = useCallback(() => {
    setOverviewToken((token) => token + 1)
  }, [])

  return {
    descriptors,
    selections,
    filtersReady,
    overview,
    charts,
    filtersState,
    overviewState,
    chartsState,
    // The visible payload no longer matches the current selection. Reported
    // per dataset because the KPI payload and the chart datasets are two
    // separate requests.
    overviewStale: overview !== null && overviewKey !== selectionKey,
    chartsStale: charts !== null && chartsKey !== selectionKey,
    isLoading:
      filtersState.loading ||
      (enabled && (overviewState.loading || chartsState.loading)),
    // Exposed so the active tab's hook can refetch in step with Refresh.
    refreshToken,
    setFilterValues,
    resetFilters,
    refresh,
    refetchOverview,
  }
}