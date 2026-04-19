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

      const currentStopMatches = matchStops(q, stops)
      const combined = [...currentStopMatches, ...placeMatches].slice(0, 5)

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
