import { MultiSelect } from './MultiSelect.jsx'

/**
 * The ten sidebar filters.
 *
 * The widgets are rendered from the descriptors /api/filters returns, so
 * labels, order, help text and option lists are whatever the backend
 * decided. This component only stores what the user ticks and never
 * decides what a selection means.
 */
export function FilterSidebar({
  descriptors = [],
  selections = {},
  onChange,
  onReset,
  onRefresh,
  loading = false,
}) {
  const available = descriptors.filter((descriptor) => descriptor.available)
  const unavailable = descriptors.filter(
    (descriptor) => !descriptor.available,
  )

  return (
    <aside className="sidebar">
      <h2 className="sidebar__title">Filters</h2>

      {available.map((descriptor) => (
        <MultiSelect
          key={descriptor.param}
          id={descriptor.param}
          label={descriptor.label}
          help={descriptor.help}
          options={descriptor.options || []}
          values={selections[descriptor.param] || []}
          onChange={(values) => onChange(descriptor.param, values)}
          disabled={loading}
        />
      ))}

      {unavailable.length > 0 && (
        <p className="sidebar__note">
          Unavailable in this dataset:{' '}
          {unavailable.map((item) => item.label).join(', ')}
        </p>
      )}

      <div className="sidebar__actions">
        <button
          type="button"
          className="button"
          onClick={onReset}
          disabled={loading}
        >
          Reset Filters
        </button>

        <button
          type="button"
          className="button button--primary"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
    </aside>
  )
}