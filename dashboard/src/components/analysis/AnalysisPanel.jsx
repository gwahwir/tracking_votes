import { useState, useEffect } from 'react'
import './AnalysisPanel.css'

const LENSES = [
  { id: 'political',     label: 'Political',   short: 'POL' },
  { id: 'demographic',  label: 'Demographic',  short: 'DEM' },
  { id: 'historical',   label: 'Historical',   short: 'HIST' },
  { id: 'strategic',    label: 'Strategic',    short: 'STRAT' },
  { id: 'factcheck',    label: 'Fact-Check',   short: 'FACT' },
  { id: 'bridget_welsh', label: 'Welsh',       short: 'WELSH' },
]

const StrengthBar = ({ value }) => {
  const color = value >= 70 ? '#39ff14' : value >= 40 ? '#ffcc00' : '#ff3131'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '5px', background: '#1a1b1e', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{
          width: `${value}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${color}80, ${color})`,
          borderRadius: '3px',
          transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color, fontWeight: 700, minWidth: '28px' }}>
        {Math.round(value)}%
      </span>
    </div>
  )
}

const LensContent = ({ data, lens }) => {
  if (!data) return (
    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66', padding: '16px 0' }}>
      No {lens.label.toLowerCase()} analysis available for this article.
    </div>
  )
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {data.direction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', minWidth: '90px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Direction
          </span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '15px', color: '#00d4ff', fontWeight: 700 }}>
            {data.direction}
          </span>
        </div>
      )}
      {data.strength != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', minWidth: '90px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Signal Strength
          </span>
          <div style={{ flex: 1 }}><StrengthBar value={data.strength} /></div>
        </div>
      )}
      {data.summary && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Summary
          </span>
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#c1c2c5', lineHeight: 1.65, margin: 0 }}>
            {data.summary}
          </p>
        </div>
      )}
    </div>
  )
}

export const AnalysisPanel = ({ article, refreshTrigger, onTaskCreated }) => {
  const [analyses, setAnalyses] = useState({})
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('political')

  useEffect(() => {
    if (!article) { setAnalyses({}); return }
    const fetchAnalyses = async () => {
      setLoading(true)
      try {
        const res = await fetch(`http://localhost:8000/analyses?article_id=${article.id}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const byLens = {}
        data.forEach((a) => { byLens[a.lens_name] = a })
        setAnalyses(byLens)
      } catch (err) {
        setAnalyses({})
      } finally {
        setLoading(false)
      }
    }
    fetchAnalyses()
  }, [article, refreshTrigger])

  if (!article) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 700, color: '#5c5f66', letterSpacing: '0.12em' }}>
            ANALYSIS
          </span>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px', opacity: 0.4 }}>
          <div style={{ fontSize: '28px', color: '#5c5f66' }}>◈</div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66' }}>
            Select an article to see analysis
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 700, color: '#5c5f66', letterSpacing: '0.12em', display: 'block' }}>
          ANALYSIS
        </span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#909296', display: 'block', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          title={article.title}>
          {article.title}
        </span>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        {LENSES.map((l) => (
          <button
            key={l.id}
            onClick={() => setActiveTab(l.id)}
            style={{
              flex: 1,
              padding: '7px 2px',
              background: activeTab === l.id ? 'rgba(0,212,255,0.05)' : 'transparent',
              border: 'none',
              borderBottom: `2px solid ${activeTab === l.id ? '#00d4ff' : 'transparent'}`,
              color: activeTab === l.id ? '#00d4ff' : '#5c5f66',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px',
              cursor: 'pointer',
              letterSpacing: '0.05em',
              transition: 'all 0.12s',
            }}
          >
            {l.short}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {loading ? (
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5c5f66' }}>Loading...</div>
        ) : (
          LENSES.map((l) => activeTab === l.id && (
            <div key={l.id}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: 700, color: '#00d4ff', marginBottom: '12px', letterSpacing: '0.08em' }}>
                {l.label}
              </div>
              <LensContent data={analyses[l.id]} lens={l} />
            </div>
          ))
        )}
      </div>
    </div>
  )
}
