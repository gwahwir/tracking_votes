import { useState, useCallback, useEffect, Component } from 'react'
import { TopBar } from './TopBar'
import { Scoreboard } from './Scoreboard'
import { ElectionMap } from '../map/ElectionMap'
import { NewsFeedPanel } from '../news/NewsFeedPanel'
import { AnalysisPanel } from '../analysis/AnalysisPanel'
import { SeatDetailPanel } from '../seats/SeatDetailPanel'
import { WikiModal } from '../wiki/WikiModal'
import { AgentStatusBar } from '../agents/AgentStatusBar'
import { useDispatchTask, useSeatPredictions, useTaskStream } from '../../hooks/useApi'
import './DashboardShell.css'

class PanelErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(err) { return { error: err } }
  render() {
    if (this.state.error) return (
      <div style={{ padding: '14px', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#ff3131' }}>
        <div style={{ marginBottom: '8px', fontWeight: 700 }}>PANEL ERROR</div>
        <div style={{ color: '#909296', wordBreak: 'break-all' }}>{this.state.error.message}</div>
        <div style={{ color: '#5c5f66', marginTop: '8px', whiteSpace: 'pre-wrap' }}>{this.state.error.stack?.split('\n').slice(0,4).join('\n')}</div>
      </div>
    )
    return this.props.children
  }
}

export const DashboardShell = () => {
  const [mapType, setMapType] = useState(() => {
    try { return JSON.parse(localStorage.getItem('jem-session'))?.mapType || 'parlimen' } catch { return 'parlimen' }
  })
  const [useCartogram, setUseCartogram] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [selectedConstituency, setSelectedConstituency] = useState(null)
  const [wikiOpen, setWikiOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [activeTaskId, setActiveTaskId] = useState(null)
  const [agentPanelOpen, setAgentPanelOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const { dispatchTask } = useDispatchTask()
  const { predictions } = useSeatPredictions()
  const { status: taskStatus, nodeOutputs } = useTaskStream(activeTaskId)

  useEffect(() => {
    try {
      const prev = JSON.parse(localStorage.getItem('jem-session')) || {}
      localStorage.setItem('jem-session', JSON.stringify({ ...prev, mapType }))
    } catch {}
  }, [mapType])

  const handleMapTypeChange = useCallback((type) => setMapType(type), [])
  const handleCartogramToggle = useCallback(() => setUseCartogram((p) => !p), [])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const result = await dispatchTask('news_agent', {
        role: 'user',
        parts: [{ type: 'text', text: 'Scrape the latest news articles about Johor elections and Malaysian politics.' }],
      })
      if (result?.task_id) {
        setActiveTaskId(result.task_id)
        setAgentPanelOpen(true)
        setTimeout(() => setRefreshTrigger((p) => p + 1), 2000)
      }
    } catch (err) {
      console.error('Failed to dispatch news scrape task:', err)
    } finally {
      setTimeout(() => setRefreshing(false), 2000)
    }
  }, [dispatchTask])

  const handleArticleSelect = useCallback((article) => {
    setSelectedArticle((prev) => (prev?.id === article.id ? null : article))
    setSelectedConstituency(null)
  }, [])

  const handleConstituencySelect = useCallback((code, name) => {
    setSelectedConstituency((prev) => (prev?.code === code ? null : { code, name }))
    setSelectedArticle(null)
  }, [])

  // Derive tasks list for agent bar from current task
  const tasks = activeTaskId
    ? [{ id: activeTaskId, agent: 'news_agent', status: taskStatus || 'pending', message: nodeOutputs[nodeOutputs.length - 1] || '', ts: '' }]
    : []

  return (
    <div className="dashboard-shell">
      <TopBar
        mapType={mapType}
        useCartogram={useCartogram}
        onMapTypeChange={handleMapTypeChange}
        onCartogramToggle={handleCartogramToggle}
        onRefresh={handleRefresh}
        onWikiOpen={() => setWikiOpen(true)}
        refreshing={refreshing}
      />

      <Scoreboard predictions={predictions} />

      <div className="dashboard-content">
        <div className="column feed-column">
          <NewsFeedPanel
            selectedArticle={selectedArticle}
            onArticleSelect={handleArticleSelect}
            refreshTrigger={refreshTrigger}
            onTaskCreated={setActiveTaskId}
          />
        </div>

        <div className="column map-column">
          <ElectionMap
            mapType={mapType}
            useCartogram={useCartogram}
            onConstituencySelect={handleConstituencySelect}
          />
        </div>

        <div className="column analysis-column">
          {selectedConstituency ? (
            <PanelErrorBoundary onReset={() => setSelectedConstituency(null)}>
              <SeatDetailPanel
                constituencyCode={selectedConstituency.code}
                seatName={selectedConstituency.name}
                onClose={() => setSelectedConstituency(null)}
              />
            </PanelErrorBoundary>
          ) : (
            <AnalysisPanel
              article={selectedArticle}
              taskId={activeTaskId}
              refreshTrigger={refreshTrigger}
              onTaskCreated={setActiveTaskId}
            />
          )}
        </div>
      </div>

      <AgentStatusBar
        tasks={tasks}
        open={agentPanelOpen}
        onToggle={() => setAgentPanelOpen((p) => !p)}
      />

      {wikiOpen && <WikiModal onClose={() => setWikiOpen(false)} />}
    </div>
  )
}
