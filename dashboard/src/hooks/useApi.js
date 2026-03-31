import { useState, useEffect, useCallback } from 'react'

const BASE = import.meta.env.VITE_API_URL || ''

export function useApi(path, refreshMs = 0) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}${path}`)
      if (!res.ok) throw new Error(res.statusText)
      setData(await res.json())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    fetch_()
    if (refreshMs > 0) {
      const id = setInterval(fetch_, refreshMs)
      return () => clearInterval(id)
    }
  }, [fetch_, refreshMs])

  return { data, loading, error, refetch: fetch_ }
}

export async function post(path, body = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}
