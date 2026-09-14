import type { HealthResponse } from '../types/health'

/**
 * All backend HTTP calls are centralized here. Pages/components must not
 * construct backend URLs or call fetch() directly.
 *
 * The dev server proxies /api/* to the backend (see vite.config.ts), so a
 * relative path is used and no backend URL is built in the UI layer.
 */
const API_BASE_PATH = '/api/v1'

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_PATH}/health`)

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }

  return (await response.json()) as HealthResponse
}
