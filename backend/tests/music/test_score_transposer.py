from app.music.models.key_signature import KeyMode, KeySignature
from app.music.models.measure import Measure
from app.music.models.note import Note, NoteType
from app.music.models.pitch import Pitch, PitchStep
from app.music.models.score import Part, Score
from app.music.models.time_signature import TimeSignature
from app.music.transposition.score_transposer import transpose_score


def test_transpose_score_notes() -> None:
    score = Score(
        title="Test Score",
        parts=[
            Part(
                id="P1",
                name="Piano",
                measures=[
                    Measure(
                        number=1,
                        divisions=1,
                        key_signature=KeySignature(
                            fifths=0,
                            mode=KeyMode.MAJOR,
                        ),
                        time_signature=TimeSignature(
                            beats=4,
                            beat_type=4,
                        ),
                        notes=[
                            Note(
                                pitch=Pitch(
                                    step=PitchStep.C,
                                    octave=4,
                                ),
                                duration=1,
                                note_type=NoteType.QUARTER,
                            ),
                            Note(
                                pitch=Pitch(
                                    step=PitchStep.E,
                                    octave=4,
                                ),
                                duration=1,
                                note_type=NoteType.QUARTER,
                            ),
                        ],
                    )
                ],
            )
        ],
    )

    result = transpose_score(score, 2)

    first_note = result.parts[0].measures[0].notes[0]
    second_note = result.parts[0].measures[0].notes[1]

    assert first_note.pitch is not None
    assert first_note.pitch.step == PitchStep.D
    assert first_note.pitch.octave == 4

    assert second_note.pitch is not None
    assert second_note.pitch.step == PitchStep.F
    assert second_note.pitch.alter == 1.0
    assert second_note.pitch.octave == 4


def test_transpose_score_preserves_measure_metadata() -> None:
    score = Score(
        title="Test Score",
        parts=[
            Part(
                id="P1",
                name="Piano",
                measures=[
                    Measure(
                        number=3,
                        divisions=4,
                        key_signature=KeySignature(
                            fifths=-5,
                            mode=KeyMode.MINOR,
                        ),
                        time_signature=TimeSignature(
                            beats=3,
                            beat_type=4,
                        ),
                        notes=[
                            Note(
                                pitch=Pitch(
                                    step=PitchStep.G,
                                    octave=3,
                                ),
                                duration=4,
                                note_type=NoteType.WHOLE,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    result = transpose_score(score, 2)

    measure = result.parts[0].measures[0]

    assert measure.number == 3
    assert measure.divisions == 4
    assert measure.key_signature is not None
    assert measure.key_signature.fifths == -3
    assert measure.key_signature.mode == KeyMode.MINOR
    assert measure.time_signature == TimeSignature(
        beats=3,
        beat_type=4,
    )


def test_transpose_score_does_not_mutate_original() -> None:
    score = Score(
        parts=[
            Part(
                id="P1",
                name="Piano",
                measures=[
                    Measure(
                        number=1,
                        notes=[
                            Note(
                                pitch=Pitch(
                                    step=PitchStep.C,
                                    octave=4,
                                ),
                                duration=1,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    result = transpose_score(score, 2)

    original_pitch = score.parts[0].measures[0].notes[0].pitch
    result_pitch = result.parts[0].measures[0].notes[0].pitch

    assert original_pitch is not None
    assert original_pitch.step == PitchStep.C
    assert original_pitch.octave == 4

    assert result_pitch is not None
    assert result_pitch.step == PitchStep.D
    assert result_pitch.octave == 4