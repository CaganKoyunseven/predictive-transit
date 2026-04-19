interface Props {
  onAnswer: (hasStroller: boolean) => void
}

export default function StrollerModal({ onAnswer }: Props) {
  return (
    <div className="fixed inset-0 bg-black/40 z-[1000] flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Do you have a stroller?</h2>
        <p className="text-sm text-gray-500 mb-6">
          Do you currently have a stroller with you? We'll warn you if the bus is too crowded.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => onAnswer(true)}
            className="flex-1 py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700"
          >
            Yes, I have it
          </button>
          <button
            onClick={() => onAnswer(false)}
            className="flex-1 py-2.5 rounded-xl border border-gray-300 text-gray-700 font-medium hover:bg-gray-50"
          >
            No
          </button>
        </div>
      </div>
    </div>
  )
}
