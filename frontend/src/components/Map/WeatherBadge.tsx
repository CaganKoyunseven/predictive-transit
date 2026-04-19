import type { Weather } from '../../hooks/useWeather'

const CONDITION_MAP: Record<string, { icon: string; label: string }> = {
  clear:  { icon: '☀️', label: 'Clear' },
  cloudy: { icon: '☁️', label: 'Cloudy' },
  rain:   { icon: '🌧️', label: 'Rain' },
  snow:   { icon: '❄️', label: 'Snow' },
  fog:    { icon: '🌫️', label: 'Fog' },
  wind:   { icon: '💨', label: 'Windy' },
}

interface Props {
  weather: Weather
}

export default function WeatherBadge({ weather }: Props) {
  const { icon, label } = CONDITION_MAP[weather.condition] ?? CONDITION_MAP.clear
  return (
    <div
      className="
        absolute top-3 right-16 z-[1000]
        h-10 px-3 rounded-full bg-white shadow-md
        flex items-center gap-1.5
        border border-gray-200
        text-sm text-gray-700 font-medium
        pointer-events-none select-none
      "
    >
      <span>{icon}</span>
      <span>{Math.round(weather.tempC)}°C</span>
      <span className="text-gray-400">·</span>
      <span>{label}</span>
    </div>
  )
}
