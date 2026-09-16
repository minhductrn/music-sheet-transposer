from pathlib import Path
import xml.etree.ElementTree as ET

from app.music.models.score import Score


def export_musicxml(score: Score, path: Path) -> None:
    root = ET.Element("score-partwise", version="4.0")

    if score.title:
        work = ET.SubElement(root, "work")
        ET.SubElement(work, "work-title").text = score.title

    part_list = ET.SubElement(root, "part-list")

    for part in score.parts:
        score_part = ET.SubElement(part_list, "score-part", id=part.id)
        ET.SubElement(score_part, "part-name").text = part.name

    for part in score.parts:
        part_element = ET.SubElement(root, "part", id=part.id)

        for measure in part.measures:
            measure_element = ET.SubElement(
                part_element,
                "measure",
                number=str(measure.number),
            )

            if (
                measure.divisions is not None
                or measure.key_signature is not None
                or measure.time_signature is not None
            ):
                attributes = ET.SubElement(measure_element, "attributes")

                if measure.divisions is not None:
                    ET.SubElement(attributes, "divisions").text = str(
                        measure.divisions
                    )

                if measure.key_signature is not None:
                    key = ET.SubElement(attributes, "key")
                    ET.SubElement(key, "fifths").text = str(
                        measure.key_signature.fifths
                    )

                    if measure.key_signature.mode.value != "major":
                        ET.SubElement(key, "mode").text = (
                            measure.key_signature.mode.value
                        )

                if measure.time_signature is not None:
                    time = ET.SubElement(attributes, "time")
                    ET.SubElement(time, "beats").text = str(
                        measure.time_signature.beats
                    )
                    ET.SubElement(time, "beat-type").text = str(
                        measure.time_signature.beat_type
                    )

            for note in measure.notes:
                note_element = ET.SubElement(measure_element, "note")

                if note.is_rest:
                    ET.SubElement(note_element, "rest")
                elif note.pitch is not None:
                    pitch_element = ET.SubElement(note_element, "pitch")

                    ET.SubElement(
                        pitch_element,
                        "step",
                    ).text = note.pitch.step.value

                    if note.pitch.alter != 0:
                        ET.SubElement(
                            pitch_element,
                            "alter",
                        ).text = str(note.pitch.alter)

                    ET.SubElement(
                        pitch_element,
                        "octave",
                    ).text = str(note.pitch.octave)

                ET.SubElement(
                    note_element,
                    "duration",
                ).text = str(note.duration)

                if note.note_type is not None:
                    ET.SubElement(
                        note_element,
                        "type",
                    ).text = note.note_type.value

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(
        path,
        encoding="UTF-8",
        xml_declaration=True,
    )