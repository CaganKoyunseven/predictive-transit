import React, { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api'

interface User {
  id: number
  username: string
  email: string
  is_disabled: boolean
  has_stroller_profile: boolean
}

interface UserContextValue {
  userId: number | null
  user: User | null
  refreshUser: () => Promise<void>
  updateUser: (patch: Partial<Pick<User, 'username' | 'is_disabled' | 'has_stroller_profile'>>) => Promise<void>
  switchUser: (id: number, enteredUsername: string) => Promise<{ success: boolean; error?: 'mismatch' | 'not_found' }>
}

const UserContext = createContext<UserContextValue | null>(null)

function randomSuffix(len: number): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  return Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState<number | null>(null)
  const [user, setUser] = useState<User | null>(null)

  async function fetchUser(id: number): Promise<User> {
    const res = await api.get<User>(`/users/${id}`)
    return res.data
  }

  async function createUser(): Promise<User> {
    const suffix = randomSuffix(6)
    const username = `transit_${suffix}`
    const res = await api.post<User>('/users', {
      username,
      email: `${username}@local.dev`,
      password: 'local_pass',
    })
    return res.data
  }

  useEffect(() => {
    async function init() {
      const stored = localStorage.getItem('userId')
      let profile: User

      if (stored) {
        try {
          profile = await fetchUser(Number(stored))
        } catch {
          profile = await createUser()
        }
      } else {
        profile = await createUser()
      }

      localStorage.setItem('userId', String(profile.id))
      setUserId(profile.id)
      setUser(profile)
    }

    init()
  }, [])

  async function refreshUser() {
    if (!userId) return
    const profile = await fetchUser(userId)
    setUser(profile)
  }

  async function updateUser(patch: Partial<Pick<User, 'username' | 'is_disabled' | 'has_stroller_profile'>>) {
    if (!userId) return
    const res = await api.patch<User>(`/users/${userId}`, patch)
    setUser(res.data)
  }

  async function switchUser(id: number, enteredUsername: string): Promise<{ success: boolean; error?: 'mismatch' | 'not_found' }> {
    try {
      const profile = await fetchUser(id)
      if (profile.username !== enteredUsername) {
        return { success: false, error: 'mismatch' }
      }
      localStorage.setItem('userId', String(profile.id))
      setUserId(profile.id)
      setUser(profile)
      return { success: true }
    } catch {
      return { success: false, error: 'not_found' }
    }
  }

  return (
    <UserContext.Provider value={{ userId, user, refreshUser, updateUser, switchUser }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useUser must be used inside UserProvider')
  return ctx
}
