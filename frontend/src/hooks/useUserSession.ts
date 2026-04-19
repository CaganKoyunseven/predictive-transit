import { useState } from 'react'
import { api } from '../api'

export interface SessionState {
  user_id: number
  stroller_active_until: string | null
  should_ask: boolean
  is_active: boolean
}

export function useUserSession() {
  const [session, setSession] = useState<SessionState | null>(null)

  async function fetchSession(userId: number) {
    const res = await api.get<SessionState>(`/users/${userId}/session`)
    setSession(res.data)
    return res.data
  }

  async function patchSession(userId: number, has_stroller_now: boolean) {
    const res = await api.patch<SessionState>(`/users/${userId}/session`, { has_stroller_now })
    setSession(res.data)
    return res.data
  }

  return { session, fetchSession, patchSession }
}
