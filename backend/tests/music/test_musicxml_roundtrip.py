from pathlib import Path
from app.music.models.note import Note
from app.music.models.timing import Backup, Forward
from app.music.musicxml.exporter import export_musicxml
from app.music.musicxml.parser import parse_musicxml


def test_minor_key_roundtrip(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "minor_key.musicxml"
    )

    original = parse_musicxml(fixture)

    exported_path = (
        tmp_path
        / "minor_key_roundtrip.musicxml"
    )

    export_musicxml(
        original,
        exported_path,
    )

    restored = parse_musicxml(exported_path)

    original_key = (
        original.parts[0]
        .measures[0]
        .key_signature
    )

    restored_key = (
        restored.parts[0]
        .measures[0]
        .key_signature
    )

    assert original_key is not None
    assert restored_key is not None

    assert restored_key.fifths == -5
    assert restored_key.mode == original_key.mode


def test_two_staff_piano_roundtrip(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "piano_two_staff.musicxml"
    )

    original = parse_musicxml(fixture)

    exported_path = (
        tmp_path
        / "piano_two_staff_roundtrip.musicxml"
    )

    export_musicxml(
        original,
        exported_path,
    )

    restored = parse_musicxml(exported_path)

    measure = restored.parts[0].measures[0]

    assert len(measure.clefs) == 2

    assert measure.clefs[0].sign.value == "G"
    assert measure.clefs[0].line == 2
    assert measure.clefs[0].staff == 1

    assert measure.clefs[1].sign.value == "F"
    assert measure.clefs[1].line == 4
    assert measure.clefs[1].staff == 2

    assert len(measure.notes) == 2

    assert measure.notes[0].staff == 1
    assert measure.notes[0].pitch is not None
    assert measure.notes[0].pitch.octave == 4

    assert measure.notes[1].staff == 2
    assert measure.notes[1].pitch is not None
    assert measure.notes[1].pitch.octave == 3


def test_chord_roundtrip(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "simple_chord.musicxml"
    )

    original = parse_musicxml(fixture)

    exported_path = (
        tmp_path
        / "simple_chord_roundtrip.musicxml"
    )

    export_musicxml(
        original,
        exported_path,
    )

    restored = parse_musicxml(exported_path)

    notes = restored.parts[0].measures[0].notes

    assert len(notes) == 3

    assert notes[0].is_chord is False
    assert notes[1].is_chord is True
    assert notes[2].is_chord is True

    assert notes[0].pitch is not None
    assert notes[1].pitch is not None
    assert notes[2].pitch is not None

    assert notes[0].pitch.step.value == "C"
    assert notes[1].pitch.step.value == "E"
    assert notes[2].pitch.step.value == "G"

def test_voice_roundtrip(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "simple_voices.musicxml"
    )

    original = parse_musicxml(fixture)

    exported_path = (
        tmp_path
        / "simple_voices_roundtrip.musicxml"
    )

    export_musicxml(
        original,
        exported_path,
    )

    restored = parse_musicxml(exported_path)

    notes = restored.parts[0].measures[0].notes

    assert len(notes) == 2

    assert notes[0].voice == "1"
    assert notes[1].voice == "2"

    assert notes[0].pitch is not None
    assert notes[1].pitch is not None

    assert notes[0].pitch.step.value == "C"
    assert notes[1].pitch.step.value == "E"

def test_timing_events_roundtrip(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "timing_events.musicxml"
    )

    original = parse_musicxml(fixture)

    exported_path = (
        tmp_path
        / "timing_events_roundtrip.musicxml"
    )

    export_musicxml(
        original,
        exported_path,
    )

    restored = parse_musicxml(exported_path)

    measure = restored.parts[0].measures[0]

    assert len(measure.notes) == 2
    assert len(measure.events) == 4

    assert isinstance(measure.events[0], Note)
    assert isinstance(measure.events[1], Backup)
    assert isinstance(measure.events[2], Note)
    assert isinstance(measure.events[3], Forward)

    assert measure.events[0].voice == "1"
    assert measure.events[1].duration == 1
    assert measure.events[2].voice == "2"
    assert measure.events[3].duration == 2