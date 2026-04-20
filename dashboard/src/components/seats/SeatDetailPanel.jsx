import { Stack, Group, Text, Badge, Tabs, Card, ActionIcon } from '@mantine/core'
import { useHistorical, useDemographics, useConstituencyArticles, useSeatPredictions } from '../../hooks/useApi'
import { PARTY_COLORS, getConfidenceRing } from '../../theme'
import { HistoryTable } from './HistoryTable'
import { DemographicsChart } from './DemographicsChart'
import { SwingIndicator } from './SwingIndicator'

const ISTALENESS_HOURS = 24

const isStale = (updatedAt) => {
  if (!updatedAt) return false
  return (Date.now() - new Date(updatedAt).getTime()) > ISTALENESS_HOURS * 3600 * 1000
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 70) return 'lime'
  if (confidence >= 40) return 'yellow'
  return 'red'
}

const OverviewTab = ({ prediction, history, demographics }) => {
  const lastResult = history?.sort((a, b) => b.election_year - a.election_year)[0] ?? null

  return (
    <Stack gap="sm" mt="sm">
      <SwingIndicator prediction={prediction} lastResult={lastResult} />

      {prediction?.signal_breakdown && (
        <>
          <Text fw={600} size="sm" c="cyan">Signal Breakdown</Text>
          <Stack gap="xs">
            {Object.entries(prediction.signal_breakdown).map(([lens, data]) => {
              if (!data) return null
              return (
                <Group key={lens} justify="space-between" wrap="nowrap">
                  <Text size="xs" tt="capitalize" style={{ minWidth: 90 }}>{lens.replace('_', ' ')}</Text>
                  {data.direction && (
                    <Badge size="xs" variant="light">{data.direction}</Badge>
                  )}
                  {data.strength != null && (
                    <Text size="xs" c="dimmed">{data.strength}%</Text>
                  )}
                </Group>
              )
            })}
          </Stack>
        </>
      )}

      {prediction?.caveats?.length > 0 && (
        <>
          <Text fw={600} size="sm" c="red">Caveats</Text>
          {prediction.caveats.map((c, i) => (
            <Text key={i} size="xs" c="red">• {c}</Text>
          ))}
        </>
      )}
    </Stack>
  )
}

const ArticlesList = ({ articles, loading }) => {
  if (loading) return <Text c="dimmed" size="sm" mt="sm">Loading articles...</Text>
  if (!articles?.length) return <Text c="dimmed" size="sm" mt="sm">No articles tagged to this constituency.</Text>

  return (
    <Stack gap="xs" mt="sm">
      {articles.map((a) => (
        <Card key={a.id} p="xs">
          <Text size="sm" fw={500} lineClamp={2}>{a.title}</Text>
          <Group gap="xs" mt={4}>
            <Text size="xs" c="dimmed">{a.source}</Text>
            {a.reliability_score != null && (
              <Badge size="xs" color={a.reliability_score >= 60 ? 'lime' : 'orange'}>
                score {a.reliability_score}
              </Badge>
            )}
            {a.published_at && (
              <Text size="xs" c="dimmed">
                {new Date(a.published_at).toLocaleDateString()}
              </Text>
            )}
          </Group>
        </Card>
      ))}
    </Stack>
  )
}

/**
 * SeatDetailPanel — Full constituency detail view with 4 tabs.
 * Renders in the right column when a constituency is selected on the map.
 */
export const SeatDetailPanel = ({ constituencyCode, seatName, onClose }) => {
  const { results: history, loading: histLoading } = useHistorical(constituencyCode)
  const { demographics, loading: demoLoading } = useDemographics(constituencyCode)
  const { articles, loading: artLoading } = useConstituencyArticles(constituencyCode)
  const { predictions } = useSeatPredictions(constituencyCode)
  const prediction = predictions?.[0] ?? null

  const stale = prediction ? isStale(prediction.updated_at) : false

  return (
    <Stack className="seat-detail-panel" gap="sm" style={{ height: '100%', overflow: 'auto', padding: '0.75rem' }}>
      {/* Header */}
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Text fw={700} c="cyan" size="lg">{seatName}</Text>
          <Text c="dimmed" size="xs">{constituencyCode}</Text>
        </div>
        <ActionIcon onClick={onClose} variant="subtle" color="gray" size="sm">✕</ActionIcon>
      </Group>

      {/* Current prediction summary */}
      {prediction ? (
        <Card p="sm">
          <Group gap="sm" wrap="nowrap">
            <Badge
              size="lg"
              style={
                PARTY_COLORS[prediction.leading_party]
                  ? { backgroundColor: PARTY_COLORS[prediction.leading_party], color: '#fff' }
                  : {}
              }
            >
              {prediction.leading_party || 'No Data'}
            </Badge>
            <Text fw={700} c={getConfidenceColor(prediction.confidence)} size="sm">
              {prediction.confidence}% confidence
            </Text>
            <Text size="xs" c="dimmed">
              {prediction.num_articles ?? 0} articles
            </Text>
            {stale && <Badge size="xs" color="red">STALE</Badge>}
          </Group>
          {prediction.updated_at && (
            <Text size="xs" c="dimmed" mt={4}>
              Updated {new Date(prediction.updated_at).toLocaleString()}
            </Text>
          )}
        </Card>
      ) : (
        <Text c="dimmed" size="sm">No prediction data yet.</Text>
      )}

      {/* Tabs */}
      <Tabs defaultValue="overview" style={{ flex: 1 }}>
        <Tabs.List>
          <Tabs.Tab value="overview">Overview</Tabs.Tab>
          <Tabs.Tab value="history">History</Tabs.Tab>
          <Tabs.Tab value="demographics">Demographics</Tabs.Tab>
          <Tabs.Tab value="articles">Articles {articles.length > 0 && `(${articles.length})`}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview">
          <OverviewTab prediction={prediction} history={history} demographics={demographics} />
        </Tabs.Panel>

        <Tabs.Panel value="history">
          <HistoryTable results={history} loading={histLoading} />
        </Tabs.Panel>

        <Tabs.Panel value="demographics">
          <DemographicsChart demographics={demographics} loading={demoLoading} />
        </Tabs.Panel>

        <Tabs.Panel value="articles">
          <ArticlesList articles={articles} loading={artLoading} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
