from app.music.models.pitch import Pitch, PitchStep
from app.music.transposition.pitch_transposer import (
    pitch_to_semitone,
    semitone_to_pitch,
    transpose_pitch,
)


def test_pitch_to_semitone() -> None:
    pitch = Pitch(
        step=PitchStep.C,
        octave=4,
    )

    assert pitch_to_semitone(pitch) == 60


def test_semitone_to_pitch() -> None:
    pitch = semitone_to_pitch(60)

    assert pitch.step == PitchStep.C
    assert pitch.octave == 4
    assert pitch.alter == 0.0


def test_transpose_pitch_up() -> None:
    pitch = Pitch(
        step=PitchStep.C,
        octave=4,
    )

    result = transpose_pitch(
        pitch,
        2,
    )

    assert result.step == PitchStep.D
    assert result.octave == 4
    assert result.alter == 0.0


def test_transpose_pitch_down() -> None:
    pitch = Pitch(
        step=PitchStep.C,
        octave=4,
    )

    result = transpose_pitch(
        pitch,
        -1,
    )

    assert result.step == PitchStep.B
    assert result.octave == 3
    assert result.alter == 0.0


def test_transpose_pitch_across_octave() -> None:
    pitch = Pitch(
        step=PitchStep.B,
        octave=4,
    )

    result = transpose_pitch(
        pitch,
        1,
    )

    assert result.step == PitchStep.C
    assert result.octave == 5
    assert result.alter == 0.0


def test_transpose_sharp_pitch() -> None:
    pitch = Pitch(
        step=PitchStep.C,
        octave=4,
        alter=1.0,
    )

    result = transpose_pitch(
        pitch,
        1,
    )

    assert result.step == PitchStep.D
    assert result.octave == 4
    assert result.alter == 0.0