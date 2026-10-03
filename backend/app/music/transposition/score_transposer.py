from app.music.models.measure import Measure
from app.music.models.note import Note
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
            key_signature = (
                transpose_key_signature(
                    measure.key_signature,
                    semitones,
                )
                if measure.key_signature is not None
                else None
            )

            transposed_notes = [
                transpose_note(
                    note,
                    semitones,
                    key_signature,
                )
                for note in measure.notes
            ]

            note_index = 0
            transposed_events = []

            for event in measure.events:
                if isinstance(event, Note):
                    transposed_events.append(
                        transposed_notes[note_index]
                    )
                    note_index += 1
                else:
                    transposed_events.append(
                        event.model_copy(deep=True)
                    )

            measures.append(
                measure.model_copy(
                    update={
                        "notes": transposed_notes,
                        "events": transposed_events,
                        "key_signature": key_signature,
                    },
                    deep=True,
                )
            )

        parts.append(
            part.model_copy(
                update={
                    "measures": measures,
                },
                deep=True,
            )
        )

    return score.model_copy(
        update={
            "parts": parts,
        },
        deep=True,
    )