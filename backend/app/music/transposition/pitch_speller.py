from app.music.models.pitch import Pitch, PitchStep
from app.music.models.key_signature import KeySignature


SHARP_SPELLINGS: dict[int, tuple[PitchStep, float]] = {
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


FLAT_SPELLINGS: dict[int, tuple[PitchStep, float]] = {
    0: (PitchStep.C, 0.0),
    1: (PitchStep.D, -1.0),
    2: (PitchStep.D, 0.0),
    3: (PitchStep.E, -1.0),
    4: (PitchStep.E, 0.0),
    5: (PitchStep.F, 0.0),
    6: (PitchStep.G, -1.0),
    7: (PitchStep.G, 0.0),
    8: (PitchStep.A, -1.0),
    9: (PitchStep.A, 0.0),
    10: (PitchStep.B, -1.0),
    11: (PitchStep.B, 0.0),
}


def spell_pitch(
    semitone: int,
    prefer_flats: bool = False,
) -> Pitch:
    octave = (semitone // 12) - 1
    pitch_class = semitone % 12

    spellings = (
        FLAT_SPELLINGS
        if prefer_flats
        else SHARP_SPELLINGS
    )

    step, alter = spellings[pitch_class]

    return Pitch(
        step=step,
        octave=octave,
        alter=alter,
    )


def spell_pitch_for_key(
    semitone: int,
    key_signature: KeySignature,
) -> Pitch:
    return spell_pitch(
        semitone,
        prefer_flats=key_signature.fifths < 0,
    )