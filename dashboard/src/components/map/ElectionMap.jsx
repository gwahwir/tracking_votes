import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, Popup } from 'react-leaflet'
import L from 'leaflet'
import { useSeatPredictions, useHistoricalByYear } from '../../hooks/useApi'
import { PARTY_COLORS, getConfidenceRing } from '../../theme'
import { Stack, Group, Text, Badge } from '@mantine/core'
import './ElectionMap.css'

/**
 * ElectionMap — Choropleth map with confidence rings
 * Supports both regular GeoJSON and cartogram toggle
 */
export const ElectionMap = ({ mapType = 'parlimen', useCartogram = false, onConstituencySelect }) => {
  const { predictions, loading: predictionsLoading } = useSeatPredictions()
  const { resultsByCode: historical2022 } = useHistoricalByYear(2022)
  const [geoJsonData, setGeoJsonData] = useState(null)
  const [selectedConstituency, setSelectedConstituency] = useState(null)

  // Load appropriate GeoJSON file
  useEffect(() => {
    const filename = useCartogram
      ? `johor_cartogram_${mapType}_2022.geojson`
      : `johor-${mapType}.geojson`

    fetch(`/geojson/${filename}`)
      .then((res) => res.json())
      .then((data) => setGeoJsonData(data))
      .catch((err) => console.error('Failed to load GeoJSON:', err))
  }, [mapType, useCartogram])

  // Look up prediction for a constituency
  const getPrediction = (constituencyCode) => {
    return predictions.find((p) => p.constituency_code === constituencyCode)
  }

  // Create GeoJSON feature style based on prediction
  const getFeatureStyle = (feature) => {
    const code = feature.properties?.constituency_code || feature.properties?.code_parlimen || feature.properties?.code_dun || feature.properties?.code || feature.properties?.id
    const prediction = getPrediction(code)

    if (!prediction) {
      return {
        color: '#666666',
        weight: 2,
        opacity: 0.7,
        fillColor: '#444444',
        fillOpacity: 0.4,
      }
    }

    const confRing = getConfidenceRing(prediction.confidence || 0)

    return {
      color: confRing.color,
      weight: confRing.weight,
      opacity: 1,
      fillColor: PARTY_COLORS[prediction.leading_party] || '#999999',
      fillOpacity: 0.7,
    }
  }

  const onEachFeature = (feature, layer) => {
    const code = feature.properties?.constituency_code || feature.properties?.code_parlimen || feature.properties?.code_dun || feature.properties?.code || feature.properties?.id
    const prediction = getPrediction(code)
    const name = feature.properties?.name || feature.properties?.NAME || feature.properties?.parlimen || feature.properties?.dun || code

    layer.on('click', () => {
      setSelectedConstituency({ code, name, prediction })
      if (onConstituencySelect) onConstituencySelect(code, name)
    })

    layer.on('mouseover', () => {
      const pred = getPrediction(code)
      const hist = historical2022[code]
      const histLine = hist
        ? `2022: <strong>${hist.winner_coalition || '?'}</strong> &mdash; ${hist.margin_pct != null ? hist.margin_pct.toFixed(1) + '% margin' : 'margin unknown'}`
        : '2022: no data'
      const predLine = pred
        ? `Now:&nbsp; <strong>${pred.leading_party || '?'}</strong> &mdash; ${pred.confidence ?? 0}% confidence`
        : 'Now:&nbsp; no prediction'
      const tooltipHtml = `<strong>${name}</strong> (${code})<br/>${histLine}<br/>${predLine}`
      layer.bindTooltip(tooltipHtml, { sticky: true, opacity: 0.92 }).openTooltip()
    })

    layer.on('mouseout', () => {
      layer.closeTooltip()
    })
  }

  if (!geoJsonData) {
    return <div className="election-map-loading">Loading map...</div>
  }

  return (
    <div className="election-map-container">
      <MapContainer center={[1.485, 103.74]} zoom={8} className="election-map">
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; CartoDB contributors'
          maxZoom={15}
        />
        <GeoJSON data={geoJsonData} style={getFeatureStyle} onEachFeature={onEachFeature} />
      </MapContainer>

      {selectedConstituency && (
        <div className="constituency-popup">
          <ConstituencyPopup
            code={selectedConstituency.code}
            name={selectedConstituency.name}
            prediction={selectedConstituency.prediction}
            onClose={() => setSelectedConstituency(null)}
          />
        </div>
      )}
    </div>
  )
}

/**
 * ConstituencyPopup — Show prediction details and signal breakdown
 */
const ConstituencyPopup = ({ code, name, prediction, onClose }) => {
  if (!prediction) {
    return (
      <Stack className="popup">
        <Group justify="space-between">
          <div>
            <Text fw={700} c="cyan" size="lg">
              {name}
            </Text>
            <Text c="dimmed" size="sm">
              {code}
            </Text>
          </div>
          <button className="popup-close" onClick={onClose}>
            ✕
          </button>
        </Group>
        <Text c="dimmed">No prediction data available.</Text>
      </Stack>
    )
  }

  const { leading_party, confidence, signal_breakdown, caveats, num_articles } = prediction

  return (
    <Stack className="popup">
      <Group justify="space-between">
        <div>
          <Text fw={700} c="cyan" size="lg">
            {name}
          </Text>
          <Text c="dimmed" size="sm">
            {code}
          </Text>
        </div>
        <button className="popup-close" onClick={onClose}>
          ✕
        </button>
      </Group>

      <Group>
        <Badge size="lg" color={PARTY_COLORS[leading_party] || 'gray'}>
          {leading_party || 'No Data'}
        </Badge>
        <Text fw={700} c={getConfidenceColor(confidence)}>
          {confidence}% confidence
        </Text>
      </Group>

      <Stack gap="xs" className="signal-breakdown">
        <Text fw={700} size="sm" c="cyan">
          Signal Breakdown:
        </Text>
        {signal_breakdown &&
          Object.entries(signal_breakdown).map(([lens, data]) => (
            <div key={lens} className="signal-lens">
              <Group justify="space-between">
                <Text size="sm" fw={500} tt="capitalize">
                  {lens}
                </Text>
                {data.direction && (
                  <Badge size="sm" variant="light">
                    {data.direction}
                  </Badge>
                )}
              </Group>
              {data.strength && <Text size="xs" c="dimmed">{data.strength}% strength</Text>}
              {data.summary && <Text size="xs" c="dimmed">{data.summary}</Text>}
            </div>
          ))}
      </Stack>

      {caveats && caveats.length > 0 && (
        <Stack gap="xs" className="caveats">
          <Text fw={700} size="sm" c="red">
            Caveats:
          </Text>
          <ul>
            {caveats.map((caveat, i) => (
              <li key={i}>
                <Text size="xs" c="red">
                  {caveat}
                </Text>
              </li>
            ))}
          </ul>
        </Stack>
      )}

      {num_articles && (
        <Text size="xs" c="dimmed">
          Based on {num_articles} article{num_articles !== 1 ? 's' : ''}
        </Text>
      )}
    </Stack>
  )
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 70) return 'lime'
  if (confidence >= 40) return 'yellow'
  return 'red'
}
