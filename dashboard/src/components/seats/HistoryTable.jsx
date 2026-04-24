import { PARTY_COLORS } from '../../theme'

const confColor = (pct) => pct >= 10 ? '#39ff14' : pct >= 5 ? '#ffcc00' : '#ff3131'

export const HistoryTable = ({ results, loading }) => {
  if (loading) return <div style={dim}>Loading history...</div>
  if (!results?.length) return <div style={dim}>No historical data available.</div>

  const sorted = [...results]
    .sort((a, b) => b.election_year - a.election_year)
    .map((r) => ({
      ...r,
      candidates: (() => { try { return typeof r.candidates === 'string' ? JSON.parse(r.candidates) : (r.candidates ?? []) } catch { return [] } })(),
    }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Election summary rows */}
      <div>
        <div style={sectionLabel}>ELECTION HISTORY</div>
        {sorted.map((r) => {
          const partyColor = PARTY_COLORS[r.winner_coalition] || PARTY_COLORS[r.winner_party] || '#666'
          return (
            <div key={r.election_year} style={{ borderBottom: '1px solid #1a1b1e', padding: '7px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ ...mono, fontSize: '11px', fontWeight: 700, color: '#e0e0e0' }}>{r.election_year}</span>
                <span style={{
                  background: partyColor,
                  color: '#000',
                  padding: '1px 7px',
                  borderRadius: '3px',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '9px',
                  fontWeight: 700,
                }}>
                  {r.winner_coalition || r.winner_party}
                </span>
              </div>
              <div style={{ ...mono, fontSize: '10px', color: '#c1c2c5', marginBottom: '4px' }}>
                {r.winner_name}
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <span style={{ ...mono, fontSize: '9px', color: '#5c5f66' }}>
                  Margin{' '}
                  <span style={{ color: r.margin_pct != null ? confColor(r.margin_pct) : '#5c5f66', fontWeight: 700 }}>
                    {r.margin_pct != null ? `${r.margin_pct.toFixed(1)}%` : '—'}
                  </span>
                  {r.margin != null && (
                    <span style={{ color: '#373a40' }}> ({r.margin.toLocaleString()})</span>
                  )}
                </span>
                <span style={{ ...mono, fontSize: '9px', color: '#5c5f66' }}>
                  Turnout <span style={{ color: '#909296', fontWeight: 700 }}>
                    {r.turnout_pct != null ? `${r.turnout_pct.toFixed(1)}%` : '—'}
                  </span>
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Most recent full candidate breakdown */}
      {sorted.map((r) => {
        if (!r.candidates?.length) return null
        const totalVotes = r.total_votes_cast || r.candidates.reduce((s, c) => s + (c.votes || 0), 0)
        const byVotes = [...r.candidates].sort((a, b) => b.votes - a.votes)

        return (
          <div key={`cands-${r.election_year}`}>
            <div style={sectionLabel}>{r.election_year} FULL RESULTS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {byVotes.map((c, i) => {
                const pct = totalVotes && c.votes ? (c.votes / totalVotes) * 100 : 0
                const color = PARTY_COLORS[c.coalition] || PARTY_COLORS[c.party] || '#555'
                const isWinner = i === 0
                return (
                  <div key={i}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span style={{ ...mono, fontSize: '10px', color: isWinner ? '#e0e0e0' : '#909296', fontWeight: isWinner ? 700 : 400 }}>
                        {c.name}
                      </span>
                      <span style={{ ...mono, fontSize: '10px', color: isWinner ? '#e0e0e0' : '#5c5f66', fontWeight: isWinner ? 700 : 400, flexShrink: 0, marginLeft: '8px' }}>
                        {c.votes?.toLocaleString() ?? '—'} <span style={{ color: '#5c5f66' }}>({pct.toFixed(1)}%)</span>
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <div style={{ flex: 1, height: '3px', background: '#1a1b1e', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: color, opacity: isWinner ? 1 : 0.5, borderRadius: '2px' }} />
                      </div>
                      <span style={{ ...mono, fontSize: '8px', color, fontWeight: 700, minWidth: '30px', textAlign: 'right' }}>
                        {c.party}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

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
  marginBottom: '8px',
  paddingBottom: '4px',
  borderBottom: '1px solid #1a1b1e',
}
