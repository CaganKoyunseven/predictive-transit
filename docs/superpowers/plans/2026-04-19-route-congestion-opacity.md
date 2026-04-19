# Route Congestion Opacity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make route polylines on the map fade or darken based on per-line congestion, derived from the already-polled bus positions data.

**Architecture:** Single file change to `MapContainer.tsx`. A `useMemo` over the existing `buses` state computes a `Map<string, number>` of line_id → opacity. The Polyline `pathOptions.opacity` reads from this map instead of the hardcoded `0.65` fallback.

**Tech Stack:** React 19, TypeScript, Leaflet / react-leaflet

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/components/Map/MapContainer.tsx` | Add `useMemo` import, add `lineOpacity` computation, update Polyline `pathOptions` |

---

## Task 1: Add Congestion Opacity to Route Polylines

**Files:**
- Modify: `frontend/src/components/Map/MapContainer.tsx`

### Context

`MapContainer.tsx` is at `frontend/src/components/Map/MapContainer.tsx` in the project at `c:/Users/cagan/Desktop/predictive-transit`.

Current line 1:
```ts
import React, { useEffect, useRef, useState } from 'react'
```

Current Polyline block (inside the `routes.map(...)` call, around line 284–298):
```tsx
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
```

`buses` state is already declared and polled every 30 s. Each `BusPosition` has:
- `line_id: string`
- `delay_min: number`
- `occupancy_pct: number`

### Steps

- [ ] **Step 1: Add `useMemo` to the React import**

Change line 1 from:
```ts
import React, { useEffect, useRef, useState } from 'react'
```
to:
```ts
import React, { useEffect, useMemo, useRef, useState } from 'react'
```

- [ ] **Step 2: Add `lineOpacity` derivation inside `MapContainer` function**

After the `allStops` derivation line (which reads `const allStops: EnrichedStop[] = routes.flatMap(...)`), add:

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

- [ ] **Step 3: Update Polyline `pathOptions` to use `lineOpacity`**

Replace:
```tsx
pathOptions={{
  color: route.color,
  opacity: isActive ? 1.0 : 0.65,
  weight: isActive ? 5 : 3,
}}
```
with:
```tsx
pathOptions={{
  color: route.color,
  opacity: isActive ? 1.0 : (lineOpacity.get(route.line_id) ?? 0.65),
  weight: isActive ? 5 : 3,
}}
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

1. Start backend: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` (from project root)
2. Open `http://localhost:8000`
3. Observe the 5 route lines on the map — some should appear noticeably fainter than others (lines with lower delay + lower occupancy)
4. Verify the base colors (blue, green, orange, purple, red) are unchanged
5. Click a faint line → it should become fully opaque (opacity 1.0) as before
6. To verify values: `curl http://localhost:8000/api/bus-positions | python -m json.tool` — check `delay_min` and `occupancy_pct` per bus, confirm lines with higher values appear darker on map

- [ ] **Step 7: Commit**

```bash
cd c:/Users/cagan/Desktop/predictive-transit
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" add frontend/src/components/Map/MapContainer.tsx
git -c user.name="CaganKoyunseven" -c user.email="koyunsevencagan@gmail.com" commit -m "feat: route opacity varies with congestion (delay + occupancy)"
```

---

## Post-Implementation

- [ ] **Push to remote**

```bash
git push origin clean-main:main
```
