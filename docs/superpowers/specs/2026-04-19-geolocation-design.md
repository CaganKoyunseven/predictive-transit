# Geolocation Feature — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Overview

A "Konumum" button on the map requests the user's GPS location. When granted, the map centers on the user, a blue dot marks their position, and the nearest bus stop is highlighted with a larger marker.

## Architecture

Pure frontend — no backend changes. `useGeolocation` hook wraps `navigator.geolocation.getCurrentPosition`. `haversineKm` is exported from `usePlaceSearch.ts` (already exists) and reused in `MapContainer` to find the nearest stop. `StopMarker` receives a `isNearest` prop to render the highlighted icon.

**New files:**
- `frontend/src/hooks/useGeolocation.ts` — getCurrentPosition wrapper
- `frontend/src/components/Map/LocationButton.tsx` — trigger button, bottom-right

**Modified files:**
- `frontend/src/hooks/usePlaceSearch.ts` — export `haversineKm`
- `frontend/src/components/Map/MapContainer.tsx` — mount LocationButton, user marker, nearestStopId state, pass `isNearest` to StopMarker

## Data Flow

1. User clicks LocationButton (bottom-right, 📍 icon)
2. `useGeolocation.getLocation()` calls `navigator.geolocation.getCurrentPosition`
3. On success: `userLocation: { lat, lng }` state set in MapContainer
4. `MapFlyTo` flies map to user location at zoom 16
5. Haversine over `allStops` → `nearestStopId` state set (only if nearest stop ≤ 2km)
6. User location rendered as blue `DivIcon` marker inside `LeafletMap`
7. `StopMarker` with `stop_id === nearestStopId` renders 2× larger icon with white ring + auto-open tooltip

## Components

### `useGeolocation`
```ts
export function useGeolocation() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function getLocation(): Promise<{ lat: number; lng: number }> { ... }
  // rejects with Turkish error message string on failure

  return { loading, error, getLocation }
}
```
- timeout: 10 000ms
- maximumAge: 0 (always fresh)
- On error code 1 (denied): "Konum izni verilmedi"
- On error code 3 / other: "Konum alınamadı, tekrar deneyin"

### `LocationButton`
- Absolute bottom-right: `bottom-20 right-3` (above Leaflet attribution)
- Circular, same style as SearchButton
- Shows spinner while `loading`, 📍 icon otherwise
- `z-[1000]`

### User Location Marker (inside MapContainer)
- Leaflet `DivIcon`: 16×16 blue filled circle (`#2563EB`), 3px white border, subtle pulse animation via CSS
- Rendered as `<Marker>` inside `LeafletMap` when `userLocation` is set
- No click handler

### Nearest Stop Highlight (StopMarker change)
- New prop: `isNearest: boolean`
- When true: icon size 20×20 (vs default 14×14), white ring (`border: 3px solid white`), `box-shadow` glow
- Tooltip rendered with `permanent={true}` so it stays open without hover

### `haversineKm` export
In `usePlaceSearch.ts`: change `function haversineKm(...)` → `export function haversineKm(...)`

## Error States

| Condition | Behaviour |
|-----------|-----------|
| Permission denied | Toast bottom-center, 3s: "Konum izni verilmedi" |
| Timeout / other error | Toast: "Konum alınamadı, tekrar deneyin" |
| Nearest stop > 2km | `nearestStopId` stays null — only blue dot shown |
| Stops not yet loaded | `userLocation` stored; nearest computed once `allStops` populates (useEffect dep on both) |

### Toast
Simple absolute div, bottom-center, `z-[1100]`, auto-dismisses after 3s. No external library needed.

## Out of Scope
- Continuous location tracking (`watchPosition`)
- Auto-requesting location on page load
- Distance label on the nearest stop marker
