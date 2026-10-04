import type { HealthResponse } from '../types/health'
import type { InputQuality, RecognitionProfile, RecognitionResponse, RecognitionResult } from '../types/recognition'
import type { ReviewPayload, ReviewSession } from '../types/review'

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

async function checkResponse(response: Response): Promise<Response> {
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    const detail = typeof error?.detail === 'string' ? error.detail
      : Array.isArray(error?.detail) ? error.detail.map((issue: { msg: string }) => issue.msg).join('; ')
        : `Request failed (${response.status}).`
    throw new Error(detail)
  }
  return response
}

async function reviewResult(response: Response): Promise<ReviewSession> {
  await checkResponse(response)
  const { musicxml_base64: xml, ...payload } = await response.json() as ReviewPayload
  return { ...payload, musicXml: decodeArtifact(xml, 'application/vnd.recordare.musicxml+xml') }
}

export async function createReview(musicXml: Blob, source: File, omr?: Blob | null, analysisOmr?: Blob | null): Promise<ReviewSession> {
  const form = new FormData()
  form.append('musicxml', musicXml, 'recognized.musicxml')
  form.append('source', source)
  if (omr) form.append('omr', omr, 'recognized.omr')
  if (analysisOmr) form.append('analysis_omr', analysisOmr, 'semantic-evidence.omr')
  return reviewResult(await fetch(`${API_BASE_PATH}/reviews`, { method: 'POST', body: form }))
}

export async function getReview(id: string): Promise<ReviewSession> {
  return reviewResult(await fetch(`${API_BASE_PATH}/reviews/${encodeURIComponent(id)}`))
}

export async function changeReview(
  review: ReviewSession, path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown,
): Promise<ReviewSession> {
  return reviewResult(await fetch(`${API_BASE_PATH}/reviews/${encodeURIComponent(review.id)}/${path}`, {
    method, headers: { 'Content-Type': 'application/json', 'If-Match': `"${review.revision}"` },
    body: body === undefined ? undefined : JSON.stringify(body),
  }))
}

export async function closeReview(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_PATH}/reviews/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (response.status !== 404) await checkResponse(response) // Expired sessions are already released.
}

export async function getReviewSource(id: string, signal?: AbortSignal): Promise<Blob> {
  return (await checkResponse(await fetch(`${API_BASE_PATH}/reviews/${encodeURIComponent(id)}/source`, { signal }))).blob()
}

export async function getVerifiedMusicXml(id: string): Promise<Blob> {
  return (await checkResponse(await fetch(`${API_BASE_PATH}/reviews/${encodeURIComponent(id)}/musicxml?verified_only=true`))).blob()
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
    baselineMusicXml: payload.baseline_musicxml_base64
      ? decodeArtifact(payload.baseline_musicxml_base64, 'application/vnd.recordare.musicxml+xml') : null,
    omrArtifact: payload.omr_artifact
      ? decodeArtifact(payload.omr_artifact.data_base64, payload.omr_artifact.media_type) : null,
    semanticEvidenceArtifact: payload.semantic_evidence_artifact
      ? decodeArtifact(payload.semantic_evidence_artifact.data_base64, payload.semantic_evidence_artifact.media_type) : null,
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
