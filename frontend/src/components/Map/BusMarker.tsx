import L from 'leaflet'
import { Marker, Popup } from 'react-leaflet'

export interface BusPosition {
  bus_id: string
  line_id: string
  line_name: string
  latitude: number
  longitude: number
  next_stop_id: string
  delay_min: number
  occupancy_pct: number
  occupancy_label: string
  occupancy_color: string
  color: string
}

interface Props {
  bus: BusPosition
}

function makeBusIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `
      <div style="
        width:32px;height:32px;border-radius:50%;
        background:${color};
        border:2px solid white;
        box-shadow:0 2px 6px rgba(0,0,0,0.35);
        display:flex;align-items:center;justify-content:center;
        font-size:16px;line-height:1;
      ">🚌</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  })
}

export default function BusMarker({ bus }: Props) {
  const icon = makeBusIcon(bus.color)
  const barPct = Math.min(100, Math.round(bus.occupancy_pct))

  return (
    <Marker position={[bus.latitude, bus.longitude]} icon={icon}>
      <Popup minWidth={200} maxWidth={220}>
        <div style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>{bus.line_name}</div>

          {/* Occupancy badge */}
          <div style={{
            display: 'inline-block',
            background: bus.occupancy_color,
            color: '#fff',
            borderRadius: 4,
            padding: '2px 8px',
            fontWeight: 600,
            fontSize: 12,
            marginBottom: 6,
          }}>
            {bus.occupancy_label}
          </div>

          {/* Progress bar */}
          <div style={{ background: '#eee', borderRadius: 4, height: 6, marginBottom: 8 }}>
            <div style={{
              width: `${barPct}%`,
              height: '100%',
              background: bus.occupancy_color,
              borderRadius: 4,
              transition: 'width 0.3s',
            }} />
          </div>

          <div style={{ color: '#555', fontSize: 12 }}>
            <div>Sonraki durak: <strong>{bus.next_stop_id}</strong></div>
            <div>Gecikme: <strong>{bus.delay_min} dk</strong></div>
          </div>
        </div>
      </Popup>
    </Marker>
  )
}
