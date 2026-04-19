# Place Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a search overlay to the map that lets users type a destination (e.g. "Sivas Üniversitesi") and get a minimal bus recommendation — which line to board and which stop to get off at.

**Architecture:** Pure frontend, no new backend endpoints. The stop list is already loaded in `MapContainer`'s `routes` state. A search icon (top-right of map) opens a fullscreen overlay with a text input; results are computed client-side using predefined POIs + Nominatim fallback + Haversine nearest-stop selection.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Leaflet / react-leaflet, Nominatim OpenStreetMap API (free, no key needed)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/data/places.ts` | ~15 hard-coded Sivas POIs |
| Create | `frontend/src/hooks/usePlaceSearch.ts` | debounce, predefined match, Nominatim fallback, Haversine nearest-stop |
| Create | `frontend/src/components/Search/SearchButton.tsx` | circular icon button, absolute top-right |
| Create | `frontend/src/components/Search/SearchOverlay.tsx` | backdrop + card + input + result rows |
| Modify | `frontend/src/components/Map/MapContainer.tsx` | export `SnappedStop`, add `MapFlyTo` child, wrap in div, mount search components |

---

## Task 1: Predefined POI Data

**Files:**
- Create: `frontend/src/data/places.ts`

- [ ] **Step 1: Create the file**

```ts
export interface Place {
  name: string
  lat: number
  lng: number
}

export const PLACES: Place[] = [
  { name: "Cumhuriyet Üniversitesi", lat: 39.748, lng: 36.978 },
  { name: "Sivas Üniversitesi",      lat: 39.748, lng: 36.978 },
  { name: "Üniversite Kampüsü",      lat: 39.615, lng: 37.063 },
  { name: "Üniversite Yurdu",        lat: 39.615, lng: 37.063 },
  { name: "Sivas Devlet Hastanesi",  lat: 39.757, lng: 36.977 },
  { name: "Numune Hastanesi",        lat: 39.789, lng: 37.067 },
  { name: "Sağlık Merkezi",          lat: 39.790, lng: 37.061 },
  { name: "Otogar",                  lat: 39.761, lng: 36.978 },
  { name: "Terminal",                lat: 39.623, lng: 37.095 },
  { name: "Tren Garı",               lat: 39.624, lng: 37.061 },
  { name: "Şehir Merkezi",           lat: 39.748, lng: 37.014 },
  { name: "Meydan",                  lat: 39.748, lng: 37.014 },
  { name: "Sanayi Çarşısı",          lat: 39.777, lng: 37.076 },
  { name: "Pazar Yeri",              lat: 39.799, lng: 37.051 },
  { name: "Bağlar",                  lat: 39.762, lng: 37.007 },
  { name: "Esentepe",                lat: 39.761, lng: 36.978 },
]
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/places.ts
git commit -m "feat: predefined Sivas POI list for place search"
```

---

## Task 2: `usePlaceSearch` Hook

**Files:**
- Create: `frontend/src/hooks/usePlaceSearch.ts`

This hook contains all search logic: predefined match → Nominatim fallback → Haversine nearest-stop.

- [ ] **Step 1: Export `SnappedStop` from `MapContainer.tsx`**

In `frontend/src/components/Map/MapContainer.tsx`, change line 12:

```ts
// before
interface SnappedStop {
```

```ts
// after
export interface SnappedStop {
```

- [ ] **Step 2: Create the hook file**

```ts
import { useState, useEffect, useRef } from 'react'
import { PLACES } from '../data/places'
import type { SnappedStop } from '../components/Map/MapContainer'

export interface EnrichedStop extends SnappedStop {
  color: string
}

export interface SearchResult {
  place_name: string
  line_id: string
  line_name: string
  line_color: string
  stop_name: string
  stop: EnrichedStop
}

const SIVAS_VIEWBOX = '36.8,39.6,37.2,39.85'  // lng_min,lat_min,lng_max,lat_max
const MAX_DIST_KM = 2
const NOMINATIM_TIMEOUT_MS = 5000

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function nearestStop(lat: number, lng: number, stops: EnrichedStop[]): EnrichedStop | null {
  let best: EnrichedStop | null = null
  let bestDist = Infinity
  for (const s of stops) {
    const d = haversineKm(lat, lng, s.lat, s.lng)
    if (d < bestDist) { bestDist = d; best = s }
  }
  return bestDist <= MAX_DIST_KM ? best : null
}

function matchPredefined(query: string): Array<{ name: string; lat: number; lng: number }> {
  const q = query.toLowerCase().trim()
  if (q.length < 2) return []
  return PLACES.filter(p => p.name.toLowerCase().includes(q)).slice(0, 3)
}

async function nominatimSearch(query: string): Promise<{ lat: number; lng: number } | null> {
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('q', `${query} Sivas`)
  url.searchParams.set('countrycodes', 'tr')
  url.searchParams.set('format', 'json')
  url.searchParams.set('limit', '1')
  url.searchParams.set('viewbox', SIVAS_VIEWBOX)
  url.searchParams.set('bounded', '0')

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), NOMINATIM_TIMEOUT_MS)
  try {
    const res = await fetch(url.toString(), {
      signal: controller.signal,
      headers: { 'Accept-Language': 'tr' },
    })
    const data = await res.json()
    if (!data.length) return null
    return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) }
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}

export function usePlaceSearch(stops: EnrichedStop[]) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    const q = query.trim()
    if (q.length < 2) {
      setResults([])
      setError(null)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      setError(null)

      // Step 1 — predefined match
      const predefined = matchPredefined(q)
      const candidates = predefined.length > 0
        ? predefined
        : await nominatimSearch(q).then(r => (r ? [{ name: q, ...r }] : []))

      if (candidates.length === 0) {
        setResults([])
        setError('Yer bulunamadı, haritadan durak seçebilirsiniz')
        setLoading(false)
        return
      }

      // Step 2 — nearest stop for each candidate (deduplicate by stop_id)
      const seen = new Set<string>()
      const found: SearchResult[] = []
      for (const c of candidates) {
        const s = nearestStop(c.lat, c.lng, stops)
        if (!s || seen.has(s.stop_id)) continue
        seen.add(s.stop_id)
        found.push({
          place_name: c.name,
          line_id: s.line_id,
          line_name: s.line_name,
          line_color: s.color,
          stop_name: s.name,
          stop: s,
        })
        if (found.length === 3) break
      }

      if (found.length === 0) {
        setResults([])
        setError('Bu konuma yakın hat bulunamadı')
      } else {
        setResults(found)
        setError(null)
      }
      setLoading(false)
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, stops])

  return { query, setQuery, results, loading, error }
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Map/MapContainer.tsx frontend/src/hooks/usePlaceSearch.ts
git commit -m "feat: usePlaceSearch hook — predefined match + Nominatim + Haversine"
```

---

## Task 3: `SearchButton` Component

**Files:**
- Create: `frontend/src/components/Search/SearchButton.tsx`

- [ ] **Step 1: Create the component**

```tsx
interface Props {
  onClick: () => void
}

export default function SearchButton({ onClick }: Props) {
  return (
    <button
      onClick={onClick}
      aria-label="Yer ara"
      className="
        absolute top-3 right-3 z-[1000]
        w-10 h-10 rounded-full bg-white shadow-md
        flex items-center justify-center
        hover:bg-gray-50 active:scale-95 transition-transform
        border border-gray-200
      "
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="11" cy="11" r="8" />
        <path strokeLinecap="round" d="M21 21l-4.35-4.35" />
      </svg>
    </button>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Search/SearchButton.tsx
git commit -m "feat: SearchButton component"
```

---

## Task 4: `SearchOverlay` Component

**Files:**
- Create: `frontend/src/components/Search/SearchOverlay.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useEffect, useRef } from 'react'
import type { EnrichedStop, SearchResult } from '../../hooks/usePlaceSearch'
import { usePlaceSearch } from '../../hooks/usePlaceSearch'

interface Props {
  open: boolean
  stops: EnrichedStop[]
  onClose: () => void
  onSelect: (stop: EnrichedStop) => void
}

export default function SearchOverlay({ open, stops, onClose, onSelect }: Props) {
  const { query, setQuery, results, loading, error } = usePlaceSearch(stops)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      setQuery('')
    }
  }, [open, setQuery])

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (open) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    // Backdrop
    <div
      className="absolute inset-0 z-[1001] bg-black/40 flex items-start justify-center pt-16 px-4"
      onClick={onClose}
    >
      {/* Card — stop propagation so clicks inside don't close */}
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Input row */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8" /><path strokeLinecap="round" d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={stops.length === 0 ? 'Harita yükleniyor...' : 'Nereye gidiyorsunuz?'}
            disabled={stops.length === 0}
            className="flex-1 outline-none text-sm text-gray-800 placeholder-gray-400 disabled:bg-transparent"
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
          )}
        </div>

        {/* Results */}
        <div className="max-h-56 overflow-y-auto">
          {loading && (
            <div className="px-4 py-3 text-sm text-gray-400">Aranıyor...</div>
          )}

          {!loading && error && (
            <div className="px-4 py-3 text-sm text-gray-500">{error}</div>
          )}

          {!loading && !error && results.map((r, i) => (
            <ResultRow key={i} result={r} onSelect={() => { onSelect(r.stop); onClose() }} />
          ))}
        </div>
      </div>
    </div>
  )
}

function ResultRow({ result, onSelect }: { result: SearchResult; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-50 last:border-0 flex items-center gap-3"
    >
      <span
        className="shrink-0 text-xs font-bold text-white px-2 py-0.5 rounded"
        style={{ background: result.line_color }}
      >
        {result.line_id}
      </span>
      <span className="text-sm text-gray-800 leading-snug">
        <span className="font-medium">{result.line_id} hattına bin</span>
        <span className="text-gray-400 mx-1">·</span>
        <span className="text-gray-600">{result.stop_name} durağında in</span>
      </span>
    </button>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Search/SearchOverlay.tsx
git commit -m "feat: SearchOverlay component with result rows"
```

---

## Task 5: Wire Into `MapContainer`

**Files:**
- Modify: `frontend/src/components/Map/MapContainer.tsx`

This task:
1. Wraps the return in a `relative` div (needed for absolute positioning of SearchButton)
2. Adds `MapFlyTo` child component inside `LeafletMap` for programmatic map pan
3. Builds `allStops: EnrichedStop[]` from `routes` state
4. Mounts `SearchButton` + `SearchOverlay`
5. Converts `EnrichedStop` → `Stop` when forwarding to `onStopSelect`

- [ ] **Step 1: Add imports at top of `MapContainer.tsx`**

Add after the existing imports:

```ts
import { useMap } from 'react-leaflet'
import SearchButton from '../Search/SearchButton'
import SearchOverlay from '../Search/SearchOverlay'
import type { EnrichedStop } from '../../hooks/usePlaceSearch'
```

Note: `import type { Stop } from './BusStopMarker'` is already on line 5 — do not add it again.

- [ ] **Step 2: Add `MapFlyTo` component (before the `export default` function)**

Insert this function after the `StopMarker` function definition (around line 138):

```tsx
function MapFlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo(target, 16, { duration: 1 })
  }, [target, map])
  return null
}
```

- [ ] **Step 3: Add state for search open + flyTo target**

Inside `export default function MapContainer`, add these two state lines after the existing `useState` calls:

```ts
const [searchOpen, setSearchOpen] = useState(false)
const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null)
```

- [ ] **Step 4: Build `allStops` derived value**

Add this after the `colorMap` block (after line ~155):

```ts
const allStops: EnrichedStop[] = routes.flatMap(route =>
  route.stops.map(s => ({ ...s, color: route.color }))
)
```

- [ ] **Step 5: Add `handleSearchSelect` function**

Add after `handleStopClick`:

```ts
function handleSearchSelect(enriched: EnrichedStop) {
  setFlyTarget([enriched.lat, enriched.lng])
  const stop: Stop = {
    stop_id: enriched.stop_id,
    line_id: enriched.line_id,
    line_name: enriched.line_name,
    stop_sequence: enriched.stop_sequence,
    latitude: enriched.lat,
    longitude: enriched.lng,
    stop_type: enriched.stop_type,
    is_terminal: enriched.is_terminal,
    is_transfer_hub: enriched.is_transfer_hub,
  }
  onStopSelect(stop)
}
```

- [ ] **Step 6: Wrap return in a div and mount search components**

Replace the existing `return (` block with:

```tsx
return (
  <div className="relative h-full w-full">
    <LeafletMap
      center={SIVAS_CENTER}
      zoom={13}
      className="h-full w-full"
      zoomControl={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {routes.map(route => {
        const isActive = activeLineId === route.line_id
        return (
          <Polyline
            key={route.line_id}
            positions={route.coordinates}
            pathOptions={{
              color: route.color,
              opacity: isActive ? 1.0 : 0.65,
              weight: isActive ? 5 : 3,
            }}
            eventHandlers={{ click: () => setActiveLineId(prev => prev === route.line_id ? null : route.line_id) }}
          />
        )
      })}

      {stopMarkers}

      {buses.map(bus => (
        <BusMarker key={bus.bus_id} bus={bus} />
      ))}

      <MapFlyTo target={flyTarget} />
    </LeafletMap>

    <SearchButton onClick={() => setSearchOpen(true)} />

    <SearchOverlay
      open={searchOpen}
      stops={allStops}
      onClose={() => setSearchOpen(false)}
      onSelect={handleSearchSelect}
    />
  </div>
)
```

- [ ] **Step 7: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 8: Build to catch any remaining errors**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 9: Manual smoke test**

1. Start backend: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` (from project root)
2. Open `http://localhost:8000` in browser
3. Look for the circular search button (🔍) top-right corner of the map
4. Click it — overlay should appear with "Nereye gidiyorsunuz?" placeholder
5. Type "üniversite" — should show result rows immediately (predefined match)
6. Click a result — overlay closes, map flies to that stop, prediction panel opens
7. Type "park" — tests Nominatim fallback (or shows "Yer bulunamadı")
8. Press Escape — overlay closes

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/Map/MapContainer.tsx
git commit -m "feat: wire place search into MapContainer — search button + overlay + fly-to"
```

---

## Post-Implementation

- [ ] **Push to remote**

```bash
git push origin clean-main:main
```
