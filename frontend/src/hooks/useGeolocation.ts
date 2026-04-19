import { useState } from 'react'

export interface GeoLocation {
  lat: number
  lng: number
}

export function useGeolocation() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function getLocation(): Promise<GeoLocation> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        const msg = 'Konum alınamadı, tekrar deneyin'
        setError(msg)
        reject(msg)
        return
      }
      setLoading(true)
      setError(null)
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLoading(false)
          resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        },
        (err) => {
          setLoading(false)
          const msg = err.code === 1
            ? 'Konum izni verilmedi'
            : 'Konum alınamadı, tekrar deneyin'
          setError(msg)
          reject(msg)
        },
        { timeout: 10_000, maximumAge: 0 },
      )
    })
  }

  return { loading, error, getLocation }
}
