# Search Stops Extension — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Overview

Extend the existing search overlay to match bus stop names directly. Searching "Terminal" or "Hastane" shows matching stops instantly at the top of results. Searching a place name (e.g. "Üniversite") still shows the navigation result. Both result types call the same `onSelect` callback — fly to stop + open prediction panel.

## Architecture

Two files modified, no new files, no backend changes.

- `frontend/src/hooks/usePlaceSearch.ts` — add `StopResult` type, combine stop matches + place matches into `CombinedResult[]`
- `frontend/src/components/Search/SearchOverlay.tsx` — render two distinct row styles; update place result text to English

## Types

```ts
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
```

The existing `SearchResult` interface is replaced by `PlaceResult` (same fields, adds `type: 'place'`).

## Data Flow

1. User types ≥ 2 characters
2. **Stop match (synchronous, no debounce):** filter `stops` where `stop.name.toLowerCase().includes(query)` → deduplicate by `stop_id` → take first 3 → wrap as `StopResult[]`
3. **Place match (existing, debounced 300ms):** predefined POIs + Nominatim → nearest stop → wrap as `PlaceResult[]`
4. Combined result: `[...stopMatches, ...placeMatches]`, capped at 5 total
5. `onSelect(result.stop)` called for both types → same MapContainer behavior (fly + open panel)

## Stop Match Deduplication

`allStops` contains one entry per stop-per-line (e.g. STP-001 appears for L01 and L02). Deduplicate by `stop_id`, keep first occurrence (which carries the first line's color).

## UI — Two Row Styles

### Stop result row
```
📍  Devlet Hastanesi         [L02]
```
- Pin emoji + stop name (left), line badge (right)
- No secondary text

### Place result row
```
[L02]  Take line 2 · get off at Devlet Hastanesi
```
- Line badge (left), English navigation text (right)
- Changed from Turkish ("hattına bin · durağında in") to English

Both rows call `onSelect(result.stop)` on click.

## Error / Edge States

| Condition | Behaviour |
|-----------|-----------|
| Query < 2 chars | Results cleared, no search |
| Stop match found, no place match | Show stop results only, no error |
| No stop match, no place match | Existing error: "Yer bulunamadı, haritadan durak seçebilirsiniz" |
| Stops not yet loaded | Input disabled, placeholder "Harita yükleniyor..." (unchanged) |

## `usePlaceSearch` Return Type Change

```ts
// Before
return { query, setQuery, results: SearchResult[], loading, error }

// After
return { query, setQuery, results: CombinedResult[], loading, error }
```

`SearchOverlay` uses `result.type` to decide which row component to render.

## Out of Scope
- Fuzzy / typo-tolerant stop name matching
- Showing multiple lines for the same stop
- Separate stop vs. place tabs
- Stop search without opening prediction panel
