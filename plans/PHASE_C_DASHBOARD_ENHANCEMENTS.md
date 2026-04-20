# Phase C: Dashboard Enhancements ✅ COMPLETE

**Completed:** 2026-04-21
**Notes:** All components built (SeatDetailPanel, HistoryTable, DemographicsChart, SwingIndicator, Scoreboard). Hover tooltip shows 2022 result vs current prediction via `useHistoricalByYear(2022)` bulk fetch. Staleness indicator (24h threshold) in SeatDetailPanel. Close button returns to AnalysisPanel. Mobile/responsive not tested — verify when stack is next running.

## Goal

Upgrade the React dashboard to show historical context, seat-level detail panels, prediction trends over time, and a comparison view between current predictions and past results. Make the map interactive and informative enough for meaningful election analysis.

**Prerequisite:** Phase A (historical data loaded) and Phase B (auto-chaining working, predictions flowing) should be complete.

---

## Context: What Exists Today

### Dashboard Architecture
- **Framework:** React 18 + Vite 5 + Mantine 8 (`dashboard/`)
- **Layout:** 3-column grid in `DashboardShell.jsx` (125 lines): News Feed | Map | Analysis Panel
- **Map:** `ElectionMap.jsx` (206 lines) using React-Leaflet with choropleth styling
- **Theme:** Cyberpunk dark theme in `theme.js` (152 lines) with party colors and confidence rings
- **API hooks:** 8 custom hooks in `useApi.js` (279 lines): `useAgents`, `useArticles`, `useSeatPredictions`, `useAnalyses`, `useDispatchTask`, `useTaskStream`, `useWikiPages`, `useCancelTask`
- **API base:** Hardcoded `http://localhost:8000` in `useApi.js` line 3

### Current Map Behavior
- Colors constituencies by `leading_party` from `seat_predictions` table
- Border color/weight shows confidence ring (green 70+, amber 40-69, red 0-39)
- Click constituency -> popup with prediction details + signal breakdown
- Supports toggle between Parlimen (26 seats) and DUN (56 seats)
- Supports cartogram toggle (electorate-weighted)
- GeoJSON properties: `code_parlimen` (e.g. `"P.140"`), `code_dun` (e.g. `"N.01"`), `parlimen`/`dun` (full name)

### Current Popup (ConstituencyPopup in ElectionMap.jsx lines 103-199)
- Shows: seat name, code, leading_party badge, confidence %, signal breakdown (6 lenses), caveats, article count
- Does NOT show: historical results, demographic data, trend/swing info, linked articles

---

## Implementation Steps

### Step 1: Add new API hooks for historical and demographic data

**Modify `dashboard/src/hooks/useApi.js`** — add two new hooks:

```javascript
/**
 * Fetch historical results for a constituency
 */
export const useHistorical = (constituencyCode) => {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchResults = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/historical/${constituencyCode}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => {
    fetchResults()
  }, [fetchResults])

  return { results, loading, error }
}

/**
 * Fetch demographics for a constituency
 */
export const useDemographics = (constituencyCode) => {
  const [demographics, setDemographics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchDemographics = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/demographics/${constituencyCode}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setDemographics(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => {
    fetchDemographics()
  }, [fetchDemographics])

  return { demographics, loading, error }
}
```

Also add a hook for fetching articles filtered by constituency:

```javascript
/**
 * Fetch articles tagged to a specific constituency
 */
export const useConstituencyArticles = (constituencyCode) => {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchArticles = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/articles?constituency=${constituencyCode}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setArticles(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => {
    fetchArticles()
  }, [fetchArticles])

  return { articles, loading }
}
```

### Step 2: Create a SeatDetailPanel component

This is the main new component — a detailed view when a constituency is selected on the map.

**Create `dashboard/src/components/seats/SeatDetailPanel.jsx`:**

```jsx
import { useState } from 'react'
import { Stack, Group, Text, Badge, Tabs, Card, Progress, Divider, CloseButton } from '@mantine/core'
import { useHistorical, useDemographics, useConstituencyArticles, useSeatPredictions } from '../../hooks/useApi'
import { PARTY_COLORS, getConfidenceRing, CONFIDENCE_COLORS } from '../../theme'
import { HistoryTable } from './HistoryTable'
import { DemographicsChart } from './DemographicsChart'
import { SwingIndicator } from './SwingIndicator'

/**
 * SeatDetailPanel — Full constituency detail view
 * Replaces the simple popup when a seat is clicked on the map.
 *
 * Tabs: Overview | History | Demographics | Articles
 */
export const SeatDetailPanel = ({ constituencyCode, seatName, onClose }) => {
  const { results: history, loading: histLoading } = useHistorical(constituencyCode)
  const { demographics, loading: demoLoading } = useDemographics(constituencyCode)
  const { articles, loading: artLoading } = useConstituencyArticles(constituencyCode)
  const { predictions } = useSeatPredictions(constituencyCode)
  const prediction = predictions?.[0]

  return (
    <Stack className="seat-detail-panel">
      {/* Header */}
      <Group justify="space-between">
        <div>
          <Text fw={700} c="cyan" size="xl">{seatName}</Text>
          <Text c="dimmed" size="sm">{constituencyCode}</Text>
        </div>
        <CloseButton onClick={onClose} variant="subtle" c="dimmed" />
      </Group>

      {/* Current Prediction Summary */}
      {prediction && (
        <Card>
          <Group>
            <Badge size="lg" color={PARTY_COLORS[prediction.leading_party] || 'gray'}>
              {prediction.leading_party || 'No Data'}
            </Badge>
            <Text fw={700} c={getConfidenceColor(prediction.confidence)}>
              {prediction.confidence}% confidence
            </Text>
            <Text size="sm" c="dimmed">
              Based on {prediction.num_articles || 0} articles
            </Text>
          </Group>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <Tabs.List>
          <Tabs.Tab value="overview">Overview</Tabs.Tab>
          <Tabs.Tab value="history">History</Tabs.Tab>
          <Tabs.Tab value="demographics">Demographics</Tabs.Tab>
          <Tabs.Tab value="articles">Articles ({articles.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview">
          {/* Signal breakdown + swing indicator + quick history */}
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
```

### Step 3: Create HistoryTable sub-component

**Create `dashboard/src/components/seats/HistoryTable.jsx`:**

Shows a table of past election results with winner, margin, turnout for each election year.

```jsx
import { Table, Text, Badge, Stack } from '@mantine/core'
import { PARTY_COLORS } from '../../theme'

export const HistoryTable = ({ results, loading }) => {
  if (loading) return <Text c="dimmed">Loading history...</Text>
  if (!results?.length) return <Text c="dimmed">No historical data available.</Text>

  // Sort by year descending
  const sorted = [...results].sort((a, b) => b.election_year - a.election_year)

  return (
    <Stack gap="md" mt="sm">
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Year</Table.Th>
            <Table.Th>Winner</Table.Th>
            <Table.Th>Party</Table.Th>
            <Table.Th>Margin</Table.Th>
            <Table.Th>Turnout</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.map((r) => (
            <Table.Tr key={r.election_year}>
              <Table.Td>{r.election_year}</Table.Td>
              <Table.Td>
                <Text size="sm">{r.winner_name}</Text>
              </Table.Td>
              <Table.Td>
                <Badge size="sm" color={PARTY_COLORS[r.winner_coalition] || 'gray'}>
                  {r.winner_party} ({r.winner_coalition})
                </Badge>
              </Table.Td>
              <Table.Td>
                <Text size="sm">
                  {r.margin_pct?.toFixed(1)}%
                  <Text span c="dimmed" size="xs"> ({r.margin?.toLocaleString()} votes)</Text>
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{r.turnout_pct?.toFixed(1)}%</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {/* Candidate breakdown for most recent election */}
      {sorted[0]?.candidates && (
        <>
          <Text fw={600} size="sm" c="cyan">
            {sorted[0].election_year} Full Results
          </Text>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Candidate</Table.Th>
                <Table.Th>Party</Table.Th>
                <Table.Th>Votes</Table.Th>
                <Table.Th>%</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sorted[0].candidates
                .sort((a, b) => b.votes - a.votes)
                .map((c, i) => (
                  <Table.Tr key={i}>
                    <Table.Td>
                      <Text size="sm" fw={i === 0 ? 700 : 400}>{c.name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs" color={PARTY_COLORS[c.coalition] || 'gray'}>
                        {c.party}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{c.votes?.toLocaleString()}</Table.Td>
                    <Table.Td>
                      {sorted[0].total_votes_cast
                        ? ((c.votes / sorted[0].total_votes_cast) * 100).toFixed(1) + '%'
                        : '-'}
                    </Table.Td>
                  </Table.Tr>
                ))}
            </Table.Tbody>
          </Table>
        </>
      )}
    </Stack>
  )
}
```

### Step 4: Create DemographicsChart sub-component

**Create `dashboard/src/components/seats/DemographicsChart.jsx`:**

A horizontal bar chart showing ethnic composition, rendered with simple CSS (no charting library needed).

```jsx
import { Stack, Text, Group, Progress } from '@mantine/core'

const ETHNIC_COLORS = {
  malay: '#3366cc',
  chinese: '#ff3333',
  indian: '#ffcc00',
  others: '#999999',
}

export const DemographicsChart = ({ demographics, loading }) => {
  if (loading) return <Text c="dimmed">Loading demographics...</Text>
  if (!demographics) return <Text c="dimmed">No demographic data available.</Text>

  const segments = [
    { label: 'Malay', value: demographics.malay_pct, color: ETHNIC_COLORS.malay },
    { label: 'Chinese', value: demographics.chinese_pct, color: ETHNIC_COLORS.chinese },
    { label: 'Indian', value: demographics.indian_pct, color: ETHNIC_COLORS.indian },
    { label: 'Others', value: demographics.others_pct, color: ETHNIC_COLORS.others },
  ].filter(s => s.value > 0)

  return (
    <Stack gap="md" mt="sm">
      <Text fw={600} size="sm" c="cyan">Ethnic Composition</Text>

      {/* Stacked bar */}
      <Progress.Root size={28}>
        {segments.map((s) => (
          <Progress.Section key={s.label} value={s.value} color={s.color}>
            <Progress.Label>{s.value >= 10 ? `${s.label} ${s.value.toFixed(0)}%` : ''}</Progress.Label>
          </Progress.Section>
        ))}
      </Progress.Root>

      {/* Legend */}
      <Group gap="lg">
        {segments.map((s) => (
          <Group key={s.label} gap="xs">
            <div style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: s.color }} />
            <Text size="xs">{s.label}: {s.value.toFixed(1)}%</Text>
          </Group>
        ))}
      </Group>

      {/* Classification */}
      <Group>
        <Text size="sm" c="dimmed">Classification:</Text>
        <Text size="sm" fw={500}>{demographics.urban_rural || 'Unknown'}</Text>
      </Group>
      {demographics.region && (
        <Group>
          <Text size="sm" c="dimmed">Region:</Text>
          <Text size="sm" fw={500}>{demographics.region}</Text>
        </Group>
      )}
    </Stack>
  )
}
```

### Step 5: Create SwingIndicator sub-component

**Create `dashboard/src/components/seats/SwingIndicator.jsx`:**

Shows the predicted swing from last election result — an arrow/indicator showing direction and magnitude.

```jsx
import { Group, Text } from '@mantine/core'
import { PARTY_COLORS } from '../../theme'

/**
 * SwingIndicator — Shows swing direction and magnitude between
 * the last election result and the current prediction.
 */
export const SwingIndicator = ({ prediction, lastResult }) => {
  if (!prediction || !lastResult) return null

  const currentParty = prediction.leading_party
  const previousParty = lastResult.winner_coalition
  const sameParty = currentParty === previousParty

  return (
    <Group gap="xs">
      <Text size="sm" c="dimmed">vs 2022:</Text>
      {sameParty ? (
        <Text size="sm" c="lime" fw={500}>
          HOLD ({currentParty})
        </Text>
      ) : (
        <Text size="sm" c="red" fw={500}>
          FLIP {previousParty} -> {currentParty}
        </Text>
      )}
      {prediction.confidence && (
        <Text size="xs" c="dimmed">
          ({prediction.confidence}% confidence)
        </Text>
      )}
    </Group>
  )
}
```

### Step 6: Integrate SeatDetailPanel into DashboardShell

**Modify `dashboard/src/components/layout/DashboardShell.jsx`:**

When a constituency is selected on the map, replace the right-hand analysis panel with the SeatDetailPanel.

Add state for selected constituency:

```jsx
const [selectedConstituency, setSelectedConstituency] = useState(null) // {code, name}
```

Pass a callback to ElectionMap:

```jsx
<ElectionMap
  mapType={mapType}
  useCartogram={useCartogram}
  onConstituencySelect={(code, name) => setSelectedConstituency({ code, name })}
/>
```

Conditionally render SeatDetailPanel instead of AnalysisPanel:

```jsx
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
```

### Step 7: Update ElectionMap to emit constituency selection

**Modify `dashboard/src/components/map/ElectionMap.jsx`:**

Change `onEachFeature` (line 61) to call the parent callback instead of just setting local state:

```jsx
export const ElectionMap = ({ mapType = 'parlimen', useCartogram = false, onConstituencySelect }) => {
  // ... existing code ...

  const onEachFeature = (feature, layer) => {
    const code = feature.properties?.constituency_code || feature.properties?.code_parlimen || feature.properties?.code_dun || feature.properties?.code || feature.properties?.id
    const name = feature.properties?.name || feature.properties?.NAME || feature.properties?.parlimen || feature.properties?.dun || code

    layer.on('click', () => {
      if (onConstituencySelect) {
        onConstituencySelect(code, name)
      }
      setSelectedConstituency({ code, name, prediction: getPrediction(code) })
    })
  }
```

### Step 8: Add a comparison overlay to the map

Add a toggle to show the 2022 result colors alongside current predictions, allowing visual comparison.

**Modify `ElectionMap.jsx`** — add a `showComparison` prop:

```jsx
export const ElectionMap = ({ mapType, useCartogram, onConstituencySelect, showComparison = false }) => {
```

When `showComparison` is true, split each constituency into two halves or show a side-by-side mini-map. The simpler approach is to add a **tooltip on hover** showing both 2022 result and current prediction:

```jsx
layer.on('mouseover', (e) => {
  const prediction = getPrediction(code)
  const historical = getHistorical(code)  // From a new hook or prop
  const tooltipContent = `
    <strong>${name}</strong> (${code})<br/>
    2022: ${historical?.winner_coalition || '?'} (${historical?.margin_pct?.toFixed(1) || '?'}% margin)<br/>
    Now: ${prediction?.leading_party || 'No data'} (${prediction?.confidence || 0}% confidence)
  `
  layer.bindTooltip(tooltipContent, { sticky: true }).openTooltip()
})
```

### Step 9: Add a scoreboard / summary bar

**Create `dashboard/src/components/layout/Scoreboard.jsx`:**

A horizontal bar at the top of the map showing aggregated seat counts by party.

```jsx
import { Group, Text, Badge, Progress } from '@mantine/core'
import { PARTY_COLORS } from '../../theme'

export const Scoreboard = ({ predictions }) => {
  // Count seats by leading_party
  const counts = {}
  let total = 0
  predictions.forEach((p) => {
    if (p.leading_party) {
      counts[p.leading_party] = (counts[p.leading_party] || 0) + 1
      total++
    }
  })

  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])

  return (
    <Group gap="lg" className="scoreboard">
      {sorted.map(([party, count]) => (
        <Group key={party} gap="xs">
          <Badge color={PARTY_COLORS[party] || 'gray'} size="lg">
            {party}
          </Badge>
          <Text fw={700} size="lg" c="white">{count}</Text>
        </Group>
      ))}
      <Text c="dimmed" size="sm">
        {total} / {predictions.length} seats predicted
      </Text>
    </Group>
  )
}
```

Place this above the map in `DashboardShell.jsx`.

### Step 10: Add prediction timestamp and freshness indicator

Show when each prediction was last updated and flag stale ones.

In `SeatDetailPanel.jsx`, add:

```jsx
{prediction?.updated_at && (
  <Text size="xs" c="dimmed">
    Last updated: {new Date(prediction.updated_at).toLocaleString()}
    {isStale(prediction.updated_at) && (
      <Badge size="xs" color="red" ml="xs">STALE</Badge>
    )}
  </Text>
)}
```

Where `isStale` checks if the prediction is more than 24 hours old.

---

## Files to Create

| File | Purpose |
|------|---------|
| `dashboard/src/components/seats/SeatDetailPanel.jsx` | Main seat detail view with tabs |
| `dashboard/src/components/seats/HistoryTable.jsx` | Historical results table |
| `dashboard/src/components/seats/DemographicsChart.jsx` | Ethnic composition bar chart |
| `dashboard/src/components/seats/SwingIndicator.jsx` | Swing direction indicator |
| `dashboard/src/components/layout/Scoreboard.jsx` | Aggregated seat count bar |

## Files to Modify

| File | Change |
|------|--------|
| `dashboard/src/hooks/useApi.js` | Add `useHistorical`, `useDemographics`, `useConstituencyArticles` hooks |
| `dashboard/src/components/layout/DashboardShell.jsx` | Add `selectedConstituency` state, conditionally render SeatDetailPanel, add Scoreboard |
| `dashboard/src/components/map/ElectionMap.jsx` | Add `onConstituencySelect` callback prop, add hover tooltips with comparison |
| `control_plane/routes.py` | Add `GET /articles?constituency={code}` filter support (may already exist via `/api/news?constituency=...` on line 178) |

---

## Verification

1. Click a constituency on the map -> SeatDetailPanel opens in right column with 4 tabs
2. History tab shows 2018/2022 results with correct winners and margins
3. Demographics tab shows ethnic composition bar chart
4. Articles tab shows news articles tagged to that constituency
5. Scoreboard above map shows correct seat counts by party
6. Hover over any constituency -> tooltip shows 2022 result vs current prediction
7. Close SeatDetailPanel -> AnalysisPanel returns (for article-level analysis)
8. Mobile/responsive: panels stack vertically on narrow screens
