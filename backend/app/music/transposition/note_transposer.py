from app.music.models.key_signature import KeySignature
from app.music.models.note import Note
from app.music.transposition.pitch_speller import spell_pitch_for_key
from app.music.transposition.pitch_transposer import (
    pitch_to_semitone,
    transpose_pitch,
)


def transpose_note(
    note: Note,
    semitones: int,
    key_signature: KeySignature | None = None,
) -> Note:
    if note.is_rest or note.pitch is None:
        return note.model_copy(deep=True)

    if key_signature is None:
        transposed_pitch = transpose_pitch(
            note.pitch,
            semitones,
        )
    else:
        transposed_semitone = (
            pitch_to_semitone(note.pitch)
            + semitones
        )

        transposed_pitch = spell_pitch_for_key(
            transposed_semitone,
            key_signature,
        )

    return note.model_copy(
        update={"pitch": transposed_pitch},
        deep=True,
    )