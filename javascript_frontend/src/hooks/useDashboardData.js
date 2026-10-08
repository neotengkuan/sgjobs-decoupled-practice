import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchFilterDescriptors,
  fetchOverview,
  fetchOverviewCharts,
} from '../api/overviewApi.js'
import { pruneSelections } from '../api/query.js'

/**
 * Loads the sidebar descriptors once, then reloads the Overview KPIs and
 * chart datasets whenever the selection changes.
 *
 * Two independent requests are kept (KPIs and charts) so one failing does
 * not blank the other, and each keeps its own loading/error state.
 *
 * @returns {object} descriptors, selections, data, loading and error flags,
 *                   plus the change/reset/refresh handlers.
 */
export function useDashboardData() {
  const [refreshToken, setRefreshToken] = useState(0)

  const [descriptors, setDescriptors] = useState([])
  const [selections, setSelections] = useState({})
  const [filtersReady, setFiltersReady] = useState(false)

  const [overview, setOverview] = useState(null)
  const [charts, setCharts] = useState(null)

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

  // ---- Sidebar descriptors -------------------------------------------------

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

  // ---- Overview KPIs + chart datasets -------------------------------------

  const selectionKey = useMemo(
    () => JSON.stringify(selections),
    [selections],
  )

  useEffect(() => {
    if (!filtersReady) {
      return undefined
    }

    const controller = new AbortController()

    setOverviewState({ loading: true, error: null })
    setChartsState({ loading: true, error: null })

    fetchOverview(selections, { signal: controller.signal })
      .then((payload) => {
        setOverview(payload)
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
        setChartsState({ loading: false, error: null })
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setChartsState({ loading: false, error })
      })

    return () => controller.abort()
    // selectionKey serialises the selection so a new object with equal
    // contents does not trigger a refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersReady, selectionKey, refreshToken])

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

  return {
    descriptors,
    selections,
    filtersReady,
    overview,
    charts,
    filtersState,
    overviewState,
    chartsState,
    isLoading:
      filtersState.loading || overviewState.loading || chartsState.loading,
    setFilterValues,
    resetFilters,
    refresh,
  }
}