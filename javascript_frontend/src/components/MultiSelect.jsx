/**
 * Compact multi-select used by all ten filters.
 *
 * A searchable checkbox list rather than a native <select multiple>, because
 * some option lists (notably Skill) can hold thousands of values.
 *
 * The search box only narrows what is SHOWN. It never narrows what is
 * SENT: every checked option is passed to the backend, which does the
 * actual filtering.
 */
import { useMemo, useState } from 'react'

export function MultiSelect({
  id,
  label,
  help,
  options = [],
  values = [],
  onChange,
  disabled = false,
}) {
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(false)

  const selected = useMemo(() => new Set(values.map(String)), [values])

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()

    if (!needle) {
      return options
    }

    return options.filter((option) =>
      String(option).toLowerCase().includes(needle),
    )
  }, [options, search])

  const toggle = (option) => {
    const value = String(option)

    if (selected.has(value)) {
      onChange(values.filter((item) => String(item) !== value))
    } else {
      onChange([...values, option])
    }
  }

  const labelText = selected.size ? `${label} (${selected.size})` : label

  return (
    <div className="multiselect" data-param={id}>
      <button
        type="button"
        className="multiselect__trigger"
        onClick={() => setExpanded((open) => !open)}
        aria-expanded={expanded}
        disabled={disabled}
        title={help || label}
      >
        <span className="multiselect__label">{labelText}</span>
        <span className="multiselect__caret" aria-hidden="true">
          {expanded ? '▾' : '▸'}
        </span>
      </button>

      {expanded && (
        <div className="multiselect__panel">
          {options.length > 12 && (
            <input
              type="search"
              className="multiselect__search"
              placeholder={`Search ${label.toLowerCase()}`}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          )}

          <div className="multiselect__options">
            {visible.length === 0 && (
              <p className="multiselect__empty">No matching option</p>
            )}

            {visible.map((option) => {
              const value = String(option)
              const inputId = `${id}--${value}`

              return (
                <label className="multiselect__option" key={inputId} htmlFor={inputId}>
                  <input
                    id={inputId}
                    type="checkbox"
                    checked={selected.has(value)}
                    onChange={() => toggle(option)}
                    disabled={disabled}
                  />
                  <span>{value}</span>
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}