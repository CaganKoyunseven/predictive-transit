import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { MapContainer as LeafletMap, Marker, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { Stop } from './BusStopMarker'
import BusMarker from './BusMarker'
import type { BusPosition } from './BusMarker'
import { api } from '../../api'
import { useMap } from 'react-leaflet'
import SearchButton from '../Search/SearchButton'
import SearchOverlay from '../Search/SearchOverlay'
import type { EnrichedStop } from '../../hooks/usePlaceSearch'

// ── Types ────────────────────────────────────────────────────────────────────

export interface SnappedStop {
  stop_id: string
  name: string
  lat: number
  lng: number
  is_terminal: boolean
  is_transfer_hub: boolean
  stop_type: string
  stop_sequence: number
  line_id: string
  line_name: string
}

interface RouteShape {
  line_id: string
  line_name: string
  color: string
  coordinates: [number, number][]
  stops: SnappedStop[]
  snapped: boolean
}


interface Props {
  onStopSelect: (stop: Stop) => void
}

// ── Constants ────────────────────────────────────────────────────────────────

const SIVAS_CENTER: [number, number] = [39.748, 37.014]
const DEBOUNCE_MS = 200
const BUS_REFRESH_MS = 30_000

// ── Stop icon ─────────────────────────────────────────────────────────────────

function makeStopIcon(color: string): L.DivIcon {
  const size = 7
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size * 2}px;height:${size * 2}px;border-radius:50%;
      background:${color};border:2px solid #fff;
      box-shadow:0 1px 4px rgba(0,0,0,0.4);
      cursor:pointer;pointer-events:all;
    "></div>`,
    iconSize: [size * 2, size * 2],
    iconAnchor: [size, size],
    tooltipAnchor: [size + 2, -size],
  })
}

// ── StopMarker — single marker with popup + prediction ───────────────────────

interface StopMarkerProps {
  snapped: SnappedStop
  color: string
  onStopClick: (stop: Stop) => void
}

interface UpcomingBus {
  line_id: string
  line_name: string
  color: string
  minutes_away: number
  delay_min: number
}

function StopMarker({ snapped, color, onStopClick }: StopMarkerProps) {
  const [upcoming, setUpcoming] = useState<UpcomingBus[] | null>(null)
  const markerRef = useRef<L.Marker>(null)
  const icon = makeStopIcon(color)

  const stop: Stop = {
    stop_id: snapped.stop_id,
    line_id: snapped.line_id,
    line_name: snapped.line_name,
    stop_sequence: snapped.stop_sequence,
    latitude: snapped.lat,
    longitude: snapped.lng,
    stop_type: snapped.stop_type,
    is_terminal: snapped.is_terminal,
    is_transfer_hub: snapped.is_transfer_hub,
  }

  function handleMouseOver() {
    if (upcoming === null) {
      api.get<{ stop_id: string; buses: UpcomingBus[] }>(`/stops/${snapped.stop_id}/upcoming`)
        .then(r => setUpcoming(r.data.buses))
        .catch(() => setUpcoming([]))
    }
  }

  return (
    <Marker
      ref={markerRef}
      position={[snapped.lat, snapped.lng]}
      icon={icon}
      eventHandlers={{
        click: (e) => { L.DomEvent.stopPropagation(e); onStopClick(stop) },
        mouseover: handleMouseOver,
      }}
      zIndexOffset={snapped.is_terminal ? 100 : 0}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        <div style={{ fontFamily: 'sans-serif', minWidth: 150 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: upcoming?.length ? 5 : 0 }}>
            {snapped.name}
          </div>
          {upcoming === null && <div style={{ fontSize: 11, color: '#888' }}>Yükleniyor...</div>}
          {upcoming?.map((bus, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '2px 0', borderTop: '1px solid #eee' }}>
              <span style={{ background: bus.color, color: '#fff', borderRadius: 3, padding: '1px 5px', fontSize: 10, fontWeight: 700 }}>
                {bus.line_id}
              </span>
              <span style={{ flex: 1, fontSize: 11, color: '#333' }}>{bus.minutes_away} dk</span>
              {bus.delay_min > 0 && (
                <span style={{ background: bus.delay_min > 5 ? '#E74C3C' : '#E67E22', color: '#fff', borderRadius: 3, padding: '1px 4px', fontSize: 10 }}>
                  +{bus.delay_min}dk
                </span>
              )}
            </div>
          ))}
        </div>
      </Tooltip>
    </Marker>
  )
}

// ── MapFlyTo ──────────────────────────────────────────────────────────────────

function MapFlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo(target, 16, { duration: 1 })
  }, [target, map])
  return null
}

// ── MapContainer ──────────────────────────────────────────────────────────────

export default function MapContainer({ onStopSelect }: Props) {
  const [routes, setRoutes] = useState<RouteShape[]>([])
  const [buses, setBuses] = useState<BusPosition[]>([])
  const [activeLineId, setActiveLineId] = useState<string | null>(null)
  const debouncingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null)

  const snappedMap = new Map<string, SnappedStop>()
  const colorMap = new Map<string, string>()
  for (const route of routes) {
    for (const s of route.stops) {
      snappedMap.set(s.stop_id, s)
      colorMap.set(s.stop_id, route.color)
    }
  }

  const allStops: EnrichedStop[] = routes.flatMap(route =>
    route.stops.map(s => ({ ...s, color: route.color }))
  )

  useEffect(() => {
    api.get<{ routes: RouteShape[] }>('/routes/all/shapes')
      .then(r => setRoutes(r.data.routes))
      .catch(() => {})
  }, [])

  useEffect(() => {
    function fetchBuses() {
      api.get<BusPosition[]>('/bus-positions').then(r => setBuses(r.data)).catch(() => {})
    }
    fetchBuses()
    const id = window.setInterval(fetchBuses, BUS_REFRESH_MS)
    return () => window.clearInterval(id)
  }, [])

  function handleStopClick(stop: Stop) {
    if (debouncingRef.current) return
    debouncingRef.current = setTimeout(() => { debouncingRef.current = null }, DEBOUNCE_MS)
    onStopSelect(stop)
  }

  function handleSearchSelect(enriched: EnrichedStop) {
    setFlyTarget([enriched.lat, enriched.lng])
    const stop: Stop = {
      stop_id: enriched.stop_id,
      line_id: enriched.line_id,
      line_name: enriched.line_name,
      stop_sequence: enriched.stop_sequence,
      latitude: enriched.lat,
      longitude: enriched.lng,
      stop_type: enriched.stop_type,
      is_terminal: enriched.is_terminal,
      is_transfer_hub: enriched.is_transfer_hub,
    }
    onStopSelect(stop)
  }

  // Deduplicate stops (a stop_id may appear in multiple routes)
  const renderedStopIds = new Set<string>()
  const stopMarkers: React.ReactElement[] = []
  for (const route of routes) {
    for (const snapped of route.stops) {
      if (renderedStopIds.has(snapped.stop_id)) continue
      renderedStopIds.add(snapped.stop_id)
      stopMarkers.push(
        <StopMarker
          key={snapped.stop_id}
          snapped={snapped}
          color={route.color}
          onStopClick={handleStopClick}
        />
      )
    }
  }

  return (
    <div className="relative h-full w-full">
      <LeafletMap
        center={SIVAS_CENTER}
        zoom={13}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {routes.map(route => {
          const isActive = activeLineId === route.line_id
          return (
            <Polyline
              key={route.line_id}
              positions={route.coordinates}
              pathOptions={{
                color: route.color,
                opacity: isActive ? 1.0 : 0.65,
                weight: isActive ? 5 : 3,
              }}
              eventHandlers={{ click: () => setActiveLineId(prev => prev === route.line_id ? null : route.line_id) }}
            />
          )
        })}

        {stopMarkers}

        {buses.map(bus => (
          <BusMarker key={bus.bus_id} bus={bus} />
        ))}

        <MapFlyTo target={flyTarget} />
      </LeafletMap>

      <SearchButton onClick={() => setSearchOpen(true)} />

      <SearchOverlay
        open={searchOpen}
        stops={allStops}
        onClose={() => setSearchOpen(false)}
        onSelect={handleSearchSelect}
      />
    </div>
  )
}
