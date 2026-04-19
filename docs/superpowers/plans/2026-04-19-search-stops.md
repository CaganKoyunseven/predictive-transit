# Search Stops Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the search overlay so stop names are searchable directly (fly to + open panel), while place search keeps its existing navigation behavior — both in one search box.

**Architecture:** `usePlaceSearch` gains a `matchStops` function and returns `CombinedResult[]` (discriminated union of `StopResult | PlaceResult`). Stop matches are shown immediately (synchronous); place matches follow after the existing 300ms debounce. `SearchOverlay` renders two distinct row styles based on `result.type`. No backend changes.

**Tech Stack:** React 19, TypeScript

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/hooks/usePlaceSearch.ts` | Add `StopResult`, `PlaceResult`, `CombinedResult` types; `matchStops` function; combine results |
| Modify | `frontend/src/components/Search/SearchOverlay.tsx` | Render `StopResultRow` and `PlaceResultRow`; update imports; English place text |

---

## Task 1: Extend `usePlaceSearch`

**Files:**
- Modify: `frontend/src/hooks/usePlaceSearch.ts`

The file currently exports `EnrichedStop`, `SearchResult`, `haversineKm`, and `usePlaceSearch`. This task replaces `SearchResult` with `PlaceResult` + adds `StopResult` and `CombinedResult`, and adds `matchStops` logic.

**Current file location:** `frontend/src/hooks/usePlaceSearch.ts`

- [ ] **Step 1: Replace the entire file contents**

```ts
import { useState, useEffect, useRef } from 'react'
import { PLACES } from '../data/places'
import type { SnappedStop } from '../components/Map/MapContainer'

export interface EnrichedStop extends SnappedStop {
  color: string
}

export interface StopResult {
  type: 'stop'
  stop: EnrichedStop
}

export interface PlaceResult {
  type: 'place'
  place_name: string
  line_id: string
  line_name: string
  line_color: string
  stop_name: string
  stop: EnrichedStop
}

export type CombinedResult = StopResult | PlaceResult

const SIVAS_VIEWBOX = '36.8,39.6,37.2,39.85'
const MAX_DIST_KM = 2
const NOMINATIM_TIMEOUT_MS = 5000

export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
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

function matchStops(query: string, stops: EnrichedStop[]): StopResult[] {
  const q = query.toLowerCase().trim()
  const seen = new Set<string>()
  const results: StopResult[] = []
  for (const s of stops) {
    if (seen.has(s.stop_id)) continue
    if (s.name.toLowerCase().includes(q)) {
      seen.add(s.stop_id)
      results.push({ type: 'stop', stop: s })
      if (results.length === 3) break
    }
  }
  return results
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
  const [results, setResults] = useState<CombinedResult[]>([])
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

    const stopMatches = matchStops(q, stops)
    if (stopMatches.length > 0) {
      setResults(stopMatches)
      setError(null)
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      setError(null)

      const predefined = matchPredefined(q)
      const candidates = predefined.length > 0
        ? predefined
        : await nominatimSearch(q).then(r => (r ? [{ name: q, ...r }] : []))

      const seen = new Set<string>()
      const placeMatches: PlaceResult[] = []
      for (const c of candidates) {
        const s = nearestStop(c.lat, c.lng, stops)
        if (!s || seen.has(s.stop_id)) continue
        seen.add(s.stop_id)
        placeMatches.push({
          type: 'place',
          place_name: c.name,
          line_id: s.line_id,
          line_name: s.line_name,
          line_color: s.color,
          stop_name: s.name,
          stop: s,
        })
        if (placeMatches.length === 3) break
      }

      const combined = [...stopMatches, ...placeMatches].slice(0, 5)

      if (combined.length === 0) {
        setResults([])
        setError('Yer bulunamadı, haritadan durak seçebilirsiniz')
      } else {
        setResults(combined)
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

- [ ] **Step 2: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/hooks/usePlaceSearch.ts
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: usePlaceSearch returns CombinedResult with stop name matching"
```

---

## Task 2: Update `SearchOverlay`

**Files:**
- Modify: `frontend/src/components/Search/SearchOverlay.tsx`

This task updates the overlay to render two distinct row types and changes the place result text from Turkish to English.

**Current file location:** `frontend/src/components/Search/SearchOverlay.tsx`

- [ ] **Step 1: Replace the entire file contents**

```tsx
import { useEffect, useRef } from 'react'
import type { CombinedResult, StopResult, PlaceResult, EnrichedStop } from '../../hooks/usePlaceSearch'
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

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      setQuery('')
    }
  }, [open, setQuery])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (open) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="absolute inset-0 z-[1001] bg-black/40 flex items-start justify-center pt-16 px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
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

        <div className="max-h-56 overflow-y-auto">
          {loading && (
            <div className="px-4 py-3 text-sm text-gray-400">Aranıyor...</div>
          )}
          {!loading && error && (
            <div className="px-4 py-3 text-sm text-gray-500">{error}</div>
          )}
          {!loading && !error && results.map((r, i) =>
            r.type === 'stop'
              ? <StopResultRow key={i} result={r} onSelect={() => { onSelect(r.stop); onClose() }} />
              : <PlaceResultRow key={i} result={r} onSelect={() => { onSelect(r.stop); onClose() }} />
          )}
        </div>
      </div>
    </div>
  )
}

function StopResultRow({ result, onSelect }: { result: StopResult; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-50 last:border-0 flex items-center gap-3"
    >
      <span className="text-base shrink-0">📍</span>
      <span className="flex-1 text-sm font-medium text-gray-800">{result.stop.name}</span>
      <span
        className="shrink-0 text-xs font-bold text-white px-2 py-0.5 rounded"
        style={{ background: result.stop.color }}
      >
        {result.stop.line_id}
      </span>
    </button>
  )
}

function PlaceResultRow({ result, onSelect }: { result: PlaceResult; onSelect: () => void }) {
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
        <span className="font-medium">Take line {result.line_id}</span>
        <span className="text-gray-400 mx-1">·</span>
        <span className="text-gray-600">get off at {result.stop_name}</span>
      </span>
    </button>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Build**

```bash
cd c:/Users/cagan/Desktop/predictive-transit/frontend && npm run build
```
Expected: exits 0.

- [ ] **Step 4: Manual smoke test**

1. Start backend: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` (from project root)
2. Open `http://localhost:8000`, click the search button (top-right)
3. Type `"Durak"` or `"Hastane"` → stop results appear instantly with 📍 icon, stop name, line badge
4. Type `"Üniversite"` → place result appears: `Take line X · get off at Y`
5. Click a stop result → map flies to stop, prediction panel opens
6. Click a place result → same behavior
7. Type something with no matches → error message shown

- [ ] **Step 5: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Search/SearchOverlay.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: SearchOverlay renders stop and place result rows"
```

---

## Post-Implementation

- [ ] **Push to remote**

```bash
git push origin clean-main:main
```
