from app.music.models.key_signature import KeyMode, KeySignature
from app.music.transposition.key_signature_transposer import (
    transpose_key_signature,
)


def test_transpose_c_major_to_d_major() -> None:
    result = transpose_key_signature(
        KeySignature(fifths=0, mode=KeyMode.MAJOR),
        2,
    )

    assert result.fifths == 2
    assert result.mode == KeyMode.MAJOR


def test_transpose_b_flat_major_to_c_major() -> None:
    result = transpose_key_signature(
        KeySignature(fifths=-2, mode=KeyMode.MAJOR),
        2,
    )

    assert result.fifths == 0
    assert result.mode == KeyMode.MAJOR


def test_transpose_d_flat_major_to_e_flat_major() -> None:
    result = transpose_key_signature(
        KeySignature(fifths=-5, mode=KeyMode.MAJOR),
        2,
    )

    assert result.fifths == -3
    assert result.mode == KeyMode.MAJOR


def test_transpose_b_flat_minor_to_c_minor() -> None:
    result = transpose_key_signature(
        KeySignature(fifths=-5, mode=KeyMode.MINOR),
        2,
    )

    assert result.fifths == -3
    assert result.mode == KeyMode.MINOR


def test_transpose_a_minor_to_b_minor() -> None:
    result = transpose_key_signature(
        KeySignature(fifths=0, mode=KeyMode.MINOR),
        2,
    )

    assert result.fifths == 2
    assert result.mode == KeyMode.MINOR


def test_transpose_preserves_original() -> None:
    original = KeySignature(
        fifths=-5,
        mode=KeyMode.MAJOR,
    )

    result = transpose_key_signature(original, 2)

    assert original.fifths == -5
    assert original.mode == KeyMode.MAJOR

    assert result.fifths == -3
    assert result.mode == KeyMode.MAJOR