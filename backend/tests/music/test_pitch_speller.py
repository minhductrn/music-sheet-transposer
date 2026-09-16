from app.music.models.pitch import PitchStep
from app.music.transposition.pitch_speller import spell_pitch


def test_spell_c_sharp() -> None:
    pitch = spell_pitch(
        61,
        prefer_flats=False,
    )

    assert pitch.step == PitchStep.C
    assert pitch.alter == 1.0
    assert pitch.octave == 4


def test_spell_d_flat() -> None:
    pitch = spell_pitch(
        61,
        prefer_flats=True,
    )

    assert pitch.step == PitchStep.D
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_d_sharp() -> None:
    pitch = spell_pitch(
        63,
        prefer_flats=False,
    )

    assert pitch.step == PitchStep.D
    assert pitch.alter == 1.0
    assert pitch.octave == 4


def test_spell_e_flat() -> None:
    pitch = spell_pitch(
        63,
        prefer_flats=True,
    )

    assert pitch.step == PitchStep.E
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_f_sharp() -> None:
    pitch = spell_pitch(
        66,
        prefer_flats=False,
    )

    assert pitch.step == PitchStep.F
    assert pitch.alter == 1.0
    assert pitch.octave == 4


def test_spell_g_flat() -> None:
    pitch = spell_pitch(
        66,
        prefer_flats=True,
    )

    assert pitch.step == PitchStep.G
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_a_flat() -> None:
    pitch = spell_pitch(
        68,
        prefer_flats=True,
    )

    assert pitch.step == PitchStep.A
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_b_flat() -> None:
    pitch = spell_pitch(
        70,
        prefer_flats=True,
    )

    assert pitch.step == PitchStep.B
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_pitch_for_flat_key() -> None:
    from app.music.models.key_signature import KeyMode, KeySignature
    from app.music.transposition.pitch_speller import spell_pitch_for_key

    key_signature = KeySignature(
        fifths=-3,
        mode=KeyMode.MAJOR,
    )

    pitch = spell_pitch_for_key(
        63,
        key_signature,
    )

    assert pitch.step == PitchStep.E
    assert pitch.alter == -1.0
    assert pitch.octave == 4


def test_spell_pitch_for_sharp_key() -> None:
    from app.music.models.key_signature import KeyMode, KeySignature
    from app.music.transposition.pitch_speller import spell_pitch_for_key

    key_signature = KeySignature(
        fifths=3,
        mode=KeyMode.MAJOR,
    )

    pitch = spell_pitch_for_key(
        63,
        key_signature,
    )

    assert pitch.step == PitchStep.D
    assert pitch.alter == 1.0
    assert pitch.octave == 4