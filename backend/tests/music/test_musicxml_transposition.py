from pathlib import Path

from app.music.models.key_signature import KeyMode
from app.music.models.pitch import PitchStep
from app.music.musicxml.exporter import export_musicxml
from app.music.musicxml.parser import parse_musicxml
from app.music.transposition.score_transposer import transpose_score


FIXTURE = Path(__file__).parent / "fixtures" / "simple_score.musicxml"


def test_musicxml_transposition_end_to_end(tmp_path: Path) -> None:
    original = parse_musicxml(FIXTURE)

    transposed = transpose_score(
        original,
        2,
    )

    exported_path = tmp_path / "transposed.musicxml"
    export_musicxml(transposed, exported_path)

    restored = parse_musicxml(exported_path)

    measure = restored.parts[0].measures[0]

    assert measure.key_signature is not None
    assert measure.key_signature.fifths == 2
    assert measure.key_signature.mode == KeyMode.MAJOR

    first_note = measure.notes[0]

    assert first_note.pitch is not None
    assert first_note.pitch.step == PitchStep.D
    assert first_note.pitch.octave == 4
    assert first_note.duration == 1


def test_minor_flat_key_transposition_end_to_end(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "minor_key.musicxml"
    )

    original = parse_musicxml(fixture)

    transposed = transpose_score(
        original,
        2,
    )

    exported_path = tmp_path / "minor_transposed.musicxml"
    export_musicxml(transposed, exported_path)

    restored = parse_musicxml(exported_path)

    measure = restored.parts[0].measures[0]

    assert measure.key_signature is not None

    # Bb minor + 2 semitones = C minor
    assert measure.key_signature.fifths == -3
    assert measure.key_signature.mode == KeyMode.MINOR

    first_note = measure.notes[0]

    assert first_note.pitch is not None

    # G3 + 2 semitones = A3
    assert first_note.pitch.step == PitchStep.A
    assert first_note.pitch.octave == 3
    assert first_note.pitch.alter == 0.0

    assert first_note.duration == 4