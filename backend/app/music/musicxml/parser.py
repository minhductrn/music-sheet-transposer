from pathlib import Path
import xml.etree.ElementTree as ET

from app.music.models.measure import Measure
from app.music.models.note import Note, NoteType
from app.music.models.pitch import Pitch, PitchStep
from app.music.models.score import Part, Score
from app.music.models.time_signature import TimeSignature


def parse_musicxml(path: Path) -> Score:
    tree = ET.parse(path)
    root = tree.getroot()

    title_element = root.find("./work/work-title")
    title = title_element.text if title_element is not None else None

    parts: list[Part] = []

    for part_element in root.findall("./part"):
        part_id = part_element.get("id", "")

        name_element = root.find(
            f"./part-list/score-part[@id='{part_id}']/part-name"
        )

        name = (
            name_element.text
            if name_element is not None and name_element.text
            else part_id
        )

        current_divisions: int | None = None
        current_time_signature: TimeSignature | None = None

        measures: list[Measure] = []

        for measure_element in part_element.findall("./measure"):
            number_text = measure_element.get("number", "1")
            number = int(number_text)

            measure_divisions: int | None = None
            measure_time_signature: TimeSignature | None = None

            attributes_element = measure_element.find("attributes")

            if attributes_element is not None:
                divisions_element = attributes_element.find("divisions")

                if (
                    divisions_element is not None
                    and divisions_element.text
                ):
                    current_divisions = int(divisions_element.text)
                    measure_divisions = current_divisions

                time_element = attributes_element.find("time")

                if time_element is not None:
                    beats_element = time_element.find("beats")
                    beat_type_element = time_element.find("beat-type")

                    if (
                        beats_element is not None
                        and beats_element.text
                        and beat_type_element is not None
                        and beat_type_element.text
                    ):
                        current_time_signature = TimeSignature(
                            beats=int(beats_element.text),
                            beat_type=int(beat_type_element.text),
                        )
                        measure_time_signature = current_time_signature

            notes: list[Note] = []

            for note_element in measure_element.findall("./note"):
                duration_element = note_element.find("duration")

                duration = (
                    int(duration_element.text)
                    if duration_element is not None
                    and duration_element.text
                    else 1
                )

                type_element = note_element.find("type")

                note_type = (
                    NoteType(type_element.text)
                    if type_element is not None and type_element.text
                    else None
                )

                rest_element = note_element.find("rest")

                if rest_element is not None:
                    notes.append(
                        Note(
                            duration=duration,
                            note_type=note_type,
                            is_rest=True,
                        )
                    )
                    continue

                pitch_element = note_element.find("pitch")

                if pitch_element is None:
                    continue

                step_element = pitch_element.find("step")
                octave_element = pitch_element.find("octave")
                alter_element = pitch_element.find("alter")

                if (
                    step_element is None
                    or not step_element.text
                    or octave_element is None
                    or not octave_element.text
                ):
                    continue

                alter = (
                    float(alter_element.text)
                    if alter_element is not None and alter_element.text
                    else 0.0
                )

                pitch = Pitch(
                    step=PitchStep(step_element.text),
                    octave=int(octave_element.text),
                    alter=alter,
                )

                notes.append(
                    Note(
                        pitch=pitch,
                        duration=duration,
                        note_type=note_type,
                    )
                )

            measures.append(
                Measure(
                    number=number,
                    divisions=measure_divisions,
                    time_signature=measure_time_signature,
                    notes=notes,
                )
            )

        parts.append(
            Part(
                id=part_id,
                name=name,
                measures=measures,
            )
        )

    return Score(
        title=title,
        parts=parts,
    )