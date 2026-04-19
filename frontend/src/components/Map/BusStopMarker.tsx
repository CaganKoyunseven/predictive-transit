import { useState } from 'react'
import { CircleMarker, Popup, Tooltip } from 'react-leaflet'
import { api } from '../../api'

export interface Stop {
  stop_id: string
  line_id: string
  line_name: string
  stop_sequence: number
  latitude: number
  longitude: number
  stop_type: string
  is_terminal: boolean
  is_transfer_hub: boolean
  occupancy_pct?: number
  occupancy_color?: string
}

interface UpcomingBus {
  line_id: string
  line_name: string
  color: string
  minutes_away: number
  delay_min: number
}

interface UpcomingResponse {
  stop_id: string
  buses: UpcomingBus[]
}

interface Props {
  stop: Stop
  onClick: (stop: Stop) => void
}

function markerColor(stop: Stop): string {
  // Use occupancy color when available, fall back to type-based color
  if (stop.occupancy_color) return stop.occupancy_color
  if (stop.is_terminal) return '#ef4444'
  if (stop.is_transfer_hub) return '#f97316'
  return '#3b82f6'
}

export default function BusStopMarker({ stop, onClick }: Props) {
  const [upcoming, setUpcoming] = useState<UpcomingBus[] | null>(null)
  const [loadingUpcoming, setLoadingUpcoming] = useState(false)

  function handleClick() {
    onClick(stop)
    if (upcoming === null && !loadingUpcoming) {
      setLoadingUpcoming(true)
      api.get<UpcomingResponse>(`/stops/${stop.stop_id}/upcoming`)
        .then(r => setUpcoming(r.data.buses))
        .catch(() => setUpcoming([]))
        .finally(() => setLoadingUpcoming(false))
    }
  }

  const color = markerColor(stop)

  return (
    <CircleMarker
      center={[stop.latitude, stop.longitude]}
      radius={7}
      pathOptions={{ color, fillColor: color, fillOpacity: 0.85 }}
      eventHandlers={{ click: handleClick }}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{stop.line_name}</span>
      </Tooltip>

      <Popup minWidth={200} maxWidth={260}>
        <div style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
          {/* Stop header */}
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>
            {stop.stop_id}
          </div>

          {/* Upcoming buses */}
          {loadingUpcoming && (
            <div style={{ color: '#888', fontSize: 12 }}>Yükleniyor...</div>
          )}

          {upcoming !== null && upcoming.length === 0 && (
            <div style={{ color: '#888', fontSize: 12 }}>Yaklaşan otobüs yok</div>
          )}

          {upcoming !== null && upcoming.map((bus, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 0',
              borderBottom: i < upcoming.length - 1 ? '1px solid #f0f0f0' : 'none',
            }}>
              {/* Line badge */}
              <div style={{
                background: bus.color,
                color: '#fff',
                borderRadius: 4,
                padding: '1px 6px',
                fontSize: 11,
                fontWeight: 700,
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}>
                {bus.line_id}
              </div>

              {/* Line name */}
              <div style={{ flex: 1, fontSize: 11, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {bus.line_name}
              </div>

              {/* Minutes away */}
              <div style={{ fontWeight: 700, fontSize: 12, color: '#111', whiteSpace: 'nowrap' }}>
                {bus.minutes_away} dk
              </div>

              {/* Delay badge */}
              {bus.delay_min > 0 && (
                <div style={{
                  background: bus.delay_min > 5 ? '#E74C3C' : '#E67E22',
                  color: '#fff',
                  borderRadius: 3,
                  padding: '1px 4px',
                  fontSize: 10,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}>
                  +{bus.delay_min}dk
                </div>
              )}
            </div>
          ))}
        </div>
      </Popup>
    </CircleMarker>
  )
}
