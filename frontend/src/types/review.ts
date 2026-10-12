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

export interface SourceLocation {
  page: number
  bounds: [number, number, number, number] | null
  width: number | null
  height: number | null
}


export interface ScoreLayout {
  mode: "SOURCE_REVIEW" | "RESPONSIVE"
  origin: string | null
  geometry_available: boolean
  systems: { id: string; part_id: string; measure_ids: string[]; explicit_break_measure_id: string; new_page: boolean }[]
}

export interface ScoreEvent {
  id: string
  kind: 'note' | 'rest' | 'unpitched'
  pitch: { step: string | null; alter: string; octave: number | null } | null
  onset: string | null
  duration: string | null
  measure_id?: string
  clef?: Record<string, unknown> | null
  accidental?: { text: string | null; attributes: Record<string, string> }
  notated_duration?: Record<string, unknown>
  duration_options?: string[]
  key_signature?: Measure['key_signature']
  duration_units: string | null
  divisions: string | null
  voice: string
  staff: number | null
  chord_id: string | null
  chord_member: boolean
  grace: boolean
  cue?: boolean
  display_size: DisplaySize
  tie_source_editable?: boolean
  tie_correction_error?: string | null
  tie_relationship?: { source_event_id: string; target_event_id: string; origin: string; source_visual_id?: string; target_visual_id?: string } | null
  tie_target_id?: string | null
  tie_direction?: 'up' | 'down' | null
  tie_direction_editable?: boolean
  tie_target_ids?: string[]
  ties: string[]
  lyric_ids: string[]
  provenance: { origin: string; layer?: "SOURCE_OBSERVATION" | "RECOGNITION_INTERPRETATION" | "USER_CORRECTION"; manual_fields: string[]; evidence_ids: string[] }
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
  rhythm_status?: "VALID" | "UNDERFILLED" | "OVERFILLED" | "STRUCTURALLY_AMBIGUOUS" | "PARTIAL"
  conflict_state?: string
  clefs?: Record<string, unknown>[]
  context_changes?: Record<string, unknown>[]
  barlines?: Record<string, unknown>[]
  partial?: { implicit: boolean; intent: string }
  meter_context?: Record<string, unknown>[]
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
    schema_version?: string
    pages?: Record<string, unknown>[]
    systems?: Record<string, unknown>[]
    layout?: ScoreLayout
    metadata: { title: string; musicxml_version: string; credits: { id: string; text: string }[] }
    parts: { id: string; name: string; measures: Measure[]; staffs?: { id: string; number: number }[] }[]
    lyrics: Lyric[]
    harmonies: Harmony[]
  }
  validation: {
    can_verify: boolean
    error_count: number
    warning_count: number
    truncated: boolean
    diagnostics: { category?: 'TECHNICAL_ERROR' | 'MUSIC_WARNING' | 'INFORMATION'; code: string; message: string; severity: 'ERROR' | 'WARNING' | 'INFO'; measure_id: string | null; event_id: string | null; id?: string; can_confirm_source?: boolean; source_confirmed?: boolean; blocking?: boolean; source_confirmation?: { status: string; note: string; revision: number } | null }[]
  }
  source_confirmations?: Record<string, unknown>[]
  can_undo: boolean
  can_redo: boolean
  source: { media_type: string; pages: number } | null
  source_evidence?: Record<string, unknown>[]
  semantic_recovery?: SemanticRecovery | null
  musicxml_base64: string
}

export interface ReviewSession extends Omit<ReviewPayload, 'musicxml_base64'> {
  musicXml: Blob
}

export interface EventPatch {
  written_accidental?: string
  tie_to_event_id?: string | null
  pitch?: Pitch
  duration?: string
  voice?: string
  staff?: number
  display_size?: DisplaySize
  grace?: boolean
}

export interface EventAdd extends EventPatch {
  onset?: string
  tie_to_event_id?: string
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

export interface MusicalPositionTarget { measureId: string; staff: number }

export interface MusicCheckResult {
  revision: number
  diagnostics: ReviewPayload['validation']['diagnostics']
  warning_count: number
  technical_error_count: number
  truncated: boolean
}
