from pathlib import Path

from app.music.models.note import NoteType
from app.music.models.pitch import PitchStep
from app.music.musicxml.parser import parse_musicxml


FIXTURE = Path(__file__).parent / "fixtures" / "simple_score.musicxml"


def test_parse_simple_musicxml() -> None:
    score = parse_musicxml(FIXTURE)

    assert score.title == "Simple Test Score"
    assert len(score.parts) == 1

    part = score.parts[0]
    assert part.id == "P1"
    assert part.name == "Piano"

    assert len(part.measures) == 2

    assert part.measures[0].number == 1
    assert len(part.measures[0].notes) == 3

    assert part.measures[1].number == 2
    assert len(part.measures[1].notes) == 1


def test_parse_note_pitches() -> None:
    score = parse_musicxml(FIXTURE)

    measure_1_notes = score.parts[0].measures[0].notes
    measure_2_notes = score.parts[0].measures[1].notes

    assert measure_1_notes[0].pitch is not None
    assert measure_1_notes[0].pitch.step == PitchStep.C
    assert measure_1_notes[0].pitch.octave == 4

    assert measure_1_notes[1].pitch is not None
    assert measure_1_notes[1].pitch.step == PitchStep.D

    assert measure_1_notes[2].pitch is not None
    assert measure_1_notes[2].pitch.step == PitchStep.E

    assert measure_2_notes[0].pitch is not None
    assert measure_2_notes[0].pitch.step == PitchStep.F


def test_parse_note_durations() -> None:
    score = parse_musicxml(FIXTURE)

    measure_1_notes = score.parts[0].measures[0].notes
    measure_2_notes = score.parts[0].measures[1].notes

    assert [note.duration for note in measure_1_notes] == [1, 2, 1]
    assert [note.duration for note in measure_2_notes] == [4]


def test_parse_note_types() -> None:
    score = parse_musicxml(FIXTURE)

    measure_1_notes = score.parts[0].measures[0].notes
    measure_2_notes = score.parts[0].measures[1].notes

    assert [note.note_type for note in measure_1_notes] == [
        NoteType.QUARTER,
        NoteType.HALF,
        NoteType.QUARTER,
    ]

    assert [note.note_type for note in measure_2_notes] == [
        NoteType.WHOLE,
    ]


def test_parse_timing_information() -> None:
    score = parse_musicxml(FIXTURE)

    measure_1 = score.parts[0].measures[0]
    measure_2 = score.parts[0].measures[1]

    assert measure_1.divisions == 1
    assert measure_1.time_signature is not None
    assert measure_1.time_signature.beats == 4
    assert measure_1.time_signature.beat_type == 4

    assert measure_2.divisions is None
    assert measure_2.time_signature is None

def test_parse_key_signature_defaults_to_major() -> None:
    score = parse_musicxml(FIXTURE)

    key_signature = score.parts[0].measures[0].key_signature

    assert key_signature is not None
    assert key_signature.fifths == 0
    assert key_signature.mode.value == "major"


def test_parse_minor_key_signature() -> None:
    from app.music.models.key_signature import KeyMode

    fixture = Path(__file__).parent / "fixtures" / "minor_key.musicxml"

    score = parse_musicxml(fixture)

    key_signature = score.parts[0].measures[0].key_signature

    assert key_signature is not None
    assert key_signature.fifths == -5
    assert key_signature.mode == KeyMode.MINOR
