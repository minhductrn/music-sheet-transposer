import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'

type ConnectionState = 'loading' | 'success' | 'error'

export default function Home() {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>('loading')
  const [statusText, setStatusText] = useState<string>('')

  useEffect(() => {
    let cancelled = false

    getHealth()
      .then((health) => {
        if (cancelled) return
        setStatusText(health.status)
        setConnectionState('success')
      })
      .catch(() => {
        if (cancelled) return
        setConnectionState('error')
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section>
      <p>
        Import, view, and transpose music sheets. This is the initial project
        foundation - core music features are not implemented yet.
      </p>

      <div className="status-card" role="status">
        <h2>Backend connection</h2>

        {connectionState === 'loading' && (
          <p>Checking backend connection…</p>
        )}

        {connectionState === 'success' && (
          <p className="status-success">
            Connected - backend status: {statusText}
          </p>
        )}

        {connectionState === 'error' && (
          <p className="status-error">
            Unable to reach the backend. Confirm the API is running.
          </p>
        )}
      </div>
    </section>
  )
}
