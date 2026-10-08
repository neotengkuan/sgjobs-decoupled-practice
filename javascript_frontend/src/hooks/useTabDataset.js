import { useEffect, useMemo, useState } from 'react'

/**
 * Generic loader for one tab's dataset.
 *
 * Every tab needs the same three things: call its endpoint with the
 * CURRENT sidebar selection, track loading and error separately, and
 * cancel in-flight requests when the selection changes. Sharing that here
 * keeps each tab's hook a one-liner, and - more importantly - keeps the
 * state instances separate: a failure in one tab cannot touch another
 * tab's payload.
 *
 * The selections are owned by useDashboardData and passed in, so every
 * tab always describes the same filtered rows.
 *
 * @param {(filters: object, opts: object) => Promise<object>} fetcher
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, refreshToken?: number}} options
 * @returns {{data: object|null, loading: boolean, error: Error|null}}
 */
export function useTabDataset(fetcher, selections, { ready, refreshToken } = {}) {
  const [data, setData] = useState(null)
  const [state, setState] = useState({ loading: true, error: null })

  const selectionKey = useMemo(
    () => JSON.stringify(selections),
    [selections],
  )

  useEffect(() => {
    if (!ready) {
      return undefined
    }

    const controller = new AbortController()

    setState({ loading: true, error: null })

    fetcher(selections, { signal: controller.signal })
      .then((payload) => {
        setData(payload)
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
  }, [fetcher, ready, selectionKey, refreshToken])

  return { data, loading: state.loading, error: state.error }
}