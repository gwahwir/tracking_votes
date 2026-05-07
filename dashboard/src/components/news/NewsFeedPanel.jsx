import { useEffect, useState } from 'react'
import { useArticles } from '../../hooks/useApi'
import { ArticleCard } from './ArticleCard'
import './NewsFeedPanel.css'

export const NewsFeedPanel = ({ selectedArticle, onArticleSelect, refreshTrigger, onScoreTaskCreated, onSignalTaskCreated, onScrape, scraping, onConstituencyClick }) => {
  const { articles, loading, error, refetch } = useArticles()
  const [sourceFilter, setSourceFilter] = useState(() => {
    try { return localStorage.getItem('jem-feed-filter') || 'all' } catch { return 'all' }
  })

  useEffect(() => { refetch() }, [refreshTrigger, refetch])

  const displayArticles = sourceFilter === 'all' ? articles
    : articles.filter((a) => (sourceFilter === 'signals' ? a.source_type === 'signal' : a.source_type !== 'signal'))

  const handleFilterChange = (f) => {
    setSourceFilter(f)
    try { localStorage.setItem('jem-feed-filter', f) } catch {}
  }

  const filterChips = [
    { key: 'all', label: 'All' },
    { key: 'news', label: 'News' },
    { key: 'signals', label: 'Signals' },
  ]

  return (
    <div className="news-feed-panel">
      <div className="feed-header">
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '10px',
          fontWeight: 700,
          color: '#5c5f66',
          letterSpacing: '0.12em',
        }}>NEWS FEED</span>
        <span style={{
          background: '#1a1b1e',
          border: '1px solid #373a40',
          borderRadius: '10px',
          padding: '1px 7px',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '10px',
          color: '#909296',
        }}>{displayArticles.length}</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {filterChips.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleFilterChange(key)}
              style={{
                background: sourceFilter === key ? (key === 'signals' ? '#ffcc0020' : 'rgba(0,212,255,0.1)') : 'none',
                border: `1px solid ${sourceFilter === key ? (key === 'signals' ? '#ffcc0060' : '#00d4ff40') : '#373a40'}`,
                borderRadius: '3px',
                color: sourceFilter === key ? (key === 'signals' ? '#ffcc00' : '#00d4ff') : '#5c5f66',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '9px', fontWeight: 700,
                letterSpacing: '0.06em',
                padding: '2px 6px', cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={onScrape}
            disabled={scraping}
            style={{
              background: 'none',
              border: '1px solid #373a40',
              borderRadius: '3px',
              color: scraping ? '#5c5f66' : '#909296',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              padding: '2px 6px',
              cursor: scraping ? 'not-allowed' : 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => { if (!scraping) { e.target.style.color = '#c1c2c5'; e.target.style.borderColor = '#5c5f66' }}}
            onMouseLeave={e => { e.target.style.color = scraping ? '#5c5f66' : '#909296'; e.target.style.borderColor = '#373a40' }}
          >
            {scraping ? 'SCRAPING…' : 'SCRAPE'}
          </button>
        </div>
      </div>

      <div className="feed-scroll">
        {loading && (
          <div style={{ padding: '20px', textAlign: 'center', color: '#5c5f66', fontSize: '10px', fontFamily: "'JetBrains Mono', monospace" }}>
            Loading...
          </div>
        )}
        {error && (
          <div style={{ padding: '10px', color: '#ff3131', fontSize: '10px', fontFamily: "'JetBrains Mono', monospace" }}>
            Failed to load articles
          </div>
        )}
        {!loading && displayArticles.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center', color: '#5c5f66', fontSize: '10px', fontFamily: "'JetBrains Mono', monospace" }}>
            No articles yet
          </div>
        )}
        <div className="feed-list">
          {displayArticles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              isSelected={selectedArticle?.id === article.id}
              onSelect={() => onArticleSelect(article)}
              onScoreTaskCreated={onScoreTaskCreated}
              onSignalTaskCreated={onSignalTaskCreated}
              onConstituencyClick={onConstituencyClick}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
