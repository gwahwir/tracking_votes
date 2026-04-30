import { useState } from 'react'
import { useHistorical, useDemographics, useConstituencyArticles, useSeatPredictions } from '../../hooks/useApi'
import { PARTY_COLORS } from '../../theme'
import { HistoryTable } from './HistoryTable'
import { DemographicsChart } from './DemographicsChart'

const TABS = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'history', label: 'HISTORY' },
  { id: 'demographics', label: 'DEMOGRAPHICS' },
  { id: 'articles', label: 'ARTICLES' },
]

const confColor = (c) => c >= 70 ? '#39ff14' : c >= 40 ? '#ffcc00' : '#ff3131'

const StrengthBar = ({ value }) => {
  const color = value >= 70 ? '#39ff14' : value >= 40 ? '#ffcc00' : '#ff3131'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
      <div style={{ flex: 1, height: '5px', background: '#1a1b1e', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${value}%`, height: '100%', background: `linear-gradient(90deg, ${color}80, ${color})`, borderRadius: '3px', transition: 'width 0.6s ease' }} />
      </div>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color, fontWeight: 700, minWidth: '28px' }}>
        {Math.round(value)}%
      </span>
    </div>
  )
}

const OverviewTab = ({ prediction }) => {
  const partyColor = PARTY_COLORS[prediction?.leading_party] || '#aaa'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {prediction?.signal_breakdown && (
        <div>
          <div style={sectionLabel}>SIGNAL BREAKDOWN</div>
          {Object.entries(prediction.signal_breakdown).map(([lens, data]) => {
            if (!data) return null
            return (
              <div key={lens} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 0', borderBottom: '1px solid #1a1b1e' }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#909296', minWidth: '80px', textTransform: 'capitalize' }}>
                  {lens.replace('_', ' ')}
                </span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 700, color: partyColor, minWidth: '50px' }}>
                  {data.direction || ''}
                </span>
                {data.strength != null && <StrengthBar value={data.strength} />}
              </div>
            )
          })}
        </div>
      )}
      {prediction?.caveats?.length > 0 && (
        <div>
          <div style={sectionLabel}>CAVEATS</div>
          {prediction.caveats.map((c, i) => (
            <div key={i} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#ff3131', padding: '4px 0' }}>
              ⚠ {c}
            </div>
          ))}
        </div>
      )}
      {!prediction && (
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66' }}>No prediction data yet.</div>
      )}
    </div>
  )
}

const ArticlesList = ({ articles, loading }) => {
  if (loading) return <div style={dimText}>Loading articles...</div>
  if (!articles?.length) return <div style={dimText}>No articles tagged to this constituency.</div>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {articles.map((a) => (
        <div key={a.id} style={{ padding: '8px', background: '#1a1b1e', borderRadius: '3px', border: '1px solid #2c2e33' }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#e0e0e0', lineHeight: 1.4 }}>{a.title}</div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '3px' }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', textTransform: 'uppercase' }}>{a.source}</span>
            {a.reliability_score != null && (
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: a.reliability_score >= 70 ? '#39ff14' : a.reliability_score >= 40 ? '#ffcc00' : '#ff3131' }}>
                {a.reliability_score}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

const sectionLabel = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: '9px',
  color: '#5c5f66',
  letterSpacing: '0.12em',
  marginBottom: '10px',
  paddingBottom: '4px',
  borderBottom: '1px solid #1a1b1e',
}

const dimText = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: '11px',
  color: '#5c5f66',
  paddingTop: '8px',
}

export const SeatDetailPanel = ({ constituencyCode, seatName, onClose }) => {
  const [activeTab, setActiveTab] = useState('overview')
  const { results: history, loading: histLoading } = useHistorical(constituencyCode)
  const { demographics, loading: demoLoading } = useDemographics(constituencyCode)
  const { articles, loading: artLoading } = useConstituencyArticles(constituencyCode)
  const { predictions } = useSeatPredictions(constituencyCode)
  const raw = (predictions ?? []).find((p) => p.constituency_code === constituencyCode && p.leading_party) ?? null
  const prediction = raw ? {
    ...raw,
    caveats: (() => { try { return typeof raw.caveats === 'string' ? JSON.parse(raw.caveats) : (raw.caveats ?? []) } catch { return [] } })(),
    signal_breakdown: (() => { try { return typeof raw.signal_breakdown === 'string' ? JSON.parse(raw.signal_breakdown) : (raw.signal_breakdown ?? {}) } catch { return {} } })(),
  } : null

  const partyColor = PARTY_COLORS[prediction?.leading_party] || '#aaa'
  const confidence = prediction?.confidence ?? null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '12px 14px', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        <div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '14px', fontWeight: 700, color: '#00d4ff' }}>
            {seatName}
          </div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5c5f66', marginTop: '2px' }}>
            {constituencyCode}
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#909296', fontSize: '14px', cursor: 'pointer', padding: '2px 6px' }}>
          ✕
        </button>
      </div>

      {/* Prediction card */}
      {prediction && (
        <div style={{
          margin: '10px 14px',
          padding: '10px 12px',
          background: '#1a1b1e',
          border: '1px solid #373a40',
          borderLeft: `3px solid ${partyColor}`,
          borderRadius: '4px',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ background: partyColor, color: '#000', padding: '2px 10px', borderRadius: '3px', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: 700 }}>
              {prediction.leading_party}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', fontWeight: 700, color: confColor(confidence) }}>
              {confidence}% confidence
            </span>
          </div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span>
              {prediction.updated_at ? `Updated ${(() => { try { return new Date(prediction.updated_at).toLocaleString() } catch { return prediction.updated_at } })()}` : ''}
            </span>
            <span>
              {articles?.length || prediction.num_articles || 0} constituency articles
              {(prediction.num_state_articles ?? 0) > 0 ? ` · ${prediction.num_state_articles} state-level articles` : ''}
              {(articles?.length || prediction.num_articles || 0) === 0 && (prediction.num_state_articles ?? 0) === 0 ? ' · based on historical baseline only' : ''}
            </span>
            {(() => {
              const ge15 = history?.find?.((h) => h.election_year === 2022)
              return ge15 ? (
                <span>GE15 baseline: <span style={{ color: PARTY_COLORS[ge15.winner_party] || '#aaa' }}>{ge15.winner_party}</span> won {ge15.margin_pct != null ? `(${ge15.margin_pct.toFixed(1)}% margin)` : ''}</span>
              ) : null
            })()}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              flex: 1,
              padding: '7px 2px',
              background: activeTab === t.id ? 'rgba(0,212,255,0.05)' : 'transparent',
              border: 'none',
              borderBottom: `2px solid ${activeTab === t.id ? '#00d4ff' : 'transparent'}`,
              color: activeTab === t.id ? '#00d4ff' : '#5c5f66',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '8px',
              cursor: 'pointer',
              letterSpacing: '0.05em',
              transition: 'all 0.12s',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {activeTab === 'overview' && <OverviewTab prediction={prediction} />}
        {activeTab === 'history' && <HistoryTable results={history} loading={histLoading} />}
        {activeTab === 'demographics' && <DemographicsChart demographics={demographics} loading={demoLoading} />}
        {activeTab === 'articles' && <ArticlesList articles={articles} loading={artLoading} />}
      </div>
    </div>
  )
}
