from app.music.models.pitch import Pitch, PitchStep


STEP_TO_SEMITONE: dict[PitchStep, int] = {
    PitchStep.C: 0,
    PitchStep.D: 2,
    PitchStep.E: 4,
    PitchStep.F: 5,
    PitchStep.G: 7,
    PitchStep.A: 9,
    PitchStep.B: 11,
}


SEMITONE_TO_STEP: dict[int, tuple[PitchStep, float]] = {
    0: (PitchStep.C, 0.0),
    1: (PitchStep.C, 1.0),
    2: (PitchStep.D, 0.0),
    3: (PitchStep.D, 1.0),
    4: (PitchStep.E, 0.0),
    5: (PitchStep.F, 0.0),
    6: (PitchStep.F, 1.0),
    7: (PitchStep.G, 0.0),
    8: (PitchStep.G, 1.0),
    9: (PitchStep.A, 0.0),
    10: (PitchStep.A, 1.0),
    11: (PitchStep.B, 0.0),
}


def pitch_to_semitone(pitch: Pitch) -> int:
    return (
        (pitch.octave + 1) * 12
        + STEP_TO_SEMITONE[pitch.step]
        + int(pitch.alter)
    )


def semitone_to_pitch(semitone: int) -> Pitch:
    octave = (semitone // 12) - 1
    pitch_class = semitone % 12

    step, alter = SEMITONE_TO_STEP[pitch_class]

    return Pitch(
        step=step,
        octave=octave,
        alter=alter,
    )


def transpose_pitch(
    pitch: Pitch,
    semitones: int,
) -> Pitch:
    original_semitone = pitch_to_semitone(pitch)
    transposed_semitone = original_semitone + semitones

    return semitone_to_pitch(transposed_semitone)