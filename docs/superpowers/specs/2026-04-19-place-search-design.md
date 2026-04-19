# Place Search Feature — Design Spec

**Date:** 2026-04-19  
**Status:** Approved

## Overview

A destination search overlay that lets users type a place name (e.g. "Sivas Üniversitesi") and receive a minimal bus recommendation: which line to board and which stop to get off at. The result triggers the existing prediction panel for that stop.

## Architecture

Pure frontend implementation — no new backend endpoints. The stop list is already loaded in `MapContainer` state (`SnappedStop[]` from `/routes/all/shapes`). This data is passed as props to the search components, avoiding duplicate API calls.

**New files:**
- `frontend/src/data/places.ts` — predefined Sivas POIs (~15 entries)
- `frontend/src/hooks/usePlaceSearch.ts` — search logic, debounce, Nominatim fallback
- `frontend/src/components/Search/SearchButton.tsx` — map overlay trigger button
- `frontend/src/components/Search/SearchOverlay.tsx` — search UI card

**Modified files:**
- `frontend/src/components/Map/MapContainer.tsx` — mount SearchButton + SearchOverlay, pass stops

## Data Flow

1. User types in overlay input (debounced 300ms)
2. Query matched against `places.ts` (case-insensitive `includes`)
3. If no predefined match → Nominatim API called:
   - `https://nominatim.openstreetmap.org/search?q=<query>&countrycodes=tr&format=json&limit=1`
   - viewbox constrained to Sivas bounding box (~39.6–39.85 lat, 36.8–37.2 lng)
   - timeout: 5 seconds
4. Resulting coordinates → Haversine distance against all `SnappedStop[]`
5. Nearest stop selected → result: `{ line_id, line_name, stop_name, stop }`
6. If nearest stop > 2km away → "Bu konuma yakın hat bulunamadı" warning
7. User clicks result → overlay closes, map flies to stop, `onStopSelect(stop)` fires

## Components

### `places.ts`
```ts
export interface Place { name: string; lat: number; lng: number }
export const PLACES: Place[] = [
  { name: "Sivas Üniversitesi", lat: 39.748, lng: 36.978 },
  { name: "Devlet Hastanesi", lat: 39.748, lng: 37.014 },
  // ~15 entries total covering university campuses, hospitals, terminal, bazaar
]
```

### `usePlaceSearch(stops: SnappedStop[])`
Returns: `{ query, setQuery, results, loading, error }`

- `results`: array of `{ place_name, line_id, line_name, line_color, stop_name, stop: SnappedStop }` (max 3)
- Nominatim called only when predefined match count is 0
- Nominatim failure (timeout / network) → silently falls back to empty results, no crash

### `SearchButton`
- Positioned top-right on map using Leaflet custom control or absolute CSS
- Circular button, search icon (🔍 or lucide `Search`)
- Opens `SearchOverlay` on click

### `SearchOverlay`
- Semi-transparent backdrop covers map
- White card (centered, max-w-sm), contains:
  - Text input (autofocused)
  - Result rows: `"L01 hattına bin · Üniversite durağında in"`
  - Max 3 results shown
- Closes on: Escape key, backdrop click, result selection

## Error States

| Condition | Behaviour |
|-----------|-----------|
| Nominatim timeout (5s) | Show predefined results only; no error message |
| Nominatim 0 results | "Yer bulunamadı, haritadan durak seçebilirsiniz" |
| Nearest stop > 2km | "Bu konuma yakın hat bulunamadı" |
| Stops not yet loaded | Input disabled, placeholder "Harita yükleniyor..." |

## Out of Scope

- Multi-hop routing (transfer between lines)
- "From → To" journey planning
- Real-time arrival times in search results (available after stop selection via existing prediction panel)
