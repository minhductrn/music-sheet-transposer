from pathlib import Path

from app.music.musicxml.parser import parse_musicxml
from app.music.models.pitch import PitchStep


FIXTURE = Path(__file__).parent / "fixtures" / "simple_score.musicxml"


def test_parse_simple_musicxml() -> None:
    score = parse_musicxml(FIXTURE)

    assert score.title == "Simple Test Score"
    assert len(score.parts) == 1

    part = score.parts[0]
    assert part.id == "P1"
    assert part.name == "Piano"

    assert len(part.measures) == 1

    measure = part.measures[0]
    assert measure.number == 1
    assert len(measure.notes) == 4


def test_parse_note_pitches() -> None:
    score = parse_musicxml(FIXTURE)

    notes = score.parts[0].measures[0].notes

    assert notes[0].pitch is not None
    assert notes[0].pitch.step == PitchStep.C
    assert notes[0].pitch.octave == 4

    assert notes[1].pitch is not None
    assert notes[1].pitch.step == PitchStep.D

    assert notes[2].pitch is not None
    assert notes[2].pitch.step == PitchStep.E

    assert notes[3].pitch is not None
    assert notes[3].pitch.step == PitchStep.F


def test_parse_note_durations() -> None:
    score = parse_musicxml(FIXTURE)

    notes = score.parts[0].measures[0].notes

    assert [note.duration for note in notes] == [1, 1, 1, 1]