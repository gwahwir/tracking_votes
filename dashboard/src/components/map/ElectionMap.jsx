import { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import L from 'leaflet'
import { useSeatPredictions, useHistoricalByYear } from '../../hooks/useApi'
import { PARTY_COLORS, getConfidenceRing } from '../../theme'
import './ElectionMap.css'

/**
 * ElectionMap — Choropleth map with confidence rings
 * Supports both regular GeoJSON and cartogram toggle
 */
export const ElectionMap = ({ mapType = 'parlimen', useCartogram = false, onConstituencySelect }) => {
  const { predictions, loading: predictionsLoading } = useSeatPredictions()
  const { resultsByCode: historical2022 } = useHistoricalByYear(2022)
  const [geoJsonData, setGeoJsonData] = useState(null)
  const selectedLayerRef = useRef(null)
  const selectedCodeRef = useRef(null)

  // Load appropriate GeoJSON file
  useEffect(() => {
    let filename
    if (!useCartogram) {
      filename = `johor-${mapType}.geojson`
    } else if (mapType === 'parlimen') {
      filename = 'johor_cartogram_parlimen_2022.geojson'
    } else {
      filename = 'johor_cartogram_electorate_2022.geojson'
    }

    fetch(`/geojson/${filename}`)
      .then((res) => { if (!res.ok) throw new Error(`${res.status}`); return res.json() })
      .then((data) => setGeoJsonData(data))
      .catch((err) => console.error('Failed to load GeoJSON:', filename, err))
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

  const getBaseStyle = (feature) => getFeatureStyle(feature)

  const onEachFeature = (feature, layer) => {
    const code = feature.properties?.constituency_code || feature.properties?.code_parlimen || feature.properties?.code_dun || feature.properties?.code || feature.properties?.id
    const prediction = getPrediction(code)
    const name = feature.properties?.name || feature.properties?.NAME || feature.properties?.parlimen || feature.properties?.dun || code

    layer.on('click', () => {
      // Restore previous selected layer to base style
      if (selectedLayerRef.current && selectedLayerRef.current !== layer) {
        selectedLayerRef.current.setStyle(getBaseStyle(selectedLayerRef.current.feature))
      }
      selectedLayerRef.current = layer
      selectedCodeRef.current = code

      layer.setStyle({
        color: '#00d4ff',
        weight: 3,
        opacity: 1,
        fillOpacity: 0.85,
      })
      layer.bringToFront()

      if (onConstituencySelect) onConstituencySelect(code, name)
    })

    layer.on('mouseover', () => {
      // Don't override the selected layer's highlight style
      if (selectedCodeRef.current !== code) {
        layer.setStyle({
          fillOpacity: 0.95,
          weight: 2.5,
          color: '#ffffff',
          opacity: 0.8,
        })
        layer.bringToFront()
      }

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
      // Restore to selected style or base style
      if (selectedCodeRef.current === code) {
        layer.setStyle({
          color: '#00d4ff',
          weight: 3,
          opacity: 1,
          fillOpacity: 0.85,
        })
      } else {
        layer.setStyle(getBaseStyle(feature))
      }
      layer.closeTooltip()
    })
  }

  if (!geoJsonData) {
    return (
      <div className="election-map-container">
        <div className="map-panel-header">
          <span className="map-panel-label">INTERACTIVE MAP</span>
          <span className="map-panel-sublabel">{mapType.toUpperCase()}{useCartogram ? ' · CARTOGRAM' : ''}</span>
        </div>
        <div className="election-map-loading">Loading map...</div>
      </div>
    )
  }

  return (
    <div className="election-map-container">
      <div className="map-panel-header">
        <span className="map-panel-label">INTERACTIVE MAP</span>
        <span className="map-panel-sublabel">{mapType.toUpperCase()}{useCartogram ? ' · CARTOGRAM' : ''}</span>
      </div>
      <MapContainer center={[1.485, 103.74]} zoom={8} className="election-map">
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; CartoDB contributors'
          maxZoom={15}
        />
        <GeoJSON data={geoJsonData} style={getFeatureStyle} onEachFeature={onEachFeature} />
      </MapContainer>

    </div>
  )
}
