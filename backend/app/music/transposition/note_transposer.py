from app.music.models.note import Note
from app.music.transposition.pitch_transposer import transpose_pitch


def transpose_note(
    note: Note,
    semitones: int,
) -> Note:
    if note.is_rest or note.pitch is None:
        return note.model_copy(deep=True)

    return note.model_copy(
        update={
            "pitch": transpose_pitch(
                note.pitch,
                semitones,
            )
        },
        deep=True,
    )