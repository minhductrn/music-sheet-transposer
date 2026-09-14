from app.music.models.measure import Measure
from app.music.models.note import Note
from app.music.models.pitch import Pitch, PitchStep
from app.music.models.score import Part, Score


def test_pitch_model() -> None:
    pitch = Pitch(step=PitchStep.C, octave=4)

    assert pitch.step == PitchStep.C
    assert pitch.octave == 4
    assert pitch.alter == 0.0


def test_note_model() -> None:
    note = Note(
        pitch=Pitch(step=PitchStep.D, octave=4, alter=1),
        duration=2,
    )

    assert note.pitch is not None
    assert note.pitch.step == PitchStep.D
    assert note.pitch.alter == 1
    assert note.duration == 2
    assert note.is_rest is False


def test_rest_note() -> None:
    note = Note(duration=4, is_rest=True)

    assert note.pitch is None
    assert note.is_rest is True


def test_score_hierarchy() -> None:
    score = Score(
        title="Test Score",
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

    assert score.title == "Test Score"
    assert len(score.parts) == 1
    assert score.parts[0].name == "Piano"
    assert len(score.parts[0].measures) == 1
    assert len(score.parts[0].measures[0].notes) == 1