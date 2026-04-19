# Weather Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show live temperature and weather condition in a pill badge to the left of the SearchButton on the map.

**Architecture:** Pure frontend. `useWeather` hook calls the existing `GET /api/weather` endpoint on mount and auto-refreshes every 5 minutes. `WeatherBadge` renders the pill. Both are wired into `MapContainer` alongside the existing SearchButton and LocationButton.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, axios (`api` instance at `frontend/src/api.ts`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/hooks/useWeather.ts` | Fetch `/weather`, manage state, auto-refresh |
| Create | `frontend/src/components/Map/WeatherBadge.tsx` | Pill badge UI |
| Modify | `frontend/src/components/Map/MapContainer.tsx` | Import hook + component, render badge |

---

## Task 1: `useWeather` Hook

**Files:**
- Create: `frontend/src/hooks/useWeather.ts`

The `/weather` endpoint (already live at `GET /api/weather`) returns:
```json
{ "weather_condition": "rain", "temperature_c": 12.5, ... }
```
The hook maps this to a simpler `Weather` shape and auto-refreshes every 5 minutes.

- [ ] **Step 1: Create the file**

```ts
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
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/hooks/useWeather.ts
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: useWeather hook"
```

---

## Task 2: `WeatherBadge` Component

**Files:**
- Create: `frontend/src/components/Map/WeatherBadge.tsx`

Renders a white pill badge: `☀️ 15°C · Clear`. Positioned `absolute top-3 right-16 z-[1000]` — to the left of SearchButton which sits at `right-3`. Same shadow/border style as SearchButton and LocationButton. `pointer-events-none` so it never intercepts map clicks.

- [ ] **Step 1: Create the file**

```tsx
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
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Map/WeatherBadge.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: WeatherBadge component"
```

---

## Task 3: Wire Into `MapContainer`

**Files:**
- Modify: `frontend/src/components/Map/MapContainer.tsx`

Two small changes: add imports + call the hook, then render the badge in JSX.

Current relevant import block (lines 13–16):
```ts
import LocationButton from './LocationButton'
import { useGeolocation } from '../../hooks/useGeolocation'
import type { GeoLocation } from '../../hooks/useGeolocation'
import { haversineKm } from '../../hooks/usePlaceSearch'
```

Current relevant JSX (lines 322–323):
```tsx
<SearchButton onClick={() => setSearchOpen(true)} />
<LocationButton loading={geoLoading} onClick={handleLocation} />
```

- [ ] **Step 1: Add imports**

After line 16 (`import { haversineKm } ...`), add:

```ts
import WeatherBadge from './WeatherBadge'
import { useWeather } from '../../hooks/useWeather'
```

- [ ] **Step 2: Add hook call inside `MapContainer` function**

After the existing hook calls (after `const { loading: geoLoading, getLocation } = useGeolocation()`), add:

```ts
const weather = useWeather()
```

- [ ] **Step 3: Add `WeatherBadge` to JSX**

After `<SearchButton onClick={() => setSearchOpen(true)} />`, add:

```tsx
{weather && <WeatherBadge weather={weather} />}
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Build**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npm run build
```
Expected: exits 0.

- [ ] **Step 6: Manual smoke test**

1. Ensure backend is running: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` (from project root)
2. Open `http://localhost:8000`
3. Look for a white pill badge at **top-right of the map, just to the left of the search button**
4. It should show an emoji icon, temperature in °C, and an English condition label (e.g. `☀️ 14°C · Clear`)
5. The badge should not be clickable / should not block map interaction
6. To verify the API: `curl http://localhost:8000/api/weather` — confirm `weather_condition` and `temperature_c` match what's displayed

- [ ] **Step 7: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Map/MapContainer.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: weather badge on map"
```

---

## Post-Implementation

- [ ] **Push to remote**

```bash
git push origin clean-main:main
```
