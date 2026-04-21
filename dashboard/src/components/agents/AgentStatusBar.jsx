import { useState, useEffect } from 'react'

const STATUS_COLOR = {
  completed: '#39ff14',
  running: '#00d4ff',
  pending: '#373a40',
  failed: '#ff3131',
  error: '#ff3131',
}

export const AgentStatusBar = ({ tasks = [], open, onToggle }) => {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 800)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{
      borderTop: '1px solid #373a40',
      background: '#0a0a0f',
      flexShrink: 0,
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {/* Collapsed bar — always visible */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '5px 12px',
        cursor: 'pointer',
      }} onClick={onToggle}>
        <button style={{
          background: 'transparent',
          border: 'none',
          color: '#5c5f66',
          fontSize: '10px',
          fontWeight: 700,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: '0.12em',
          cursor: 'pointer',
          padding: 0,
        }}>
          {open ? '▼' : '▲'} AGENTS
        </button>
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
          {tasks.map((task) => (
            <span key={task.id} style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: STATUS_COLOR[task.status] || '#373a40',
              opacity: task.status === 'running' ? (tick % 2 === 0 ? 1 : 0.4) : 1,
              transition: 'opacity 0.2s',
              display: 'inline-block',
            }} />
          ))}
        </div>
        {tasks.length === 0 && (
          <span style={{ fontSize: '10px', color: '#373a40' }}>No active tasks</span>
        )}
      </div>

      {/* Expanded task list */}
      {open && tasks.length > 0 && (
        <div style={{ padding: '0 12px 8px' }}>
          {tasks.map((task) => (
            <div key={task.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '4px 0',
            }}>
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: STATUS_COLOR[task.status] || '#373a40',
                opacity: task.status === 'running' ? (tick % 2 === 0 ? 1 : 0.4) : 1,
                transition: 'opacity 0.2s',
                flexShrink: 0,
              }} />
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                fontWeight: 700,
                color: task.status === 'running' ? '#00d4ff' : '#909296',
                minWidth: '120px',
              }}>{task.agent}</span>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color: '#5c5f66',
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>{task.message}</span>
              {task.ts && (
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '10px',
                  color: '#373a40',
                }}>{task.ts}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
