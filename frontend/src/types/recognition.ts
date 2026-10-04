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
  baseline_musicxml_base64?: string | null
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
  semantic_evidence_artifact?: RecognitionResponse['omr_artifact']
}

export interface RecognitionResult extends Omit<RecognitionResponse, 'musicxml_base64' | 'baseline_musicxml_base64' | 'omr_artifact' | 'semantic_evidence_artifact'> {
  musicXml: Blob
  baselineMusicXml: Blob | null
  omrArtifact: Blob | null
  semanticEvidenceArtifact: Blob | null
}
