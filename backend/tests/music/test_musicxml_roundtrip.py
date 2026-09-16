from pathlib import Path

from app.music.musicxml.exporter import export_musicxml
from app.music.musicxml.parser import parse_musicxml

def test_minor_key_roundtrip(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "minor_key.musicxml"

    original = parse_musicxml(fixture)

    exported_path = tmp_path / "minor_key_roundtrip.musicxml"
    export_musicxml(original, exported_path)

    restored = parse_musicxml(exported_path)

    original_key = original.parts[0].measures[0].key_signature
    restored_key = restored.parts[0].measures[0].key_signature

    assert original_key is not None
    assert restored_key is not None

    assert restored_key.fifths == -5
    assert restored_key.mode == original_key.mode