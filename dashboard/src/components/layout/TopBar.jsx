import { useState, useEffect } from 'react'
import './TopBar.css'

export const TopBar = ({
  mapType = 'parlimen',
  useCartogram = false,
  onMapTypeChange,
  onCartogramToggle,
  onRefresh,
  onWikiOpen,
  refreshing = false,
}) => {
  const [pulse, setPulse] = useState(true)

  useEffect(() => {
    const t = setInterval(() => setPulse((p) => !p), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="topbar">
      <div className="topbar-left">
        <span className="topbar-title">JOHOR ELECTION MONITOR</span>
      </div>

      <div className="topbar-center">
        <div className="live-badge">
          <span className="live-dot" style={{ opacity: pulse ? 1 : 0.3 }} />
          LIVE
        </div>
      </div>

      <div className="topbar-right">
        <div className="map-toggle-group">
          <button
            className={`toggle-btn ${mapType === 'parlimen' ? 'active' : ''}`}
            onClick={() => onMapTypeChange('parlimen')}
          >
            Parlimen
          </button>
          <button
            className={`toggle-btn ${mapType === 'dun' ? 'active' : ''}`}
            onClick={() => onMapTypeChange('dun')}
          >
            DUN
          </button>
        </div>

        <button
          title={useCartogram ? 'Regular Map' : 'Cartogram'}
          className={`icon-btn ${useCartogram ? 'active' : ''}`}
          onClick={onCartogramToggle}
        >
          ⊞
        </button>

        <button
          title="Refresh"
          className={`icon-btn ${refreshing ? 'spin' : ''}`}
          onClick={onRefresh}
        >
          ↻
        </button>

        <button title="Wiki" className="icon-btn" onClick={onWikiOpen}>
          ⊟
        </button>
      </div>
    </div>
  )
}
