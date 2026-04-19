import { useState } from 'react'
import MapContainer from '../components/Map/MapContainer'
import type { Stop } from '../components/Map/BusStopMarker'
import PredictionCard from '../components/StopPanel/PredictionCard'
import StrollerModal from '../components/Modals/StrollerModal'
import BeatTheBusModal from '../components/Modals/BeatTheBusModal'
import PostTripModal from '../components/Modals/PostTripModal'
import { usePrediction } from '../hooks/usePrediction'
import { useUserSession } from '../hooks/useUserSession'
import { useUser } from '../context/UserContext'

type Modal = 'stroller' | 'beat' | 'trip' | null

export default function MapPage() {
  const { userId, user } = useUser()
  const { loading, prediction, error, predict } = usePrediction()
  const { fetchSession, patchSession } = useUserSession()
  const [selectedStop, setSelectedStop] = useState<Stop | null>(null)
  const [modal, setModal] = useState<Modal>(null)
  const [panelOpen, setPanelOpen] = useState(false)

  async function handleStopSelect(stop: Stop) {
    setSelectedStop(stop)

    if (user?.has_stroller_profile && userId) {
      try {
        const s = await fetchSession(userId)
        if (s.should_ask) {
          setModal('stroller')
          return
        }
      } catch {
        // session check failed — proceed to prediction anyway
      }
    }

    openPrediction(stop)
  }

  async function openPrediction(stop: Stop) {
    setPanelOpen(true)
    await predict(stop)
  }

  async function handleStrollerAnswer(hasStroller: boolean) {
    if (userId) await patchSession(userId, hasStroller)
    setModal(null)
    if (selectedStop) await openPrediction(selectedStop)
  }

  function closePanel() {
    setPanelOpen(false)
    setSelectedStop(null)
  }

  const skeleton = (
    <div className="bg-white rounded-t-2xl shadow-xl p-4 flex flex-col gap-4 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-2/3" />
      <div className="h-8 bg-gray-200 rounded w-1/2" />
      <div className="h-3 bg-gray-200 rounded w-full" />
      <div className="h-3 bg-gray-200 rounded w-3/4" />
    </div>
  )

  return (
    <div className="relative h-full w-full">
      <MapContainer onStopSelect={handleStopSelect} />

      {panelOpen && (
        <div className="absolute bottom-0 left-0 right-0 z-[900] max-w-lg mx-auto">
          {loading && skeleton}
          {error && (
            <div className="bg-white rounded-t-2xl shadow-xl p-4 text-center text-red-500 text-sm">
              {error}
            </div>
          )}
          {prediction && selectedStop && userId && (
            <PredictionCard
              stop={selectedStop}
              prediction={prediction}
              userId={userId}
              onClose={closePanel}
              onTripComplete={() => setModal('trip')}
              onBeatTheBus={() => setModal('beat')}
            />
          )}
        </div>
      )}

      {modal === 'stroller' && (
        <StrollerModal onAnswer={handleStrollerAnswer} />
      )}
      {modal === 'beat' && selectedStop && (
        <BeatTheBusModal stop={selectedStop} onClose={() => setModal(null)} />
      )}
      {modal === 'trip' && selectedStop && userId && (
        <PostTripModal
          userId={userId}
          stopId={selectedStop.stop_id}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
