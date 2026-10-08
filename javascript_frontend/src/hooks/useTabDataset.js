import { useEffect, useMemo, useState } from 'react'

/**
 * Generic loader for one tab's dataset.
 *
 * Every tab needs the same five things:
 *   1. call its endpoint with the CURRENT sidebar selection,
 *   2. fetch ONLY while the tab is active,
 *   3. keep the last successful payload on screen while a new request
 *      for that tab is in flight,
 *   4. report that the visible payload is out of date once the selection
 *      moved on, so the UI can say so,
 *   5. cancel in-flight requests when the selection changes or the tab
 *      is switched away.
 *
 * Sharing that here keeps each tab's hook a one-liner, and - more
 * importantly - keeps the state instances separate: a failure in one tab
 * cannot touch another tab's payload.
 *
 * The selections are owned by useDashboardData and passed in, so every
 * tab always describes the same filtered rows.
 *
 * @param {(filters: object, opts: object) => Promise<object>} fetcher
 * @param {Record<string, Array<string|number>>} selections
 * @param {{
 *   ready?: boolean,
 *   enabled?: boolean,
 *   refreshToken?: number,
 * }} options
 *   ready         - descriptors have loaded, so selections are meaningful
 *   enabled       - the tab is currently active; no fetch happens otherwise
 *   refreshToken  - bumped by Refresh, to refetch this tab
 * @returns {{
 *   data: object|null,
 *   loading: boolean,
 *   error: Error|null,
 *   stale: boolean,
 *   refetch: () => void
 * }}
 */
export function useTabDataset(
  fetcher,
  selections,
  { ready, enabled = true, refreshToken } = {},
) {
  const [data, setData] = useState(null)
  const [loadedKey, setLoadedKey] = useState(null)
  const [state, setState] = useState({ loading: true, error: null })
  const [localToken, setLocalToken] = useState(0)

  const selectionKey = useMemo(
    () => JSON.stringify(selections),
    [selections],
  )

  useEffect(() => {
    // Nothing to ask the API yet, or the tab is not on screen: leave the
    // payload alone. It stays visible, flagged stale, and is fetched when
    // the tab is activated again.
    if (!ready || !enabled) {
      return undefined
    }

    const controller = new AbortController()

    setState({ loading: true, error: null })

    fetcher(selections, { signal: controller.signal })
      .then((payload) => {
        setData(payload)
        setLoadedKey(selectionKey)
        setState({ loading: false, error: null })
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setState({ loading: false, error })
      })

    return () => controller.abort()
    // selectionKey serialises the selection, so a new object with equal
    // contents does not trigger a refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, ready, enabled, selectionKey, refreshToken, localToken])

  // The visible payload no longer matches the current selection.
  const stale = data !== null && loadedKey !== null && loadedKey !== selectionKey

  /**
   * Force a refetch of this tab, e.g. from its own Retry button, without
   * touching the shared Refresh counter or any other tab.
   */
  const refetch = () => setLocalToken((token) => token + 1)

  return { data, loading: state.loading, error: state.error, stale, refetch }
}