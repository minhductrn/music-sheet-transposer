export type ReviewState = 'DRAFT' | 'REVIEW_REQUIRED' | 'VERIFIED'
export type DisplaySize = 'normal' | 'small' | 'cue'

export interface Pitch {
  step: string
  alter: string
  octave: number
}

export interface SemanticRecovery {
  state: 'AUTO_RECOVERED' | 'REVIEW_REQUIRED' | 'NO_RECOVERY'
  auto_recovered: number
  review_candidates: number
  diagnostics: string[]
  candidates: {
    id: string
    operation: string | null
    classification: 'GRACE' | 'CUE' | 'SIMULTANEOUS_VARIANT' | 'UNCERTAIN'
    confidence: 'EXACT' | 'HIGH' | 'AMBIGUOUS' | 'UNMATCHED'
    state: 'AUTO_RECOVERED' | 'REVIEW_REQUIRED' | 'NO_RECOVERY'
    measure_id: string | null
    event_id: string | null
    anchor_id: string | null
    pitch: Pitch | null
    diagnostics: string[]
    evidence: {
      id: string
      sheet: number
      staff_number: number | null
      bounds: [number, number, number, number] | null
      shape: string
      visual_size: string
    }
  }[]
}

export interface ScoreEvent {
  id: string
  kind: 'note' | 'rest' | 'unpitched'
  pitch: { step: string | null; alter: string; octave: number | null } | null
  onset: string | null
  duration: string | null
  duration_units: string | null
  divisions: string | null
  voice: string
  staff: number | null
  chord_id: string | null
  chord_member: boolean
  grace: boolean
  display_size: DisplaySize
  ties: string[]
  lyric_ids: string[]
}

export interface Measure {
  id: string
  number: string
  index: number
  divisions: string | null
  time_signature: { staff: string | null; pairs: { beats: string; beat_type: string }[] }[]
  key_signature: { staff: string | null; fifths: string | null; mode: string | null }[]
  staves: number
  expected_duration: string | null
  actual_duration: string | null
  validation_state: string
  voices: { id: string; events: ScoreEvent[] }[]
}

export interface Lyric {
  id: string
  event_id: string
  number: string
  text: string
  segments: string[]
  syllabic: string | null
}

export interface Harmony {
  id: string
  measure_id: string
  onset: string | null
  root_step: string | null
  root_alter: string | null
  kind: string | null
  text: string
}

export interface ReviewPayload {
  id: string
  revision: number
  state: ReviewState
  expires_at: number
  score: {
    metadata: { title: string; musicxml_version: string; credits: { id: string; text: string }[] }
    parts: { id: string; name: string; measures: Measure[] }[]
    lyrics: Lyric[]
    harmonies: Harmony[]
  }
  validation: {
    can_verify: boolean
    error_count: number
    warning_count: number
    truncated: boolean
    diagnostics: { code: string; message: string; severity: 'ERROR' | 'WARNING' | 'INFO'; measure_id: string | null; event_id: string | null }[]
  }
  can_undo: boolean
  can_redo: boolean
  source: { media_type: string; pages: number } | null
  semantic_recovery?: SemanticRecovery | null
  musicxml_base64: string
}

export interface ReviewSession extends Omit<ReviewPayload, 'musicxml_base64'> {
  musicXml: Blob
}

export interface EventPatch {
  pitch?: Pitch
  duration?: string
  voice?: string
  staff?: number
  display_size?: DisplaySize
  grace?: boolean
}

export interface EventAdd extends EventPatch {
  measure_id: string
  kind: 'note' | 'rest'
  after_event_id?: string
  before_event_id?: string
  chord_with_id?: string
}

export interface ScoreSelection {
  eventId: string
  measureIndex: number
  onset: string | null
  label: string
}
