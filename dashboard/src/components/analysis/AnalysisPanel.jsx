import { useState, useEffect, useRef } from 'react'
import { useTaskStream } from '../../hooks/useApi'
import './AnalysisPanel.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const LENSES = [
  { id: 'political',     label: 'Political',  short: 'POL' },
  { id: 'demographic',  label: 'Demographic', short: 'DEM' },
  { id: 'historical',   label: 'Historical',  short: 'HIST' },
  { id: 'strategic',    label: 'Strategic',   short: 'STRAT' },
  { id: 'factcheck',    label: 'Fact-Check',  short: 'FACT' },
  { id: 'bridget_welsh', label: 'Welsh',      short: 'WELSH' },
]

const StrengthBar = ({ value }) => {
  const color = value >= 70 ? '#39ff14' : value >= 40 ? '#ffcc00' : '#ff3131'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '5px', background: '#1a1b1e', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{
          width: `${value}%`, height: '100%',
          background: `linear-gradient(90deg, ${color}80, ${color})`,
          borderRadius: '3px', transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color, fontWeight: 700, minWidth: '28px' }}>
        {Math.round(value)}%
      </span>
    </div>
  )
}

const PendingLens = ({ label }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: 700, color: '#00d4ff', marginBottom: '4px', letterSpacing: '0.08em' }}>
      {label}
    </div>
    {['Direction', 'Signal Strength', 'Summary'].map((field) => (
      <div key={field} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', minWidth: '90px', textTransform: 'uppercase' }}>
          {field}
        </span>
        <div style={{
          flex: 1, height: field === 'Summary' ? '36px' : '12px',
          background: 'linear-gradient(90deg, #2c2e33 25%, #373a40 50%, #2c2e33 75%)',
          backgroundSize: '200% 100%',
          borderRadius: '3px',
          animation: 'shimmer 1.4s ease-in-out infinite',
        }} />
      </div>
    ))}
  </div>
)

const LensContent = ({ data, lens, pending }) => {
  if (pending) return <PendingLens label={lens.label} />
  if (!data) return (
    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#5c5f66', padding: '16px 0' }}>
      No {lens.label.toLowerCase()} analysis yet.
    </div>
  )
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {data.direction && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', minWidth: '90px', textTransform: 'uppercase' }}>
            Direction
          </span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '15px', color: '#00d4ff', fontWeight: 700 }}>
            {data.direction}
          </span>
        </div>
      )}
      {data.strength != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', minWidth: '90px', textTransform: 'uppercase' }}>
            Signal Strength
          </span>
          <div style={{ flex: 1 }}><StrengthBar value={data.strength} /></div>
        </div>
      )}
      {data.summary && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5c5f66', textTransform: 'uppercase' }}>
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

const StatusPill = ({ state }) => {
  if (!state || state === 'idle') return null
  const cfg = {
    scoring:   { label: 'Scoring…',   color: '#ffcc00' },
    analysing: { label: 'Analysing…', color: '#00d4ff' },
    done:      { label: 'Complete',   color: '#39ff14' },
    failed:    { label: 'Failed',     color: '#ff3131' },
  }[state] || { label: state, color: '#909296' }
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', fontWeight: 700,
      color: cfg.color, border: `1px solid ${cfg.color}40`,
      borderRadius: '3px', padding: '2px 6px', letterSpacing: '0.08em',
      animation: state === 'scoring' || state === 'analysing' ? 'pulse 1.2s ease-in-out infinite' : 'none',
    }}>
      {cfg.label}
    </span>
  )
}

async function fetchAnalyses(articleId) {
  const res = await fetch(`${API_BASE}/analyses?article_id=${articleId}`)
  if (!res.ok) return {}
  const data = await res.json()
  const byLens = {}
  data.forEach((a) => { byLens[a.lens_name] = a })
  return byLens
}

export const AnalysisPanel = ({ article, taskId, refreshTrigger, onTaskCreated }) => {
  const [analyses, setAnalyses] = useState({})
  const [loading, setLoading] = useState(false)
  const [pipelineState, setPipelineState] = useState('idle') // idle | scoring | analysing | done | failed
  const activeArticleId = useRef(null)
  const pollRef = useRef(null)

  const { status: taskStatus } = useTaskStream(taskId)

  // Translate scorer task WebSocket status → pipeline state
  useEffect(() => {
    if (!taskId) return
    if (taskStatus === 'running') setPipelineState('scoring')
    else if (taskStatus === 'completed') setPipelineState('analysing')
    else if (taskStatus === 'failed' || taskStatus === 'cancelled') setPipelineState('failed')
  }, [taskId, taskStatus])

  // Load analyses on article change or explicit refresh
  useEffect(() => {
    if (!article) { setAnalyses({}); setPipelineState('idle'); return }
    activeArticleId.current = article.id
    setLoading(true)
    fetchAnalyses(article.id).then((byLens) => {
      if (activeArticleId.current !== article.id) return
      setAnalyses(byLens)
      setLoading(false)
    })
  }, [article?.id, refreshTrigger])

  // Poll for analyses while in 'analysing' state (scorer done, analyst running)
  useEffect(() => {
    if (pipelineState !== 'analysing' || !article) return

    let ws = null
    let stopped = false

    const finish = (state) => {
      if (stopped) return
      stopped = true
      clearInterval(pollRef.current)
      ws?.close()
      setPipelineState(state)
    }

    const poll = async () => {
      const byLens = await fetchAnalyses(article.id)
      setAnalyses(byLens)
      if (Object.keys(byLens).length >= LENSES.length) finish('done')
    }

    // Find the analyst task for this article and watch its WebSocket
    const watchAnalystTask = async () => {
      try {
        const res = await fetch(`${API_BASE}/tasks?limit=20`)
        const tasks = await res.json()
        const analystTask = tasks.find(t =>
          t.type_id === 'analyst_agent' &&
          t.metadata?.article_id === article.id
        )
        if (!analystTask || stopped) return

        const wsUrl = `${API_BASE.replace(/^http/, 'ws')}/ws/tasks/${analystTask.task_id}`
        ws = new WebSocket(wsUrl)
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'state') {
              if (msg.state === 'completed') {
                fetchAnalyses(article.id).then(setAnalyses)
                finish('done')
              } else if (msg.state === 'failed' || msg.state === 'cancelled') {
                finish('failed')
              }
            }
          } catch (_) {}
        }
      } catch (_) {}
    }

    pollRef.current = setInterval(poll, 3000)
    poll()
    watchAnalystTask()
    return () => { stopped = true; clearInterval(pollRef.current); ws?.close() }
  }, [pipelineState, article?.id])

  const [activeTab, setActiveTab] = useState('political')
  const isPending = pipelineState === 'scoring' || pipelineState === 'analysing'

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
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Header */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 700, color: '#5c5f66', letterSpacing: '0.12em' }}>
            ANALYSIS
          </span>
          <StatusPill state={pipelineState} />
        </div>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#909296',
          display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }} title={article.title}>
          {article.title}
        </span>
      </div>

      {/* Lens tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #373a40', flexShrink: 0 }}>
        {LENSES.map((l) => {
          const hasData = !!analyses[l.id]
          const isActive = activeTab === l.id
          return (
            <button
              key={l.id}
              onClick={() => setActiveTab(l.id)}
              style={{
                flex: 1, padding: '7px 2px',
                background: isActive ? 'rgba(0,212,255,0.05)' : 'transparent',
                border: 'none',
                borderBottom: `2px solid ${isActive ? '#00d4ff' : 'transparent'}`,
                color: isActive ? '#00d4ff' : hasData ? '#909296' : isPending ? '#ffcc0080' : '#5c5f66',
                fontFamily: "'JetBrains Mono', monospace", fontSize: '9px',
                cursor: 'pointer', letterSpacing: '0.05em', transition: 'all 0.12s',
              }}
            >
              {l.short}
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {loading ? (
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5c5f66' }}>
            Loading…
          </div>
        ) : (
          LENSES.map((l) => activeTab === l.id && (
            <LensContent
              key={l.id}
              data={analyses[l.id]}
              lens={l}
              pending={isPending && !analyses[l.id]}
            />
          ))
        )}
      </div>
    </div>
  )
}
