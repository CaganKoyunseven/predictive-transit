import { useEffect, useState } from 'react'
import { api } from '../api'

export type WeatherCondition = 'clear' | 'cloudy' | 'rain' | 'snow' | 'fog' | 'wind'

export interface Weather {
  condition: WeatherCondition
  tempC: number
}

interface WeatherResponse {
  weather_condition: WeatherCondition
  temperature_c: number
}

const REFRESH_MS = 300_000

export function useWeather(): Weather | null {
  const [weather, setWeather] = useState<Weather | null>(null)

  useEffect(() => {
    function fetchWeather() {
      api.get<WeatherResponse>('/weather')
        .then(r => setWeather({ condition: r.data.weather_condition, tempC: r.data.temperature_c }))
        .catch(() => {})
    }
    fetchWeather()
    const id = window.setInterval(fetchWeather, REFRESH_MS)
    return () => window.clearInterval(id)
  }, [])

  return weather
}
