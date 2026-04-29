import { useState, useEffect } from 'react'
import { useDispatchTask, useTaskStream, useFetchArticle } from '../../hooks/useApi'

const SEAT_NAMES = {
  'P.140':'Segamat','P.141':'Sekijang','P.142':'Labis','P.143':'Pagoh','P.144':'Ledang',
  'P.145':'Bakri','P.146':'Muar','P.147':'Parit Sulong','P.148':'Ayer Hitam','P.149':'Sri Gading',
  'P.150':'Batu Pahat','P.151':'Simpang Renggam','P.152':'Kluang','P.153':'Sembrong','P.154':'Mersing',
  'P.155':'Tenggara','P.156':'Kota Tinggi','P.157':'Pengerang','P.158':'Tebrau','P.159':'Pasir Gudang',
  'P.160':'Johor Bahru','P.161':'Pulai','P.162':'Iskandar Puteri','P.163':'Kulai','P.164':'Pontian',
  'P.165':'Tanjung Piai',
  'N.01':'Buloh Kasap','N.02':'Jementah','N.03':'Pemanis','N.04':'Kemelah','N.05':'Tenang',
  'N.06':'Bekok','N.07':'Bukit Kepong','N.08':'Bukit Pasir','N.09':'Gambir','N.10':'Tangkak',
  'N.11':'Serom','N.12':'Bentayan','N.13':'Simpang Jeram','N.14':'Bukit Naning','N.15':'Maharani',
  'N.16':'Sungai Balang','N.17':'Semerah','N.18':'Sri Medan','N.19':'Yong Peng','N.20':'Semarang',
  'N.21':'Parit Yaani','N.22':'Parit Raja','N.23':'Penggaram','N.24':'Senggarang','N.25':'Rengit',
  'N.26':'Machap','N.27':'Layang-Layang','N.28':'Mengkibol','N.29':'Mahkota','N.30':'Paloh',
  'N.31':'Kahang','N.32':'Endau','N.33':'Tenggaroh','N.34':'Panti','N.35':'Pasir Raja',
  'N.36':'Sedili','N.37':'Johor Lama','N.38':'Penawar','N.39':'Tanjung Surat','N.40':'Tiram',
  'N.41':'Puteri Wangsa','N.42':'Johor Jaya','N.43':'Permas','N.44':'Larkin','N.45':'Stulang',
  'N.46':'Perling','N.47':'Kempas','N.48':'Skudai','N.49':'Kota Iskandar','N.50':'Bukit Permai',
  'N.51':'Bukit Batu','N.52':'Senai','N.53':'Benut','N.54':'Pulai Sebatang','N.55':'Pekan Nanas',
  'N.56':'Kukup',
}

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

export const ArticleCard = ({ article: initialArticle, isSelected, onSelect, onTaskCreated }) => {
  const [article, setArticle] = useState(initialArticle)
  const [hovered, setHovered] = useState(false)
  const [tagsExpanded, setTagsExpanded] = useState(false)

  // Keep in sync if parent refreshes the article list
  useEffect(() => { setArticle(initialArticle) }, [initialArticle])

  const handleScored = (updated) => setArticle(updated)

  const formatDate = (d) =>
    new Date(d).toLocaleDateString('en-MY', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  let constituencies = article.constituency_ids || []
  if (typeof constituencies === 'string') {
    try { constituencies = JSON.parse(constituencies) } catch { constituencies = [] }
  }
  if (!Array.isArray(constituencies)) constituencies = []

  const fmt = (c) => `${c}${SEAT_NAMES[c] ? ` — ${SEAT_NAMES[c]}` : ''}`
  const preview = constituencies.slice(0, 2).map(fmt).join(', ')
  const extra = constituencies.length > 2 ? ` +${constituencies.length - 2}` : ''

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

      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '12px', fontWeight: 600, lineHeight: 1.4,
        color: isSelected ? '#00d4ff' : '#e0e0e0',
        display: '-webkit-box', WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical', overflow: 'hidden',
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

      {constituencies.length > 0 && (
        <div
          onClick={(e) => { e.stopPropagation(); if (constituencies.length > 2) setTagsExpanded((p) => !p) }}
          style={{
            fontSize: '10px', color: '#00d4ff', fontFamily: "'JetBrains Mono', monospace",
            cursor: constituencies.length > 2 ? 'pointer' : 'default',
            userSelect: 'none',
          }}
        >
          {!tagsExpanded ? (
            <span>◈ {preview}{extra}</span>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {constituencies.map((c) => (
                <span key={c}>◈ {fmt(c)}</span>
              ))}
              <span style={{ color: '#5c5f66', fontSize: '9px' }}>▲ collapse</span>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: '6px', marginTop: '2px' }}>
        <button
          onClick={(e) => { e.stopPropagation(); onSelect() }}
          style={{
            flex: 1, padding: '4px',
            background: isSelected ? '#00d4ff' : 'rgba(0,212,255,0.1)',
            border: `1px solid ${isSelected ? '#00d4ff' : '#00d4ff40'}`,
            borderRadius: '3px',
            color: isSelected ? '#000' : '#00d4ff',
            fontFamily: "'JetBrains Mono', monospace", fontSize: '10px',
            fontWeight: isSelected ? 700 : 400, cursor: 'pointer',
          }}
        >
          {isSelected ? '✓ Selected' : 'Select'}
        </button>

        <ScoreButton
          article={article}
          onScored={handleScored}
          onTaskCreated={onTaskCreated}
        />
      </div>
    </div>
  )
}
