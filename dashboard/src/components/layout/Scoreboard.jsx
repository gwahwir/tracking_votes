import { PARTY_COLORS } from '../../theme'

export const Scoreboard = ({ predictions }) => {
  if (!predictions?.length) return null

  const counts = {}
  predictions.forEach((p) => {
    if (p.leading_party) {
      counts[p.leading_party] = (counts[p.leading_party] || 0) + 1
    }
  })

  const total = predictions.length
  const predicted = Object.values(counts).reduce((a, b) => a + b, 0)
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      padding: '6px 16px',
      background: '#0d0d14',
      borderBottom: '1px solid #373a40',
      flexShrink: 0,
      overflowX: 'auto',
      height: '34px',
      boxSizing: 'border-box',
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {sorted.map(([party, count]) => (
        <div key={party} style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '2px',
            background: PARTY_COLORS[party] || '#666',
            display: 'inline-block',
            flexShrink: 0,
          }} />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            fontWeight: 700,
            color: PARTY_COLORS[party] || '#aaa',
          }}>{party}</span>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '13px',
            fontWeight: 700,
            color: '#fff',
          }}>{count}</span>
        </div>
      ))}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px', flexShrink: 0 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#00d4ff' }}>
          Majority: {Math.floor(total / 2) + 1}
        </span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66' }}>
          {predicted}/{total} seats predicted
        </span>
      </div>
    </div>
  )
}
