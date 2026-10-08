/**
 * Minimal accessible tab bar.
 *
 * No router: the tab is local UI state. Only the active panel is mounted,
 * which is why switching tabs is instant once its data has arrived.
 */
export function Tabs({ tabs, activeId, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => {
        const active = tab.id === activeId

        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={active}
            aria-controls={`panel-${tab.id}`}
            className={`tab ${active ? 'tab--active' : ''}`}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}

/**
 * A single tab panel.
 */
export function TabPanel({ id, active, children }) {
  if (!active) {
    return null
  }

  return (
    <div
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
      className="tab-panel"
    >
      {children}
    </div>
  )
}