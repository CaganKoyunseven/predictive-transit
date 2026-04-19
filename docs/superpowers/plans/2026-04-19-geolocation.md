# Geolocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Konumum" button that shows the user's GPS position on the map, centers the view, and highlights the nearest bus stop with a larger marker.

**Architecture:** Pure frontend. `useGeolocation` wraps `navigator.geolocation.getCurrentPosition`. `haversineKm` (already in `usePlaceSearch.ts`) is exported and reused in `MapContainer` to find the nearest stop. `StopMarker` gets an `isNearest` prop for the highlight style. `MapFlyTo` (already present) reuses `flyTarget` state for centering.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Leaflet / react-leaflet, Browser Geolocation API

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/hooks/usePlaceSearch.ts` | Export `haversineKm` |
| Create | `frontend/src/hooks/useGeolocation.ts` | `getCurrentPosition` wrapper, loading/error state |
| Create | `frontend/src/components/Map/LocationButton.tsx` | Trigger button, bottom-right |
| Modify | `frontend/src/components/Map/MapContainer.tsx` | userLocation state, nearestStopId, toast, user marker, StopMarker `isNearest` prop |

---

## Task 1: Export `haversineKm`

**Files:**
- Modify: `frontend/src/hooks/usePlaceSearch.ts`

- [ ] **Step 1: Add `export` keyword to `haversineKm`**

In `frontend/src/hooks/usePlaceSearch.ts`, line 22, change:
```ts
// before
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
```
```ts
// after
export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/hooks/usePlaceSearch.ts
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "refactor: export haversineKm for reuse"
```

---

## Task 2: `useGeolocation` Hook

**Files:**
- Create: `frontend/src/hooks/useGeolocation.ts`

- [ ] **Step 1: Create the file**

```ts
import { useState } from 'react'

export interface GeoLocation {
  lat: number
  lng: number
}

export function useGeolocation() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function getLocation(): Promise<GeoLocation> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        const msg = 'Konum alınamadı, tekrar deneyin'
        setError(msg)
        reject(msg)
        return
      }
      setLoading(true)
      setError(null)
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLoading(false)
          resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        },
        (err) => {
          setLoading(false)
          const msg = err.code === 1
            ? 'Konum izni verilmedi'
            : 'Konum alınamadı, tekrar deneyin'
          setError(msg)
          reject(msg)
        },
        { timeout: 10_000, maximumAge: 0 },
      )
    })
  }

  return { loading, error, getLocation }
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
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/hooks/useGeolocation.ts
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: useGeolocation hook"
```

---

## Task 3: `LocationButton` Component

**Files:**
- Create: `frontend/src/components/Map/LocationButton.tsx`

- [ ] **Step 1: Create the file**

```tsx
interface Props {
  loading: boolean
  onClick: () => void
}

export default function LocationButton({ loading, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      aria-label="Konumumu göster"
      className="
        absolute bottom-20 right-3 z-[1000]
        w-10 h-10 rounded-full bg-white shadow-md
        flex items-center justify-center
        hover:bg-gray-50 active:scale-95 transition-transform
        border border-gray-200
        disabled:opacity-60 disabled:cursor-not-allowed
      "
    >
      {loading ? (
        <svg className="w-5 h-5 text-blue-500 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
      )}
    </button>
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
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Map/LocationButton.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: LocationButton component"
```

---

## Task 4: Wire Into `MapContainer`

**Files:**
- Modify: `frontend/src/components/Map/MapContainer.tsx`

This task makes 6 targeted changes to MapContainer:
1. Add imports
2. Modify `makeStopIcon` to support nearest highlight
3. Add `isNearest` prop to `StopMarker`
4. Add state + logic in `MapContainer` function body
5. Add user location `<Marker>` + `<LocationButton>` + toast to JSX
6. Pass `isNearest` when building `stopMarkers`

- [ ] **Step 1: Add imports**

After line 12 (`import type { EnrichedStop } ...`), add:

```ts
import LocationButton from './LocationButton'
import { useGeolocation } from '../../hooks/useGeolocation'
import type { GeoLocation } from '../../hooks/useGeolocation'
import { haversineKm } from '../../hooks/usePlaceSearch'
```

- [ ] **Step 2: Modify `makeStopIcon` to support nearest highlight**

Replace the existing `makeStopIcon` function (lines 51–65) with:

```ts
function makeStopIcon(color: string, nearest = false): L.DivIcon {
  const r = nearest ? 10 : 7
  const border = nearest ? '3px solid #fff' : '2px solid #fff'
  const shadow = nearest
    ? '0 0 0 4px rgba(37,99,235,0.35), 0 2px 8px rgba(0,0,0,0.4)'
    : '0 1px 4px rgba(0,0,0,0.4)'
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${r * 2}px;height:${r * 2}px;border-radius:50%;
      background:${color};border:${border};
      box-shadow:${shadow};
      cursor:pointer;pointer-events:all;
    "></div>`,
    iconSize: [r * 2, r * 2],
    iconAnchor: [r, r],
    tooltipAnchor: [r + 2, -r],
  })
}
```

- [ ] **Step 3: Add `isNearest` prop to `StopMarker`**

Replace the `StopMarkerProps` interface (around line 69–73):

```ts
interface StopMarkerProps {
  snapped: SnappedStop
  color: string
  isNearest: boolean
  onStopClick: (stop: Stop) => void
}
```

And update the `StopMarker` function signature and icon call. Replace:
```ts
function StopMarker({ snapped, color, onStopClick }: StopMarkerProps) {
```
with:
```ts
function StopMarker({ snapped, color, isNearest, onStopClick }: StopMarkerProps) {
```

Replace the `const icon = makeStopIcon(color)` line with:
```ts
const icon = makeStopIcon(color, isNearest)
```

Update the `<Tooltip>` to stay open when nearest. Replace:
```tsx
<Tooltip direction="top" offset={[0, -8]}>
```
with:
```tsx
<Tooltip direction="top" offset={[0, -8]} permanent={isNearest}>
```

- [ ] **Step 4: Add state and logic inside `MapContainer` function**

After the existing `useState` lines (after `flyTarget` line), add:

```ts
const [userLocation, setUserLocation] = useState<GeoLocation | null>(null)
const [nearestStopId, setNearestStopId] = useState<string | null>(null)
const [toastMsg, setToastMsg] = useState<string | null>(null)
const { loading: geoLoading, getLocation } = useGeolocation()
```

After `allStops` derivation, add the nearest-stop effect:

```ts
useEffect(() => {
  if (!userLocation || allStops.length === 0) return
  let bestId: string | null = null
  let bestDist = Infinity
  for (const s of allStops) {
    const d = haversineKm(userLocation.lat, userLocation.lng, s.lat, s.lng)
    if (d < bestDist) { bestDist = d; bestId = s.stop_id }
  }
  setNearestStopId(bestDist <= 2 ? bestId : null)
}, [userLocation, allStops])
```

Add the `handleLocation` function after `handleSearchSelect`:

```ts
async function handleLocation() {
  try {
    const loc = await getLocation()
    setUserLocation(loc)
    setFlyTarget([loc.lat, loc.lng])
  } catch (msg) {
    setToastMsg(msg as string)
    setTimeout(() => setToastMsg(null), 3000)
  }
}
```

- [ ] **Step 5: Pass `isNearest` when building `stopMarkers`**

In the `stopMarkers` building loop, replace:

```tsx
stopMarkers.push(
  <StopMarker
    key={snapped.stop_id}
    snapped={snapped}
    color={route.color}
    onStopClick={handleStopClick}
  />
)
```

with:

```tsx
stopMarkers.push(
  <StopMarker
    key={snapped.stop_id}
    snapped={snapped}
    color={route.color}
    isNearest={snapped.stop_id === nearestStopId}
    onStopClick={handleStopClick}
  />
)
```

- [ ] **Step 6: Add user marker, LocationButton, and toast to JSX**

Inside `<LeafletMap>`, after `<MapFlyTo target={flyTarget} />`, add the user location marker:

```tsx
{userLocation && (
  <Marker
    position={[userLocation.lat, userLocation.lng]}
    icon={L.divIcon({
      className: '',
      html: `<div style="
        width:16px;height:16px;border-radius:50%;
        background:#2563EB;border:3px solid #fff;
        box-shadow:0 0 0 4px rgba(37,99,235,0.25);
      "></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    })}
    zIndexOffset={500}
  />
)}
```

Outside `<LeafletMap>` (after `<SearchButton ...>`), add:

```tsx
<LocationButton loading={geoLoading} onClick={handleLocation} />

{toastMsg && (
  <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1100] bg-gray-800 text-white text-sm px-4 py-2 rounded-full shadow-lg">
    {toastMsg}
  </div>
)}
```

- [ ] **Step 7: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 8: Build**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npm run build
```
Expected: exits 0.

- [ ] **Step 9: Manual smoke test**

1. Ensure backend is running: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` (from project root)
2. Open `http://localhost:8000`
3. Look for blue location pin button at **bottom-right** of map
4. Click it → browser asks for location permission
5. Allow → map flies to your location, blue dot appears
6. Nearest stop should appear **larger** with a permanent tooltip
7. Deny → toast "Konum izni verilmedi" appears for 3s then disappears
8. Spinner shows during GPS fetch

- [ ] **Step 10: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Map/MapContainer.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: geolocation — user marker, nearest stop highlight, toast"
```

---

## Post-Implementation

- [ ] **Push to remote**

```bash
git push origin clean-main:main
```
