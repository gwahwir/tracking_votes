import { useState, useEffect } from 'react'
import { useWikiPages } from '../../hooks/useApi'

export const WikiModal = ({ onClose }) => {
  const { pages, loading } = useWikiPages()
  const [search, setSearch] = useState('')
  const [filtered, setFiltered] = useState([])

  useEffect(() => {
    if (!pages) return
    setFiltered(
      pages.filter(
        (p) =>
          p.title.toLowerCase().includes(search.toLowerCase()) ||
          p.path.toLowerCase().includes(search.toLowerCase())
      )
    )
  }, [pages, search])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.8)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '540px',
          maxHeight: '80vh',
          background: '#0a0a0f',
          border: '1px solid #373a40',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 0 40px rgba(0,212,255,0.15)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 16px',
          borderBottom: '1px solid #373a40',
        }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', fontWeight: 700, color: '#00d4ff', letterSpacing: '0.1em' }}>
            ⊟ WIKI KNOWLEDGE BASE
          </span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#909296', fontSize: '14px', cursor: 'pointer' }}>
            ✕
          </button>
        </div>

        {/* Search */}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search pages..."
          style={{
            margin: '10px 16px',
            padding: '7px 10px',
            background: '#1a1b1e',
            border: '1px solid #373a40',
            borderRadius: '4px',
            color: '#e0e0e0',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '12px',
            outline: 'none',
          }}
        />

        {/* List */}
        <div style={{ overflowY: 'auto', padding: '0 8px 10px' }}>
          {loading && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
              Loading...
            </div>
          )}
          {filtered.map((p) => (
            <div key={p.path} style={{ padding: '8px', borderBottom: '1px solid #1a1b1e', cursor: 'pointer' }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#e0e0e0', marginBottom: '3px' }}>
                {p.title}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5c5f66' }}>{p.path}</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5c5f66' }}>
                  {new Date(p.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
          {!loading && filtered.length === 0 && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
              No pages found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
