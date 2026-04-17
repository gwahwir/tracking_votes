import { useEffect, useState } from 'react'
import { Stack, Text, Loader, Group, Badge } from '@mantine/core'
import { useArticles } from '../../hooks/useApi'
import { ArticleCard } from './ArticleCard'
import './NewsFeedPanel.css'

/**
 * NewsFeedPanel — Scrollable list of news articles
 */
export const NewsFeedPanel = ({ selectedArticle, onArticleSelect, refreshTrigger, onTaskCreated }) => {
  const { articles, loading, error, refetch } = useArticles()
  const [displayArticles, setDisplayArticles] = useState([])

  useEffect(() => {
    refetch()
  }, [refreshTrigger, refetch])

  useEffect(() => {
    setDisplayArticles(articles)
  }, [articles])

  return (
    <div className="news-feed-panel">
      <div className="feed-header">
        <Text fw={700} c="cyan" size="sm" tt="uppercase" ls={1}>
          News Feed
        </Text>
        {displayArticles.length > 0 && (
          <Badge size="sm" variant="light" color="cyan">
            {displayArticles.length}
          </Badge>
        )}
      </div>

      {loading && (
        <div className="feed-loading">
          <Loader size="sm" color="cyan" />
        </div>
      )}

      {error && (
        <div className="feed-error">
          <Text size="xs" c="red">
            Failed to load articles
          </Text>
        </div>
      )}

      <div className="feed-scroll">
        {displayArticles.length === 0 && !loading && (
          <div className="feed-empty">
            <Text size="xs" c="dimmed">
              No articles yet
            </Text>
          </div>
        )}

        <Stack gap="xs">
          {displayArticles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              isSelected={selectedArticle?.id === article.id}
              onSelect={() => onArticleSelect(article)}
              onTaskCreated={onTaskCreated}
            />
          ))}
        </Stack>
      </div>
    </div>
  )
}
