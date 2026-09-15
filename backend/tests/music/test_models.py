from app.music.models.measure import Measure
from app.music.models.note import Note
from app.music.models.pitch import Pitch, PitchStep
from app.music.models.score import Part, Score
from app.music.models.time_signature import TimeSignature


def test_pitch_model() -> None:
    pitch = Pitch(
        step=PitchStep.C,
        octave=4,
    )

    assert pitch.step == PitchStep.C
    assert pitch.octave == 4
    assert pitch.alter == 0.0


def test_note_model() -> None:
    note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
    )

    assert note.pitch is not None
    assert note.pitch.step == PitchStep.C
    assert note.duration == 1
    assert note.is_rest is False


def test_rest_note() -> None:
    note = Note(
        duration=1,
        is_rest=True,
    )

    assert note.pitch is None
    assert note.is_rest is True


def test_measure_model() -> None:
    measure = Measure(
        number=1,
        divisions=4,
        time_signature=TimeSignature(
            beats=4,
            beat_type=4,
        ),
    )

    assert measure.number == 1
    assert measure.divisions == 4
    assert measure.time_signature is not None
    assert measure.time_signature.beats == 4
    assert measure.time_signature.beat_type == 4
    assert measure.notes == []


def test_score_hierarchy() -> None:
    measure = Measure(
        number=1,
        divisions=4,
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
                duration=4,
            )
        ],
    )

    part = Part(
        id="P1",
        name="Piano",
        measures=[measure],
    )

    score = Score(
        title="Test Score",
        parts=[part],
    )

    assert score.title == "Test Score"
    assert len(score.parts) == 1

    assert score.parts[0].id == "P1"
    assert score.parts[0].name == "Piano"

    assert len(score.parts[0].measures) == 1

    assert score.parts[0].measures[0].divisions == 4
    assert score.parts[0].measures[0].time_signature is not None
    assert score.parts[0].measures[0].time_signature.beats == 4
    assert score.parts[0].measures[0].time_signature.beat_type == 4