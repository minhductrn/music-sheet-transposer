import type { HealthResponse } from '../types/health'
import type { InputQuality, RecognitionProfile, RecognitionResponse, RecognitionResult } from '../types/recognition'

/**
 * All backend HTTP calls are centralized here. Pages/components must not
 * construct backend URLs or call fetch() directly.
 *
 * The dev server proxies /api/* to the backend (see vite.config.ts), so a
 * relative path is used and no backend URL is built in the UI layer.
 */
const API_BASE_PATH = '/api/v1'

function decodeArtifact(data: string, type: string): Blob {
  const decoded = atob(data)
  const bytes = new Uint8Array(decoded.length)
  for (let index = 0; index < decoded.length; index++) bytes[index] = decoded.charCodeAt(index)
  return new Blob([bytes], { type })
}

export async function recognizeSheetMusic(
  file: File, profile: RecognitionProfile, inputQuality?: InputQuality,
): Promise<RecognitionResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('profile', profile)
  formData.append('response_format', 'json')
  if (inputQuality) formData.append('input_quality', inputQuality)
  const response = await fetch(`${API_BASE_PATH}/recognize`, {
    method: 'POST', body: formData,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string'
      ? error.detail : `Recognition failed (${response.status}).`)
  }
  const payload = await response.json() as RecognitionResponse
  return {
    provider: payload.provider, profile: payload.profile,
    review_required: payload.review_required, warnings: payload.warnings,
    diagnostics: payload.diagnostics,
    musicXml: decodeArtifact(payload.musicxml_base64, 'application/vnd.recordare.musicxml+xml'),
    omrArtifact: payload.omr_artifact
      ? decodeArtifact(payload.omr_artifact.data_base64, payload.omr_artifact.media_type) : null,
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_PATH}/health`)

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }

  return (await response.json()) as HealthResponse
}

export async function transposeMusicXml(
  file: File,
  semitones: number,
): Promise<Blob> {
  const formData = new FormData()

  formData.append('file', file)
  formData.append('semitones', semitones.toString())

  const response = await fetch(
    `${API_BASE_PATH}/transpose/musicxml`,
    {
      method: 'POST',
      body: formData,
    },
  )

  if (!response.ok) {
    throw new Error(
      `MusicXML transposition failed with status ${response.status}`,
    )
  }

  return response.blob()
}
