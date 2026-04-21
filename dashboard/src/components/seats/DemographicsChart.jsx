const ETHNIC = [
  { key: 'malay_pct',   label: 'Malay',   color: '#3366cc' },
  { key: 'chinese_pct', label: 'Chinese',  color: '#ff6633' },
  { key: 'indian_pct',  label: 'Indian',   color: '#ffcc00' },
  { key: 'others_pct',  label: 'Others',   color: '#666666' },
]

export const DemographicsChart = ({ demographics, loading }) => {
  if (loading) return <div style={dim}>Loading demographics...</div>
  if (!demographics) return <div style={dim}>No demographic data available.</div>

  const segments = ETHNIC
    .map((e) => ({ ...e, value: demographics[e.key] ?? 0 }))
    .filter((s) => s.value > 0)

  const total = segments.reduce((s, e) => s + e.value, 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

      {/* Section label */}
      <div style={sectionLabel}>VOTER DEMOGRAPHICS</div>

      {/* Stacked bar */}
      <div style={{ height: '8px', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
        {segments.map((s) => (
          <div key={s.label} style={{
            width: `${(s.value / total) * 100}%`,
            background: s.color,
            height: '100%',
          }} />
        ))}
      </div>

      {/* Per-ethnicity rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
        {segments.map((s) => (
          <div key={s.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: s.color, display: 'inline-block', flexShrink: 0 }} />
                <span style={{ ...mono, fontSize: '10px', color: '#909296' }}>{s.label}</span>
              </div>
              <span style={{ ...mono, fontSize: '10px', color: '#e0e0e0', fontWeight: 700 }}>
                {s.value.toFixed(1)}%
              </span>
            </div>
            <div style={{ height: '3px', background: '#1a1b1e', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${s.value}%`, height: '100%', background: s.color, opacity: 0.7, borderRadius: '2px' }} />
            </div>
          </div>
        ))}
      </div>

      {/* Meta row */}
      <div style={{ display: 'flex', gap: '16px', paddingTop: '4px', borderTop: '1px solid #1a1b1e' }}>
        {demographics.urban_rural && (
          <div>
            <div style={{ ...mono, fontSize: '9px', color: '#5c5f66', letterSpacing: '0.08em', marginBottom: '2px' }}>CLASSIFICATION</div>
            <div style={{ ...mono, fontSize: '11px', color: '#c1c2c5', textTransform: 'capitalize' }}>{demographics.urban_rural}</div>
          </div>
        )}
        {demographics.region && (
          <div>
            <div style={{ ...mono, fontSize: '9px', color: '#5c5f66', letterSpacing: '0.08em', marginBottom: '2px' }}>REGION</div>
            <div style={{ ...mono, fontSize: '11px', color: '#c1c2c5', textTransform: 'capitalize' }}>{demographics.region}</div>
          </div>
        )}
      </div>

    </div>
  )
}

const mono = { fontFamily: "'JetBrains Mono', monospace" }
const dim = { fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66', paddingTop: '8px' }
const sectionLabel = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: '9px',
  color: '#5c5f66',
  letterSpacing: '0.12em',
  paddingBottom: '4px',
  borderBottom: '1px solid #1a1b1e',
}
