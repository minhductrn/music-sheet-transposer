from app.music.models.note import Note, NoteType
from app.music.models.pitch import Pitch, PitchStep
from app.music.transposition.note_transposer import transpose_note


def test_transpose_note_pitch() -> None:
    note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
        note_type=NoteType.QUARTER,
    )

    result = transpose_note(note, 2)

    assert result.pitch is not None
    assert result.pitch.step == PitchStep.D
    assert result.pitch.octave == 4


def test_transpose_note_preserves_duration_and_type() -> None:
    note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=2,
        note_type=NoteType.HALF,
    )

    result = transpose_note(note, 2)

    assert result.duration == 2
    assert result.note_type == NoteType.HALF


def test_transpose_rest() -> None:
    note = Note(
        duration=1,
        note_type=NoteType.QUARTER,
        is_rest=True,
    )

    result = transpose_note(note, 2)

    assert result.is_rest is True
    assert result.pitch is None
    assert result.duration == 1
    assert result.note_type == NoteType.QUARTER


def test_transpose_note_does_not_mutate_original() -> None:
    note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
        note_type=NoteType.QUARTER,
    )

    result = transpose_note(note, 2)

    assert note.pitch is not None
    assert note.pitch.step == PitchStep.C
    assert note.pitch.octave == 4

    assert result.pitch is not None
    assert result.pitch.step == PitchStep.D
    assert result.pitch.octave == 4