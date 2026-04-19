import { useRef, useState } from 'react'
import { api } from '../api'

export interface StopInfo {
  stop_id: string
  stop_sequence: number
  stop_type: string
  is_terminal: boolean
  is_transfer_hub: boolean
  latitude: number
  longitude: number
}

export interface PredictResponse {
  stop_id: string
  predicted_delay_min: number
  predicted_passengers_waiting: number
  accessibility_warning: boolean
  confidence: 'low' | 'medium' | 'high'
}

interface WeatherData {
  weather_condition: string
  temperature_c: number
  precipitation_mm: number
  wind_speed_kmh: number
}

interface CacheEntry {
  ts: number
  data: PredictResponse
}

const CACHE_TTL_MS = 30_000
const WEATHER_TTL_MS = 5 * 60_000   // 5 min — matches backend cache

// Module-level weather cache (shared across all usePrediction instances)
let weatherCache: { ts: number; data: WeatherData } | null = null

async function fetchWeather(): Promise<WeatherData> {
  const now = Date.now()
  if (weatherCache && now - weatherCache.ts < WEATHER_TTL_MS) {
    return weatherCache.data
  }
  try {
    const res = await api.get<WeatherData>('/weather')
    weatherCache = { ts: now, data: res.data }
    return res.data
  } catch {
    // Fallback: clear conditions
    return { weather_condition: 'clear', temperature_c: 15, precipitation_mm: 0, wind_speed_kmh: 10 }
  }
}

export function usePrediction() {
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState<PredictResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map())

  async function predict(stop: StopInfo) {
    const cached = cacheRef.current.get(stop.stop_id)
    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
      setPrediction(cached.data)
      return
    }

    setLoading(true)
    setError(null)
    setPrediction(null)

    const now = new Date()
    const hour = now.getHours()

    // Traffic estimate from time of day
    const isRushHour = (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)
    const isNight = hour < 6 || hour >= 22
    const trafficLevel = isRushHour ? 'high' : isNight ? 'low' : 'moderate'
    const speedFactor = isRushHour ? 0.55 : isNight ? 0.9 : 0.75
    const baseDelay = isRushHour ? 12 : isNight ? 1.5 : 5
    const cumulativeDelay = +(baseDelay * (1 + stop.stop_sequence * 0.05)).toFixed(1)

    try {
      // Fetch real weather (5-min cached, falls back to defaults if API key missing)
      const weather = await fetchWeather()

      const res = await api.post<PredictResponse>('/predict', {
        stop_id: stop.stop_id,
        stop_sequence: stop.stop_sequence,
        hour_of_day: hour,
        day_of_week: now.getDay(),
        is_weekend: now.getDay() === 0 || now.getDay() === 6,
        cumulative_delay_min: cumulativeDelay,
        speed_factor: speedFactor,
        traffic_level: trafficLevel,
        weather_condition: weather.weather_condition,
        temperature_c: weather.temperature_c,
        precipitation_mm: weather.precipitation_mm,
        wind_speed_kmh: weather.wind_speed_kmh,
        is_terminal: stop.is_terminal,
        is_transfer_hub: stop.is_transfer_hub,
        stop_type: stop.stop_type,
        departure_delay_min: +(baseDelay * 0.6).toFixed(1),
        minutes_to_next_bus: 15,
      })
      cacheRef.current.set(stop.stop_id, { ts: Date.now(), data: res.data })
      setPrediction(res.data)
    } catch (err: unknown) {
      const msg = (err as { code?: string })?.code === 'ECONNABORTED'
        ? 'Server unreachable'
        : 'Prediction failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return { loading, prediction, error, predict }
}
