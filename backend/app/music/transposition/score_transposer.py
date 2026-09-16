from app.music.models.measure import Measure
from app.music.models.score import Part, Score
from app.music.transposition.key_signature_transposer import (
    transpose_key_signature,
)
from app.music.transposition.note_transposer import transpose_note


def transpose_score(
    score: Score,
    semitones: int,
) -> Score:
    parts: list[Part] = []

    for part in score.parts:
        measures: list[Measure] = []

        for measure in part.measures:
            notes = [
                transpose_note(note, semitones)
                for note in measure.notes
            ]

            key_signature = (
                transpose_key_signature(
                    measure.key_signature,
                    semitones,
                )
                if measure.key_signature is not None
                else None
            )

            measures.append(
                measure.model_copy(
                    update={
                        "notes": notes,
                        "key_signature": key_signature,
                    },
                    deep=True,
                )
            )

        parts.append(
            part.model_copy(
                update={"measures": measures},
                deep=True,
            )
        )

    return score.model_copy(
        update={"parts": parts},
        deep=True,
    )