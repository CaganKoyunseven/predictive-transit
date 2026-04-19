# Weather Widget — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Overview

A small weather badge displayed to the left of the SearchButton on the map. Shows current temperature and condition fetched from the existing `/weather` backend endpoint (Open-Meteo, 5-minute server-side cache, Sivas coordinates).

## Architecture

Pure frontend — no backend changes. A `useWeather` hook calls `GET /weather` on mount and auto-refreshes every 5 minutes. A `WeatherBadge` component renders the result as a pill badge next to SearchButton.

**New files:**
- `frontend/src/hooks/useWeather.ts` — fetches `/weather`, manages loading/error state, auto-refresh interval
- `frontend/src/components/Map/WeatherBadge.tsx` — pill badge UI

**Modified files:**
- `frontend/src/components/Map/MapContainer.tsx` — mount WeatherBadge outside LeafletMap

## API

`GET /weather` returns:
```ts
{
  weather_condition: "clear" | "cloudy" | "rain" | "snow" | "fog" | "wind"
  temperature_c: number      // e.g. 12.5
  precipitation_mm: number
  wind_speed_kmh: number
  description: string        // Turkish, not used by frontend
  source: "open-meteo" | "fallback"
}
```

## Data Flow

1. `MapContainer` mounts → `useWeather()` called
2. Hook calls `api.get('/weather')` immediately
3. `setInterval` re-calls every 300 000ms (5 min)
4. On success: `weather` state set → `WeatherBadge` renders
5. On error or while loading: `WeatherBadge` not rendered (silent fail)

## Components

### `useWeather`
```ts
export interface Weather {
  condition: "clear" | "cloudy" | "rain" | "snow" | "fog" | "wind"
  tempC: number
}

export function useWeather(): Weather | null
```
- Calls `api.get<WeatherResponse>('/weather')` on mount
- `setInterval` every 300 000ms
- Returns `null` while loading or on error
- Cleans up interval on unmount

### `WeatherBadge`
```tsx
interface Props { weather: Weather }
export default function WeatherBadge({ weather }: Props)
```
- `absolute top-3 right-16 z-[1000]`
- White pill: `rounded-full bg-white shadow-md border border-gray-200 px-3 h-10`
- Content: `{icon} {Math.round(tempC)}°C · {label}`
- Same visual style as SearchButton and LocationButton

**Condition → icon + label mapping:**
| condition | icon | label |
|-----------|------|-------|
| clear     | ☀️   | Clear |
| cloudy    | ☁️   | Cloudy |
| rain      | 🌧️   | Rain |
| snow      | ❄️   | Snow |
| fog       | 🌫️   | Fog |
| wind      | 💨   | Windy |

### MapContainer change
After `<SearchButton onClick={...} />`, add:
```tsx
{weather && <WeatherBadge weather={weather} />}
```
Where `weather` comes from `const weather = useWeather()` inside MapContainer.

## Error States

| Condition | Behaviour |
|-----------|-----------|
| Loading | Badge not rendered |
| Network error | Badge not rendered (silent) |
| `source: "fallback"` | Badge renders with fallback values (15°C, clear) |

## Out of Scope
- Animated weather icons
- Hourly / daily forecast
- Click-to-expand weather detail
- Location-based weather (uses fixed Sivas coordinates from backend)
