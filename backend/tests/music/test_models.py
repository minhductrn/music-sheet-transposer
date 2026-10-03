from app.music.models.measure import Measure
from app.music.models.timing import Backup, Forward
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

def test_key_signature_model() -> None:
    from app.music.models.key_signature import KeyMode, KeySignature

    major_key = KeySignature(
        fifths=-5,
        mode=KeyMode.MAJOR,
    )

    minor_key = KeySignature(
        fifths=-5,
        mode=KeyMode.MINOR,
    )

    assert major_key.fifths == -5
    assert major_key.mode == KeyMode.MAJOR

    assert minor_key.fifths == -5
    assert minor_key.mode == KeyMode.MINOR


def test_measure_with_clefs() -> None:
    from app.music.models.clef import Clef, ClefSign

    measure = Measure(
        number=1,
        clefs=[
            Clef(
                sign=ClefSign.G,
                line=2,
                staff=1,
            ),
            Clef(
                sign=ClefSign.F,
                line=4,
                staff=2,
            ),
        ],
    )

    assert len(measure.clefs) == 2

    assert measure.clefs[0].sign == ClefSign.G
    assert measure.clefs[0].line == 2
    assert measure.clefs[0].staff == 1

    assert measure.clefs[1].sign == ClefSign.F
    assert measure.clefs[1].line == 4
    assert measure.clefs[1].staff == 2

def test_note_staff_assignment() -> None:
    treble_note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
        staff=1,
    )

    bass_note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=3,
        ),
        duration=1,
        staff=2,
    )

    assert treble_note.staff == 1
    assert bass_note.staff == 2

def test_note_chord_assignment() -> None:
    chord_note = Note(
        pitch=Pitch(
            step=PitchStep.E,
            octave=4,
        ),
        duration=1,
        staff=1,
        is_chord=True,
    )

    assert chord_note.is_chord is True
    assert chord_note.staff == 1

def test_note_voice_assignment() -> None:
    note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
        voice="2",
    )

    assert note.voice == "2"

def test_measure_ordered_events() -> None:
    first_note = Note(
        pitch=Pitch(
            step=PitchStep.C,
            octave=4,
        ),
        duration=1,
        voice="1",
    )

    backup = Backup(duration=1)

    second_note = Note(
        pitch=Pitch(
            step=PitchStep.E,
            octave=4,
        ),
        duration=1,
        voice="2",
    )

    forward = Forward(duration=1)

    measure = Measure(
        number=1,
        notes=[
            first_note,
            second_note,
        ],
        events=[
            first_note,
            backup,
            second_note,
            forward,
        ],
    )

    assert len(measure.notes) == 2
    assert len(measure.events) == 4

    assert isinstance(measure.events[0], Note)
    assert isinstance(measure.events[1], Backup)
    assert isinstance(measure.events[2], Note)
    assert isinstance(measure.events[3], Forward)

    assert measure.events[0].voice == "1"
    assert measure.events[2].voice == "2"