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
