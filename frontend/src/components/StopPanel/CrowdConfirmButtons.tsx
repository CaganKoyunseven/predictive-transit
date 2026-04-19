import { useState } from 'react'
import { useFeedback } from '../../hooks/useFeedback'

interface Props {
  userId: number
  stopId: string
}

type CrowdActual = 'empty' | 'as_predicted' | 'crowded'

const OPTIONS: { label: string; value: CrowdActual }[] = [
  { label: 'Correct', value: 'as_predicted' },
  { label: 'Less crowded', value: 'empty' },
  { label: 'Very crowded', value: 'crowded' },
]

export default function CrowdConfirmButtons({ userId, stopId }: Props) {
  const { confirmCrowd } = useFeedback()
  const [selected, setSelected] = useState<CrowdActual | null>(null)
  const [toast, setToast] = useState(false)

  async function handleClick(value: CrowdActual) {
    setSelected(value)
    try {
      await confirmCrowd({ user_id: userId, stop_id: stopId, crowd_actual: value })
      setToast(true)
      setTimeout(() => setToast(false), 2000)
    } catch {
      setSelected(null)
    }
  }

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">Is this accurate?</p>
      <div className="flex gap-2">
        {OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => handleClick(opt.value)}
            className={`flex-1 text-xs py-1.5 rounded border font-medium transition-colors
              ${selected === opt.value
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 text-gray-600 hover:border-gray-400'}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {toast && (
        <p className="text-xs text-green-600 mt-2 text-center">Thank you for your feedback</p>
      )}
    </div>
  )
}
