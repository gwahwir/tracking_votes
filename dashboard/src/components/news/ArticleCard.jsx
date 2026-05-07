import { useState, useEffect } from 'react'
import { useDispatchTask, useTaskStream, useFetchArticle } from '../../hooks/useApi'
import { SEAT_NAMES, formatSeatLabel } from '../../constants/seats'

const ReliabilityBar = ({ score }) => {
  if (score == null) return null
  const color = score >= 70 ? '#39ff14' : score >= 40 ? '#ffcc00' : '#ff3131'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ flex: 1, height: '4px', background: '#2c2e33', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: '2px' }} />
      </div>
      <span style={{ fontSize: '10px', color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>
        {score}%
      </span>
    </div>
  )
}

const ScoreButton = ({ article, onScored, onTaskCreated }) => {
  const [taskId, setTaskId] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const { dispatchTask } = useDispatchTask()
  const { fetchArticle } = useFetchArticle()
  const { status } = useTaskStream(taskId)

  // Watch WebSocket status transitions
  useEffect(() => {
    if (!status) return
    if (status === 'completed') {
      // Refetch the article to get the updated reliability_score
      fetchArticle(article.id).then((updated) => {
        if (updated) onScored?.(updated)
        setPhase('done')
      })
    } else if (status === 'failed' || status === 'cancelled') {
      setPhase('error')
    }
  }, [status])

  const handleClick = async (e) => {
    e.stopPropagation()
    setPhase('running')
    try {
      const result = await dispatchTask('scorer_agent', {
        role: 'user',
        parts: [{ type: 'text', text: `Score this article:\n\nTitle: ${article.title}\n\nURL: ${article.url}\n\nSource: ${article.source}\n\n${article.content || ''}` }],
        metadata: { article_id: article.id, source: article.source, constituency_codes: article.constituency_ids || [] },
      })
      if (result?.task_id) {
        setTaskId(result.task_id)
        onTaskCreated?.(result.task_id)
      }
    } catch {
      setPhase('error')
    }
  }

  const alreadyScored = article.reliability_score != null
  const isRunning = phase === 'running'
  const isError = phase === 'error'

  let label, bg, border, color, cursor
  if (alreadyScored) {
    label = 'Scored'; bg = 'rgba(90,90,90,0.1)'; border = '#37373730'; color = '#5c5f66'; cursor = 'default'
  } else if (isRunning) {
    label = 'Scoring…'; bg = 'rgba(255,204,0,0.07)'; border = '#ffcc0040'; color = '#ffcc00'; cursor = 'default'
  } else if (isError) {
    label = 'Failed'; bg = 'rgba(255,49,49,0.07)'; border = '#ff313140'; color = '#ff3131'; cursor = 'pointer'
  } else {
    label = 'Score'; bg = 'rgba(57,255,20,0.07)'; border = '#39ff1430'; color = '#39ff14'; cursor = 'pointer'
  }

  return (
    <button
      onClick={alreadyScored || isRunning ? undefined : handleClick}
      disabled={alreadyScored || isRunning}
      style={{
        flex: 1, padding: '4px',
        background: bg, border: `1px solid ${border}`, borderRadius: '3px',
        color, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px',
        cursor, opacity: alreadyScored ? 0.6 : 1,
        animation: isRunning ? 'pulse 1.2s ease-in-out infinite' : 'none',
      }}
    >
      {label}
    </button>
  )
}

const AnalyseButton = ({ article, onTaskCreated }) => {
  const [taskId, setTaskId] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const { dispatchTask } = useDispatchTask()
  const { status } = useTaskStream(taskId)

  useEffect(() => {
    if (!status) return
    if (status === 'completed') setPhase('done')
    else if (status === 'failed' || status === 'cancelled') setPhase('error')
  }, [status])

  const handleAnalyse = async (e) => {
    e.stopPropagation()
    if (phase === 'running') return
    setPhase('running')
    try {
      const result = await dispatchTask('signals_analyser', {
        role: 'user',
        parts: [{ type: 'text', text: `Analyse this signal:\n\nTitle: ${article.title}\n\nSource: ${article.source}\n\nContent: ${article.content || ''}` }],
        metadata: { article_id: article.id },
      })
      if (result?.task_id) { setTaskId(result.task_id); onTaskCreated?.(result.task_id) }
    } catch { setPhase('error') }
  }

  const label = { idle: 'Analyse', running: 'Analysing…', done: 'Done', error: 'Retry' }[phase]
  const color = { idle: '#ffcc00', running: '#ffcc00', done: '#39ff14', error: '#ff3131' }[phase]

  return (
    <button
      onClick={handleAnalyse}
      disabled={phase === 'running'}
      style={{
        padding: '4px 8px', background: 'none',
        border: `1px solid ${color}60`, borderRadius: '3px',
        color, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px',
        cursor: phase === 'running' ? 'not-allowed' : 'pointer',
        animation: phase === 'running' ? 'pulse 1.2s ease-in-out infinite' : 'none',
      }}
    >
      {label}
    </button>
  )
}

export const ArticleCard = ({ article: initialArticle, isSelected, onSelect, onScoreTaskCreated, onSignalTaskCreated, onConstituencyClick }) => {
  const [article, setArticle] = useState(initialArticle)
  const [hovered, setHovered] = useState(false)
  const [tagsExpanded, setTagsExpanded] = useState(false)

  useEffect(() => { setArticle(initialArticle) }, [initialArticle])

  const handleScored = (updated) => setArticle(updated)

  const formatDate = (d) =>
    new Date(d).toLocaleDateString('en-MY', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const isSignal = article.source_type === 'signal'
  const accent = isSignal ? '#ffcc00' : '#00d4ff'
  const constituencies = article.constituency_ids || []
  const metadata = article.metadata || {}

  const cardStyle = {
    padding: '10px 12px',
    background: isSelected ? (isSignal ? '#1f1a00' : '#0d1f2a') : hovered ? '#1e1f23' : '#1a1b1e',
    border: `1px solid ${isSelected ? accent : hovered ? '#5c5f66' : '#373a40'}`,
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    boxShadow: isSelected ? `0 0 10px ${accent}20` : 'none',
  }

  return (
    <div
      style={cardStyle}
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Title row with optional SIGNAL badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
        {isSignal && (
          <span style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: '8px', fontWeight: 700,
            color: '#ffcc00', border: '1px solid #ffcc0060', borderRadius: '2px',
            padding: '1px 4px', letterSpacing: '0.08em', whiteSpace: 'nowrap', marginTop: '2px',
          }}>
            SIGNAL
          </span>
        )}
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '12px', fontWeight: 600, lineHeight: 1.4,
          color: isSelected ? accent : '#e0e0e0',
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {article.title}
        </div>
      </div>

      {/* Source + date row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '4px', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '10px', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace", textTransform: 'uppercase' }}>
            {article.source}
          </span>
          {/* Reddit engagement metrics */}
          {isSignal && metadata.score != null && (
            <span style={{ fontSize: '9px', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace" }}>
              ↑{metadata.score} ⚬{metadata.num_comments}
            </span>
          )}
        </div>
        <span style={{ fontSize: '10px', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace" }}>
          {formatDate(article.created_at)}
        </span>
      </div>

      {/* News: reliability bar. Signal: no bar */}
      {!isSignal && <ReliabilityBar score={article.reliability_score} />}

      {/* Constituency tags */}
      {constituencies.length > 0 && (
        <div style={{ fontSize: '10px', color: accent, fontFamily: "'JetBrains Mono', monospace", userSelect: 'none' }}>
          {!tagsExpanded ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center' }}>
              {constituencies.slice(0, 2).map((c) => (
                <span
                  key={c}
                  onClick={(e) => { e.stopPropagation(); onConstituencyClick?.(c, SEAT_NAMES[c] || c) }}
                  style={{ cursor: 'pointer' }}
                  title={`Go to ${formatSeatLabel(c)}`}
                >
                  ◈ {formatSeatLabel(c)}
                </span>
              ))}
              {constituencies.length > 2 && (
                <span
                  onClick={(e) => { e.stopPropagation(); setTagsExpanded(true) }}
                  style={{ cursor: 'pointer', color: '#5c5f66' }}
                >
                  +{constituencies.length - 2}
                </span>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {constituencies.map((c) => (
                <span
                  key={c}
                  onClick={(e) => { e.stopPropagation(); onConstituencyClick?.(c, SEAT_NAMES[c] || c) }}
                  style={{ cursor: 'pointer' }}
                  title={`Go to ${formatSeatLabel(c)}`}
                >
                  ◈ {formatSeatLabel(c)}
                </span>
              ))}
              <span
                onClick={(e) => { e.stopPropagation(); setTagsExpanded(false) }}
                style={{ color: '#5c5f66', fontSize: '9px', cursor: 'pointer' }}
              >
                ▲ collapse
              </span>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '2px' }}>
        <button
          onClick={(e) => { e.stopPropagation(); onSelect() }}
          style={{
            flex: 1, padding: '4px',
            background: isSelected ? accent : `${accent}1a`,
            border: `1px solid ${isSelected ? accent : `${accent}40`}`,
            borderRadius: '3px',
            color: isSelected ? (isSignal ? '#000' : '#000') : accent,
            fontFamily: "'JetBrains Mono', monospace", fontSize: '10px',
            fontWeight: isSelected ? 700 : 400, cursor: 'pointer',
          }}
        >
          {isSelected ? '✓ Selected' : 'Select'}
        </button>

        {isSignal ? (
          <AnalyseButton article={article} onTaskCreated={onSignalTaskCreated} />
        ) : (
          <ScoreButton article={article} onScored={handleScored} onTaskCreated={onScoreTaskCreated} />
        )}
      </div>
    </div>
  )
}
