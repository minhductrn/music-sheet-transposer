from pathlib import Path

from app.music.musicxml.exporter import export_musicxml
from app.music.musicxml.parser import parse_musicxml


FIXTURE = Path(__file__).parent / "fixtures" / "simple_score.musicxml"


def test_musicxml_roundtrip(tmp_path: Path) -> None:
    original = parse_musicxml(FIXTURE)

    exported_path = tmp_path / "roundtrip.musicxml"
    export_musicxml(original, exported_path)

    restored = parse_musicxml(exported_path)

    assert restored.title == original.title
    assert len(restored.parts) == len(original.parts)

    original_part = original.parts[0]
    restored_part = restored.parts[0]

    assert restored_part.id == original_part.id
    assert restored_part.name == original_part.name
    assert len(restored_part.measures) == len(original_part.measures)

    for original_measure, restored_measure in zip(
        original_part.measures,
        restored_part.measures,
    ):
        assert restored_measure.number == original_measure.number
        assert restored_measure.divisions == original_measure.divisions
        assert (
            restored_measure.time_signature
            == original_measure.time_signature
        )

        assert len(restored_measure.notes) == len(
            original_measure.notes
        )

        for original_note, restored_note in zip(
            original_measure.notes,
            restored_measure.notes,
        ):
            assert restored_note.duration == original_note.duration
            assert restored_note.note_type == original_note.note_type
            assert restored_note.is_rest == original_note.is_rest

            assert restored_note.pitch is not None
            assert original_note.pitch is not None

            assert restored_note.pitch.step == original_note.pitch.step
            assert restored_note.pitch.octave == original_note.pitch.octave
            assert restored_note.pitch.alter == original_note.pitch.alter