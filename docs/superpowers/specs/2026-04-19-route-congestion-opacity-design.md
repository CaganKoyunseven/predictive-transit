# Route Congestion Opacity — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Overview

Route polylines on the map change opacity based on real-time congestion: low delay + low occupancy → faint line; high delay or high occupancy → fully opaque line. Base colors stay identical.

## Architecture

Pure frontend, single file change. The existing `buses` state in `MapContainer` (polled every 30 s from `GET /api/bus-positions`) already contains `delay_min` and `occupancy_pct` per bus. These are aggregated by `line_id` to compute a per-line congestion score, which is mapped to Leaflet Polyline `opacity`.

**Modified files:**
- `frontend/src/components/Map/MapContainer.tsx` — add `lineOpacity` derived map, apply to Polyline `pathOptions`

**No new files. No backend changes.**

## Data Flow

1. `buses` state updates every 30 s (existing `setInterval`)
2. `useMemo` over `buses` → `lineOpacity: Map<string, number>` (line_id → opacity value)
3. For each route's `<Polyline>`, `opacity` reads from `lineOpacity.get(route.line_id)` with fallback
4. Active line always gets `opacity: 1.0` (existing behaviour preserved)

## Congestion Score Formula

```
avg_delay_min    = mean of delay_min for all buses on this line
avg_occupancy    = mean of occupancy_pct for all buses on this line

delay_norm    = clamp(avg_delay_min / 10, 0, 1)   // 10+ min → 1.0
occupancy_norm = clamp(avg_occupancy / 100, 0, 1)
score          = max(delay_norm, occupancy_norm)
opacity        = 0.3 + score * 0.7
```

| Condition | Score | Opacity |
|-----------|-------|---------|
| On time, empty | 0.0 | 0.30 |
| 5 min delay OR 50% full | 0.5 | 0.65 |
| 10+ min delay OR 100% full | 1.0 | 1.00 |
| No bus data yet | — | 0.65 (fallback) |
| Active (clicked) line | — | 1.00 (always) |

## MapContainer Change

```tsx
// Before (existing):
pathOptions={{
  color: route.color,
  opacity: isActive ? 1.0 : 0.65,
  weight: isActive ? 5 : 3,
}}

// After:
pathOptions={{
  color: route.color,
  opacity: isActive ? 1.0 : (lineOpacity.get(route.line_id) ?? 0.65),
  weight: isActive ? 5 : 3,
}}
```

`lineOpacity` is computed with `useMemo`:

```ts
const lineOpacity = useMemo(() => {
  const map = new Map<string, number>()
  const grouped = new Map<string, { delaySum: number; occSum: number; count: number }>()
  for (const bus of buses) {
    const g = grouped.get(bus.line_id) ?? { delaySum: 0, occSum: 0, count: 0 }
    g.delaySum += bus.delay_min
    g.occSum += bus.occupancy_pct
    g.count += 1
    grouped.set(bus.line_id, g)
  }
  for (const [lineId, g] of grouped) {
    const avgDelay = g.delaySum / g.count
    const avgOcc = g.occSum / g.count
    const delayNorm = Math.min(1, Math.max(0, avgDelay / 10))
    const occNorm = Math.min(1, Math.max(0, avgOcc / 100))
    const score = Math.max(delayNorm, occNorm)
    map.set(lineId, 0.3 + score * 0.7)
  }
  return map
}, [buses])
```

## Out of Scope
- Changing line weight based on congestion
- Color hue/saturation changes
- Legend or tooltip explaining opacity levels
- Persistent congestion history
