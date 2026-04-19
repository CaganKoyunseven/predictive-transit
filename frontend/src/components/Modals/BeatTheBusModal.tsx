import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Polyline } from 'react-leaflet'
import { api } from '../../api'
import type { Stop } from '../Map/BusStopMarker'
import 'leaflet/dist/leaflet.css'

interface Props {
  stop: Stop
  onClose: () => void
}

interface ChallengeResult {
  challenge: boolean
  walking_time_min?: number
  bus_time_min?: number
  time_saved_min?: number
  calories_burned?: number
  walking_distance_m?: number
  reason?: string
}

export default function BeatTheBusModal({ stop, onClose }: Props) {
  const [result, setResult] = useState<ChallengeResult | null>(null)
  const [userPos, setUserPos] = useState<[number, number] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    navigator.geolocation.getCurrentPosition(
      async pos => {
        const { latitude, longitude } = pos.coords
        setUserPos([latitude, longitude])
        try {
          const res = await api.post<ChallengeResult>('/challenge/beat-the-bus', {
            user_lat: latitude,
            user_lng: longitude,
            target_stop_lat: stop.latitude,
            target_stop_lng: stop.longitude,
            bus_eta_min: 15,
            user_weight_kg: 70,
          })
          setResult(res.data)
        } catch {
          setError('Could not reach server.')
        } finally {
          setLoading(false)
        }
      },
      () => {
        setError('Location permission denied.')
        setLoading(false)
      }
    )
  }, [stop])

  return (
    <div className="fixed inset-0 bg-black/40 z-[1000] flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-5 w-full max-w-sm flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">🚶 Beat the Bus</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>

        {loading && <p className="text-sm text-gray-500 text-center py-4">Getting your location…</p>}
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}

        {result && !loading && (
          <>
            {result.challenge ? (
              <>
                <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-center">
                  <p className="text-green-700 font-bold text-xl">You can win! 🏆</p>
                  <p className="text-green-600 text-sm mt-1">
                    Arrive <strong>{result.time_saved_min} min</strong> earlier
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="font-semibold text-gray-800">{result.walking_time_min} min</p>
                    <p className="text-xs text-gray-500">Walk</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="font-semibold text-gray-800">{result.calories_burned} kcal</p>
                    <p className="text-xs text-gray-500">Burn</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="font-semibold text-gray-800">{result.walking_distance_m}m</p>
                    <p className="text-xs text-gray-500">Distance</p>
                  </div>
                </div>

                {userPos && (
                  <div className="rounded-xl overflow-hidden h-40">
                    <MapContainer
                      center={userPos}
                      zoom={15}
                      className="h-full w-full"
                      zoomControl={false}
                      attributionControl={false}
                    >
                      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                      <Polyline
                        positions={[userPos, [stop.latitude, stop.longitude]]}
                        pathOptions={{ color: '#22c55e', weight: 4 }}
                      />
                    </MapContainer>
                  </div>
                )}

                <button
                  onClick={onClose}
                  className="w-full py-2.5 rounded-xl bg-green-500 text-white font-medium hover:bg-green-600"
                >
                  Accept Challenge!
                </button>
              </>
            ) : (
              <div className="text-center py-4">
                <p className="text-gray-600 font-medium">Bus is faster this time 🚌</p>
                <p className="text-sm text-gray-500 mt-1">
                  Walk {result.walking_time_min} min vs bus {result.bus_time_min} min
                </p>
                <button
                  onClick={onClose}
                  className="mt-4 px-6 py-2 rounded-xl border border-gray-300 text-gray-700 hover:bg-gray-50"
                >
                  Got it
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
