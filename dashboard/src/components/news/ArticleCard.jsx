import { useState } from 'react'
import { useDispatchTask } from '../../hooks/useApi'

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

export const ArticleCard = ({ article, isSelected, onSelect, onTaskCreated }) => {
  const [hovered, setHovered] = useState(false)
  const [isScoring, setIsScoring] = useState(false)
  const { dispatchTask } = useDispatchTask()

  const formatDate = (d) =>
    new Date(d).toLocaleDateString('en-MY', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  let constituencies = article.constituency_ids || []
  if (typeof constituencies === 'string') {
    try { constituencies = JSON.parse(constituencies) } catch { constituencies = [] }
  }
  if (!Array.isArray(constituencies)) constituencies = []

  const shown = constituencies.slice(0, 2).map((c) => (typeof c === 'string' ? c.split('.').pop() : c)).join(', ')
  const extra = constituencies.length > 2 ? ` +${constituencies.length - 2}` : ''

  const handleScoreArticle = async (e) => {
    e.stopPropagation()
    setIsScoring(true)
    try {
      const result = await dispatchTask('scorer_agent', {
        role: 'user',
        parts: [{ type: 'text', text: `Score this article:\n\nTitle: ${article.title}\n\nURL: ${article.url}\n\nSource: ${article.source}` }],
      })
      if (result?.task_id) onTaskCreated?.(result.task_id)
    } catch (err) {
      console.error('Failed to dispatch score task:', err)
    } finally {
      setIsScoring(false)
    }
  }

  const cardStyle = {
    padding: '10px 12px',
    background: isSelected ? '#0d1f2a' : hovered ? '#1e1f23' : '#1a1b1e',
    border: `1px solid ${isSelected ? '#00d4ff' : hovered ? '#5c5f66' : '#373a40'}`,
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    boxShadow: isSelected ? '0 0 10px rgba(0,212,255,0.1)' : 'none',
  }

  const alreadyScored = article.reliability_score != null

  return (
    <div
      style={cardStyle}
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '12px',
        fontWeight: 600,
        lineHeight: 1.4,
        color: isSelected ? '#00d4ff' : '#e0e0e0',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {article.title}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '4px' }}>
        <span style={{ fontSize: '10px', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace", textTransform: 'uppercase' }}>
          {article.source}
        </span>
        <span style={{ fontSize: '10px', color: '#5c5f66', fontFamily: "'JetBrains Mono', monospace" }}>
          {formatDate(article.created_at)}
        </span>
      </div>

      <ReliabilityBar score={article.reliability_score} />

      {shown && (
        <div style={{ fontSize: '10px', color: '#00d4ff', fontFamily: "'JetBrains Mono', monospace" }}>
          ◈ {shown}{extra}
        </div>
      )}

      <div style={{ display: 'flex', gap: '6px', marginTop: '2px' }}>
        <button
          onClick={(e) => { e.stopPropagation(); onSelect() }}
          style={{
            flex: 1,
            padding: '4px',
            background: isSelected ? '#00d4ff' : 'rgba(0,212,255,0.1)',
            border: `1px solid ${isSelected ? '#00d4ff' : '#00d4ff40'}`,
            borderRadius: '3px',
            color: isSelected ? '#000' : '#00d4ff',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            fontWeight: isSelected ? 700 : 400,
            cursor: 'pointer',
          }}
        >
          {isSelected ? '✓ Selected' : 'Select'}
        </button>
        <button
          onClick={alreadyScored ? undefined : handleScoreArticle}
          disabled={alreadyScored || isScoring}
          style={{
            flex: 1,
            padding: '4px',
            background: alreadyScored ? 'rgba(90,90,90,0.1)' : 'rgba(57,255,20,0.07)',
            border: `1px solid ${alreadyScored ? '#37373730' : '#39ff1430'}`,
            borderRadius: '3px',
            color: alreadyScored ? '#5c5f66' : '#39ff14',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            cursor: alreadyScored ? 'default' : 'pointer',
            opacity: alreadyScored ? 0.6 : 1,
          }}
        >
          {isScoring ? '...' : alreadyScored ? 'Scored' : 'Score'}
        </button>
      </div>
    </div>
  )
}
