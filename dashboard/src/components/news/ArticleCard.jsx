import { useState } from 'react'
import { Card, Text, Group, Badge, Stack, Button, Loader } from '@mantine/core'
import { ReliabilityBadge } from './ReliabilityBadge'
import { useDispatchTask } from '../../hooks/useApi'
import './ArticleCard.css'

/**
 * ArticleCard — Single article in the feed
 */
export const ArticleCard = ({ article, isSelected, onSelect, onTaskCreated }) => {
  const { dispatchTask, loading: dispatchLoading } = useDispatchTask()
  const [isScoring, setIsScoring] = useState(false)
  const formatDate = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-MY', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  // Parse constituency_ids (may come as string from API)
  let constituencies = article.constituency_ids || []
  if (typeof constituencies === 'string') {
    try {
      constituencies = JSON.parse(constituencies)
    } catch (e) {
      constituencies = []
    }
  }
  if (!Array.isArray(constituencies)) {
    constituencies = []
  }

  const constituencyLabels = constituencies
    .slice(0, 2)
    .map((c) => (typeof c === 'string' ? c.split('.')[1] : c))
    .join(', ')

  const handleScoreArticle = async (e) => {
    e.stopPropagation()
    console.log('[ArticleCard] Score button clicked for:', article.title)
    setIsScoring(true)
    try {
      console.log('[ArticleCard] Dispatching task to scorer_agent')
      const result = await dispatchTask('scorer_agent', {
        role: 'user',
        parts: [
          {
            type: 'text',
            text: `Score this article:\n\nTitle: ${article.title}\n\nURL: ${article.url}\n\nSource: ${article.source}`,
          },
        ],
      })
      console.log('[ArticleCard] Task dispatched, result:', result)
      if (result?.task_id) {
        console.log('[ArticleCard] Opening agent panel with task:', result.task_id)
        onTaskCreated?.(result.task_id)
      }
    } catch (err) {
      console.error('[ArticleCard] Failed to dispatch score task:', err)
    } finally {
      setIsScoring(false)
    }
  }

  return (
    <Card
      className={`article-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
      withBorder
      p="md"
    >
      <Stack gap="xs">
        {/* Title */}
        <Text fw={600} size="sm" c={isSelected ? 'cyan' : 'white'} lineClamp={2}>
          {article.title}
        </Text>

        {/* Source and date */}
        <Group justify="space-between" gap="xs">
          <Text size="xs" c="dimmed" tt="capitalize">
            {article.source}
          </Text>
          <Text size="xs" c="dimmed">
            {formatDate(article.created_at)}
          </Text>
        </Group>

        {/* Reliability score */}
        {article.reliability_score !== null && article.reliability_score !== undefined && (
          <ReliabilityBadge score={article.reliability_score} />
        )}

        {/* Constituencies tagged */}
        {constituencyLabels && (
          <Text size="xs" c="cyan">
            Constituencies: {constituencyLabels}
            {(article.constituency_ids || []).length > 2 && ` +${(article.constituency_ids || []).length - 2}`}
          </Text>
        )}

        {/* Action buttons */}
        <Group gap={4}>
          <Button
            variant={isSelected ? 'filled' : 'light'}
            color="cyan"
            size="xs"
            style={{ flex: 1 }}
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
          >
            {isSelected ? 'Selected' : 'Select'}
          </Button>
          {article.reliability_score === null || article.reliability_score === undefined ? (
            <Button
              variant="light"
              color="green"
              size="xs"
              style={{ flex: 1 }}
              loading={isScoring}
              onClick={handleScoreArticle}
            >
              {isScoring ? 'Scoring...' : 'Score'}
            </Button>
          ) : (
            <Button variant="light" color="gray" size="xs" style={{ flex: 1 }} disabled>
              Scored
            </Button>
          )}
        </Group>
      </Stack>
    </Card>
  )
}
