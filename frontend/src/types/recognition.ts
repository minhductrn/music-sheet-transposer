export type RecognitionProfile = 'VOCAL_SONG' | 'SATB' | 'PIANO' | 'GENERAL' | 'ORCHESTRAL'
export type InputQuality = 'Synthetic' | 'Standard' | 'Poor'

export interface RecognitionIssue {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error'
  part_id: string | null
  measure: string | null
  details: Record<string, unknown>
}

export interface RecognitionResponse {
  musicxml_base64: string
  provider: string
  profile: RecognitionProfile
  review_required: boolean
  warnings: RecognitionIssue[]
  diagnostics: {
    counts: Record<string, number>
    voices: string[]
    issue_count: number
    artifact_retained: boolean
    provider_metadata: Record<string, unknown>
    validation_scope: string
  }
  omr_artifact: {
    filename: string
    media_type: string
    size_bytes: number
    sha256: string
    data_base64: string
  } | null
}

export interface RecognitionResult extends Omit<RecognitionResponse, 'musicxml_base64' | 'omr_artifact'> {
  musicXml: Blob
  omrArtifact: Blob | null
}
