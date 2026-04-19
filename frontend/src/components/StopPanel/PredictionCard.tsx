import type { PredictResponse } from '../../hooks/usePrediction'
import type { Stop } from '../Map/BusStopMarker'
import CrowdBar from './CrowdBar'
import CrowdConfirmButtons from './CrowdConfirmButtons'
import AccessibilityAlert from '../Modals/AccessibilityAlert'

interface Props {
  stop: Stop
  prediction: PredictResponse
  userId: number
  onClose: () => void
  onTripComplete: () => void
  onBeatTheBus: () => void
}

const CONFIDENCE_BADGE: Record<string, string> = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-red-100 text-red-700',
}

export default function PredictionCard({
  stop,
  prediction,
  userId,
  onClose,
  onTripComplete,
  onBeatTheBus,
}: Props) {
  return (
    <div className="bg-white rounded-t-2xl shadow-xl p-4 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">{stop.line_id}</p>
            {stop.is_terminal && (
              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">Terminal</span>
            )}
          </div>
          <h2 className="font-semibold text-gray-800 text-base leading-tight">{stop.line_name}</h2>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-2xl font-bold text-blue-600">~{prediction.predicted_delay_min} min</span>
        <span className="text-sm text-gray-500">delay expected</span>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${CONFIDENCE_BADGE[prediction.confidence]}`}>
          {prediction.confidence} confidence
        </span>
      </div>

      <CrowdBar passengers={prediction.predicted_passengers_waiting} />

      {prediction.accessibility_warning && (
        <AccessibilityAlert onWaitNext={onClose} />
      )}

      <CrowdConfirmButtons userId={userId} stopId={stop.stop_id} />

      <div className="flex gap-2 pt-1">
        <button
          onClick={onBeatTheBus}
          className="flex-1 text-sm py-2 rounded-lg border border-green-500 text-green-600 font-medium hover:bg-green-50"
        >
          🚶 Beat the Bus
        </button>
        <button
          onClick={onTripComplete}
          className="flex-1 text-sm py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
        >
          Trip complete
        </button>
      </div>
    </div>
  )
}
