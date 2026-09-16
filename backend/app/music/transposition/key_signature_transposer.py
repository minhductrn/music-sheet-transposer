from app.music.models.key_signature import KeyMode, KeySignature


MAJOR_FIFTHS_TO_SEMITONE: dict[int, int] = {
    -7: 11,  # Cb
    -6: 6,   # Gb
    -5: 1,   # Db
    -4: 8,   # Ab
    -3: 3,   # Eb
    -2: 10,  # Bb
    -1: 5,   # F
    0: 0,    # C
    1: 7,    # G
    2: 2,    # D
    3: 9,    # A
    4: 4,    # E
    5: 11,   # B
    6: 6,    # F#
    7: 1,    # C#
}


MINOR_FIFTHS_TO_SEMITONE: dict[int, int] = {
    -7: 8,   # Ab minor
    -6: 3,   # Eb minor
    -5: 10,  # Bb minor
    -4: 5,   # F minor
    -3: 0,   # C minor
    -2: 7,   # G minor
    -1: 2,   # D minor
    0: 9,    # A minor
    1: 4,    # E minor
    2: 11,   # B minor
    3: 6,    # F# minor
    4: 1,    # C# minor
    5: 8,    # G# minor
    6: 3,    # D# minor
    7: 10,   # A# minor
}


def _build_preferred_lookup(
    fifths_to_semitone: dict[int, int],
) -> dict[int, int]:
    lookup: dict[int, int] = {}

    for fifths in sorted(
        fifths_to_semitone,
        key=lambda value: (abs(value), value),
    ):
        semitone = fifths_to_semitone[fifths]
        lookup.setdefault(semitone, fifths)

    return lookup


MAJOR_SEMITONE_TO_FIFTHS = _build_preferred_lookup(
    MAJOR_FIFTHS_TO_SEMITONE
)

MINOR_SEMITONE_TO_FIFTHS = _build_preferred_lookup(
    MINOR_FIFTHS_TO_SEMITONE
)


def transpose_key_signature(
    key_signature: KeySignature,
    semitones: int,
) -> KeySignature:
    if key_signature.mode == KeyMode.MAJOR:
        fifths_to_semitone = MAJOR_FIFTHS_TO_SEMITONE
        semitone_to_fifths = MAJOR_SEMITONE_TO_FIFTHS
    else:
        fifths_to_semitone = MINOR_FIFTHS_TO_SEMITONE
        semitone_to_fifths = MINOR_SEMITONE_TO_FIFTHS

    original_semitone = fifths_to_semitone[key_signature.fifths]
    transposed_semitone = (original_semitone + semitones) % 12

    return KeySignature(
        fifths=semitone_to_fifths[transposed_semitone],
        mode=key_signature.mode,
    )