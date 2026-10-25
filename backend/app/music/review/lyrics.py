"""Preserve the existing contextual auxiliary-note lyric ownership policy."""
from .importer import rational


def auxiliary_lyric_owner(score, event):
    if (event.kind != "note" or event.display_size != "small" or event.grace or event.cue
            or not event.chord_member or not event.chord_id or event.staff != 1
            or event.lyric_ids or len(score.parts) != 1):
        return None
    measure = next((m for m in score.parts[0].measures
                    if any(e is event for v in m.voices for e in v.events)), None)
    if measure is None or measure.staves != 1 or measure.rhythm_status == "STRUCTURALLY_AMBIGUOUS":
        return None
    events = [e for v in measure.voices for e in v.events]
    chord = [e for e in events if e.chord_id == event.chord_id]
    owner = next((e for e in chord if e.id == event.chord_id), None)
    onset, duration = rational(event.onset), rational(event.duration)
    if (len(chord) != 2 or owner is None or owner is event or owner.chord_member
            or owner.kind != "note" or owner.display_size != "normal" or owner.grace or owner.cue
            or owner.staff != event.staff or owner.voice != event.voice
            or onset is None or onset < 0 or duration is None or duration <= 0
            or rational(owner.onset) != onset or rational(owner.duration) != duration or not owner.lyric_ids):
        return None
    for other in events:
        if other in chord or other.kind == "rest":
            continue
        start, length = rational(other.onset), rational(other.duration)
        if (start is None or length is None or start < onset + duration and start + length > onset
                or other.grace and onset <= start < onset + duration):
            return None
    return owner
