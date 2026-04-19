import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Star } from 'lucide-react'
import { useFeedback } from '../../hooks/useFeedback'

interface Props {
  userId: number
  stopId: string
  onClose: () => void
}

interface FormValues {
  rating: number
  is_on_time: boolean | null
  comment: string
}

export default function PostTripModal({ userId, stopId, onClose }: Props) {
  const { postTrip } = useFeedback()
  const { register, handleSubmit, setValue, watch } = useForm<FormValues>({
    defaultValues: { rating: 0, is_on_time: null, comment: '' },
  })
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const rating = watch('rating')
  const isOnTime = watch('is_on_time')

  async function onSubmit(data: FormValues) {
    if (data.rating === 0) return
    setSubmitting(true)
    try {
      await postTrip({
        user_id: userId,
        stop_id: stopId,
        rating: data.rating,
        is_on_time: data.is_on_time ?? undefined,
        comment: data.comment || undefined,
      })
      setDone(true)
      setTimeout(onClose, 1500)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-[1000] flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-5 w-full max-w-sm flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">How was your trip?</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>

        {done ? (
          <p className="text-center text-green-600 font-medium py-4">Thanks for the review! ✓</p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-2 font-medium">Overall experience *</p>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setValue('rating', n)}
                    className="focus:outline-none"
                  >
                    <Star
                      size={28}
                      className={n <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}
                    />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2 font-medium">Was the bus on time?</p>
              <div className="flex gap-2">
                {([true, false] as const).map(val => (
                  <button
                    key={String(val)}
                    type="button"
                    onClick={() => setValue('is_on_time', val)}
                    className={`flex-1 py-1.5 rounded-lg text-sm border font-medium transition-colors
                      ${isOnTime === val
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-600 hover:border-gray-400'}`}
                  >
                    {val ? 'Yes' : 'No'}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2 font-medium">Comment (optional)</p>
              <textarea
                {...register('comment', { maxLength: 500 })}
                rows={3}
                placeholder="Anything to add?"
                className="w-full border border-gray-300 rounded-lg p-2 text-sm resize-none focus:outline-none focus:border-blue-400"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || rating === 0}
              className="w-full py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Sending…' : 'Submit'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
