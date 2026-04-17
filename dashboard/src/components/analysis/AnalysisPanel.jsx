import { useState, useEffect } from 'react'
import { Stack, Text, Tabs, Loader, Alert } from '@mantine/core'
import './AnalysisPanel.css'

const LENSES = [
  { id: 'political', label: 'Political', icon: '🏛' },
  { id: 'demographic', label: 'Demographic', icon: '👥' },
  { id: 'historical', label: 'Historical', icon: '📚' },
  { id: 'strategic', label: 'Strategic', icon: '🎯' },
  { id: 'factcheck', label: 'Fact-Check', icon: '✓' },
  { id: 'bridget_welsh', label: 'Welsh', icon: '🔍' },
]

/**
 * AnalysisPanel — 6-lens analysis display with tabs
 */
export const AnalysisPanel = ({ article, refreshTrigger, onTaskCreated }) => {
  const [analyses, setAnalyses] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('political')

  useEffect(() => {
    if (!article) {
      setAnalyses({})
      setError(null)
      return
    }

    const fetchAnalyses = async () => {
      setLoading(true)
      setError(null)
      try {
        // Fetch analyses for this article
        const res = await fetch(`http://localhost:8000/analyses?article_id=${article.id}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()

        // Group by lens
        const byLens = {}
        data.forEach((analysis) => {
          byLens[analysis.lens_name] = analysis
        })
        setAnalyses(byLens)

        if (Object.keys(byLens).length === 0) {
          setError('No analyses available for this article yet.')
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalyses()
  }, [article, refreshTrigger])

  if (!article) {
    return (
      <div className="analysis-panel empty">
        <Text size="sm" c="dimmed" ta="center">
          Select an article to see analysis
        </Text>
      </div>
    )
  }

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <Text fw={700} c="cyan" size="sm" tt="uppercase" ls={1}>
          Analysis
        </Text>
      </div>

      {loading && (
        <div className="analysis-loading">
          <Loader size="sm" color="cyan" />
          <Text size="xs" c="dimmed">
            Loading...
          </Text>
        </div>
      )}

      {error && (
        <Alert title="No data" color="yellow" className="analysis-alert">
          <Text size="xs">{error}</Text>
        </Alert>
      )}

      {!loading && Object.keys(analyses).length > 0 && (
        <Tabs value={activeTab} onTabChange={setActiveTab} className="analysis-tabs">
          <Tabs.List>
            {LENSES.map((lens) => (
              <Tabs.Tab key={lens.id} value={lens.id} leftSection={lens.icon}>
                {lens.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>

          {LENSES.map((lens) => (
            <Tabs.Panel key={lens.id} value={lens.id}>
              <LensAnalysis analysis={analyses[lens.id]} lens={lens} />
            </Tabs.Panel>
          ))}
        </Tabs>
      )}
    </div>
  )
}

/**
 * LensAnalysis — Display individual lens result
 */
const LensAnalysis = ({ analysis, lens }) => {
  if (!analysis) {
    return (
      <div className="lens-empty">
        <Text size="xs" c="dimmed">
          No {lens.label.toLowerCase()} analysis available
        </Text>
      </div>
    )
  }

  const { direction, strength, summary } = analysis

  return (
    <Stack gap="md" className="lens-content">
      {direction && (
        <div className="lens-direction">
          <Text size="xs" c="dimmed">
            Direction
          </Text>
          <Text fw={700} c="cyan" size="lg">
            {direction}
          </Text>
        </div>
      )}

      {strength !== null && strength !== undefined && (
        <div className="lens-strength">
          <Text size="xs" c="dimmed">
            Signal Strength
          </Text>
          <div className="strength-bar">
            <div className="strength-fill" style={{ width: `${strength}%` }} />
          </div>
          <Text size="xs" fw={600}>
            {Math.round(strength)}%
          </Text>
        </div>
      )}

      {summary && (
        <div className="lens-summary">
          <Text size="xs" c="dimmed">
            Summary
          </Text>
          <Text size="sm" c="white" style={{ whiteSpace: 'pre-wrap' }}>
            {summary}
          </Text>
        </div>
      )}
    </Stack>
  )
}
