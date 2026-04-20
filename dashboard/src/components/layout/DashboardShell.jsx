import { useState, useCallback } from 'react'
import { ActionIcon, Tooltip } from '@mantine/core'
import { TopBar } from './TopBar'
import { Scoreboard } from './Scoreboard'
import { ElectionMap } from '../map/ElectionMap'
import { NewsFeedPanel } from '../news/NewsFeedPanel'
import { AnalysisPanel } from '../analysis/AnalysisPanel'
import { SeatDetailPanel } from '../seats/SeatDetailPanel'
import { WikiModal } from '../wiki/WikiModal'
import TaskMonitor from '../agents/TaskMonitor'
// import AgentGraph from '../agents/AgentGraph'
import { useDispatchTask, useSeatPredictions } from '../../hooks/useApi'
import './DashboardShell.css'

/**
 * DashboardShell — Main 3-column layout
 * Left: News feed | Center: Map | Right: Analysis
 * Bottom: Agent panel (collapsible)
 */
export const DashboardShell = () => {
  const [mapType, setMapType] = useState('parlimen')
  const [useCartogram, setUseCartogram] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [selectedConstituency, setSelectedConstituency] = useState(null) // { code, name }
  const [wikiOpen, setWikiOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [activeTaskId, setActiveTaskId] = useState(null)
  const [agentPanelOpen, setAgentPanelOpen] = useState(false)
  const { dispatchTask, loading: dispatchLoading } = useDispatchTask()
  const { predictions } = useSeatPredictions()

  const handleMapTypeChange = useCallback((type) => {
    setMapType(type)
  }, [])

  const handleCartogramToggle = useCallback(() => {
    setUseCartogram((prev) => !prev)
  }, [])

  const handleRefresh = useCallback(async () => {
    // Dispatch news_agent scrape task
    try {
      const result = await dispatchTask('news_agent', {
        role: 'user',
        parts: [
          {
            type: 'text',
            text: 'Scrape the latest news articles about Johor elections and Malaysian politics.',
          },
        ],
      })
      if (result?.task_id) {
        // Open agent panel and show task monitor
        setActiveTaskId(result.task_id)
        setAgentPanelOpen(true)
        // Refresh articles after a brief delay to allow scraping to complete
        setTimeout(() => {
          setRefreshTrigger((prev) => prev + 1)
        }, 2000)
      }
    } catch (err) {
      console.error('Failed to dispatch news scrape task:', err)
    }
  }, [dispatchTask])

  const handleArticleSelect = useCallback((article) => {
    setSelectedArticle(article)
  }, [])

  return (
    <div className={`dashboard-shell ${agentPanelOpen ? 'agent-panel-open' : ''}`}>
      <TopBar
        mapType={mapType}
        useCartogram={useCartogram}
        onMapTypeChange={handleMapTypeChange}
        onCartogramToggle={handleCartogramToggle}
        onRefresh={handleRefresh}
        onWikiOpen={() => setWikiOpen(true)}
        showWikiButton={true}
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
            onConstituencySelect={(code, name) => setSelectedConstituency({ code, name })}
          />
        </div>

        <div className="column analysis-column">
          {selectedConstituency ? (
            <SeatDetailPanel
              constituencyCode={selectedConstituency.code}
              seatName={selectedConstituency.name}
              onClose={() => setSelectedConstituency(null)}
            />
          ) : (
            <AnalysisPanel
              article={selectedArticle}
              refreshTrigger={refreshTrigger}
              onTaskCreated={setActiveTaskId}
            />
          )}
        </div>
      </div>

      {/* Agent panel (collapsible) */}
      {agentPanelOpen && activeTaskId && (
        <div className="agent-panel">
          <TaskMonitor taskId={activeTaskId} agentType="Active Task" />
        </div>
      )}

      {/* Agent panel toggle button */}
      <Tooltip label={agentPanelOpen ? 'Collapse agent panel' : 'Expand agent panel'}>
        <ActionIcon
          className="agent-panel-toggle"
          onClick={() => setAgentPanelOpen(!agentPanelOpen)}
          variant="light"
          color="cyan"
          size="lg"
        >
          {agentPanelOpen ? '▼' : '▲'} AGENTS
        </ActionIcon>
      </Tooltip>

      {wikiOpen && <WikiModal onClose={() => setWikiOpen(false)} />}
    </div>
  )
}
