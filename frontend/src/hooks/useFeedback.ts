import { api } from '../api'

export function useFeedback() {
  async function confirmCrowd(payload: {
    user_id: number
    stop_id: string
    trip_id?: string
    crowd_actual: 'empty' | 'as_predicted' | 'crowded'
  }) {
    await api.post('/feedback/live-crowd', payload)
  }

  async function postTrip(payload: {
    user_id: number
    stop_id?: string
    trip_id?: string
    rating: number
    is_on_time?: boolean
    comment?: string
  }) {
    await api.post('/feedback/post-trip', payload)
  }

  return { confirmCrowd, postTrip }
}
