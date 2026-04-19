import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props {
  onWaitNext: () => void
}

export default function AccessibilityAlert({ onWaitNext }: Props) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="border border-red-500 rounded-xl p-3 bg-red-50 flex flex-col gap-3">
      <div className="flex items-start gap-2">
        <AlertTriangle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-red-700 font-medium">
          This bus is very crowded — wheelchair/stroller space may be full.
        </p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={onWaitNext}
          className="flex-1 text-xs py-1.5 rounded-lg bg-red-500 text-white font-medium hover:bg-red-600"
        >
          Wait for next bus
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="flex-1 text-xs py-1.5 rounded-lg border border-red-300 text-red-600 font-medium hover:bg-red-100"
        >
          Continue anyway
        </button>
      </div>
    </div>
  )
}
