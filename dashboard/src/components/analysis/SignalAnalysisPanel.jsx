import { useState, useEffect, useRef } from 'react'
import { useTaskStream } from '../../hooks/useApi'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TONE_COLOR = {
  positive: '#39ff14',
  negative: '#ff3131',
  neutral:  '#909296',
  mixed:    '#ffcc00',
}

const IMPLICATION_COLOR = {
  BN:      '#3b82f6',
  PH:      '#ef4444',
  PN:      '#22c55e',
  unclear: '#5c5f66',
}

const TRACTION_DOTS = { low: 1, medium: 2, high: 3 }

const mono = { fontFamily: "'JetBrains Mono', monospace" }

const Field = ({ label, children }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
    <span style={{ ...mono, fontSize: '9px', color: '#5c5f66', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
      {label}
    </span>
    {children}
  </div>
)

async function fetchSignalAnalysis(articleId) {
  try {
    const res = await fetch(`${API_BASE}/analyses?article_id=${articleId}`)
    if (!res.ok) return null
    const rows = await res.json()
    const row = rows.find((r) => r.lens_name === 'social_signal')
    if (!row?.full_result) return null
    const data = typeof row.full_result === 'string' ? JSON.parse(row.full_result) : row.full_result
    return data
  } catch {
    return null
  }
}

export const SignalAnalysisPanel = ({ article, taskId, onAnalysisDone }) => {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [taskState, setTaskState] = useState('idle') // idle | running | done | failed
  const activeArticleId = useRef(null)

  const { status: taskStatus } = useTaskStream(taskId)

  // Track task progress
  useEffect(() => {
    if (!taskId) return
    if (taskStatus === 'running') setTaskState('running')
    else if (taskStatus === 'completed') {
      setTaskState('done')
      // Fetch the result once the task completes
      if (article?.id) {
        fetchSignalAnalysis(article.id).then((data) => {
          if (data) { setAnalysis(data); onAnalysisDone?.() }
        })
      }
    } else if (taskStatus === 'failed' || taskStatus === 'cancelled') {
      setTaskState('failed')
    }
  }, [taskId, taskStatus])

  // Load existing analysis when article changes
  useEffect(() => {
    if (!article) { setAnalysis(null); setTaskState('idle'); return }
    activeArticleId.current = article.id
    setLoading(true)
    fetchSignalAnalysis(article.id).then((data) => {
      if (activeArticleId.current !== article.id) return
      setAnalysis(data)
      setLoading(false)
    })
  }, [article?.id])

  const metadata = article?.metadata || {}
  const hasEngagement = metadata.score != null

  if (!article) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
          <span style={{ ...mono, fontSize: '10px', fontWeight: 700, color: '#5c5f66', letterSpacing: '0.12em' }}>
            SIGNAL
          </span>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px', opacity: 0.4 }}>
          <div style={{ fontSize: '28px', color: '#ffcc00' }}>◈</div>
          <div style={{ ...mono, fontSize: '11px', color: '#5c5f66' }}>Select a signal to see analysis</div>
        </div>
      </div>
    )
  }

  const isRunning = taskState === 'running'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>

      {/* Header */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #37340a', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ ...mono, fontSize: '10px', fontWeight: 700, color: '#5c5f66', letterSpacing: '0.12em' }}>
              SIGNAL
            </span>
            <span style={{
              ...mono, fontSize: '8px', fontWeight: 700,
              color: '#ffcc00', border: '1px solid #ffcc0060',
              borderRadius: '2px', padding: '1px 4px', letterSpacing: '0.08em',
            }}>
              {article.source}
            </span>
          </div>
          {isRunning && (
            <span style={{
              ...mono, fontSize: '9px', fontWeight: 700, color: '#ffcc00',
              animation: 'pulse 1.2s ease-in-out infinite',
            }}>
              Analysing…
            </span>
          )}
          {taskState === 'failed' && (
            <span style={{ ...mono, fontSize: '9px', color: '#ff3131' }}>Failed</span>
          )}
        </div>
        <span style={{
          ...mono, fontSize: '11px', color: '#909296',
          display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }} title={article.title}>
          {article.title}
        </span>
        {hasEngagement && (
          <span style={{ ...mono, fontSize: '9px', color: '#5c5f66', marginTop: '3px', display: 'block' }}>
            ↑{metadata.score} ⚬{metadata.num_comments}
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {['TONE', 'CLAIM', 'IMPLICATION', 'TRACTION'].map((label) => (
              <Field key={label} label={label}>
                <div style={{
                  height: '14px', borderRadius: '3px',
                  background: 'linear-gradient(90deg, #1a1b1e 25%, #2c2e33 50%, #1a1b1e 75%)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 1.5s infinite',
                  width: label === 'CLAIM' ? '100%' : '40%',
                }} />
              </Field>
            ))}
          </div>
        )}

        {!loading && !analysis && !isRunning && (
          <div style={{ ...mono, fontSize: '11px', color: '#5c5f66', textAlign: 'center', paddingTop: '40px' }}>
            Click Analyse to run signal analysis
          </div>
        )}

        {!loading && isRunning && !analysis && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {['TONE', 'CLAIM', 'IMPLICATION', 'TRACTION'].map((label) => (
              <Field key={label} label={label}>
                <div style={{
                  height: '14px', borderRadius: '3px',
                  background: 'linear-gradient(90deg, #1a1b1e 25%, #2c2e33 50%, #1a1b1e 75%)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 1.5s infinite',
                  width: label === 'CLAIM' ? '100%' : '40%',
                }} />
              </Field>
            ))}
          </div>
        )}

        {!loading && analysis && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Field label="Tone">
              <span style={{
                ...mono, fontSize: '13px', fontWeight: 700,
                color: TONE_COLOR[analysis.tone] || '#909296',
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                {analysis.tone}
              </span>
            </Field>

            <Field label="Claim">
              <span style={{ ...mono, fontSize: '11px', color: '#e0e0e0', lineHeight: 1.5 }}>
                {analysis.claim}
              </span>
            </Field>

            <Field label="Implication">
              <span style={{
                ...mono, fontSize: '13px', fontWeight: 700,
                color: IMPLICATION_COLOR[analysis.implication] || '#5c5f66',
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                {analysis.implication === 'unclear' ? '— unclear' : analysis.implication}
              </span>
            </Field>

            <Field label="Traction">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '3px' }}>
                  {[1, 2, 3].map((dot) => (
                    <div key={dot} style={{
                      width: '8px', height: '8px', borderRadius: '50%',
                      background: dot <= (TRACTION_DOTS[analysis.signal_strength] || 1)
                        ? '#ffcc00' : '#2c2e33',
                    }} />
                  ))}
                </div>
                <span style={{ ...mono, fontSize: '10px', color: '#909296' }}>
                  {analysis.signal_strength}
                </span>
              </div>
            </Field>
          </div>
        )}
      </div>
    </div>
  )
}
