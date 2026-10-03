"""Transpose partwise MusicXML without rebuilding its notation tree."""

from xml.dom import Node, minidom
from xml.parsers import expat

from app.music.models.key_signature import KeyMode, KeySignature
from app.music.transposition.key_signature_transposer import transpose_key_signature


class MusicXMLTranspositionError(ValueError):
    """The document cannot be transposed safely by this service."""


_STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ACCIDENTALS = {
    -2: "flat-flat", -1: "flat", 0: "natural", 1: "sharp", 2: "double-sharp",
}


def _children(element: minidom.Element, name: str) -> list[minidom.Element]:
    return [
        child for child in element.childNodes
        if child.nodeType == Node.ELEMENT_NODE
        and child.localName == name
        and child.namespaceURI == element.namespaceURI
    ]


def _child(element: minidom.Element, name: str) -> minidom.Element | None:
    return next(iter(_children(element, name)), None)


def _text(element: minidom.Element | None) -> str:
    if element is None:
        raise MusicXMLTranspositionError("Missing required MusicXML value.")
    return "".join(
        child.data for child in element.childNodes
        if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)
    ).strip()


def _set_text(element: minidom.Element, value: str | int) -> None:
    # Retain element attributes and comments, replacing only its scalar value.
    for child in list(element.childNodes):
        if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
            element.removeChild(child)
    element.appendChild(element.ownerDocument.createTextNode(str(value)))


def _spell(semitone: int, fifths: int) -> tuple[str, int, int]:
    """Prefer the destination key's diatonic spelling, then simple accidentals."""
    signature = dict.fromkeys(_STEPS, 0)
    order = "FCGDAEB" if fifths >= 0 else "BEADGCF"
    for step in order[:abs(fifths)]:
        signature[step] = 1 if fifths >= 0 else -1
    candidates = []
    for step, natural in _STEPS.items():
        for alter in range(-2, 3):
            if (natural + alter) % 12 == semitone % 12:
                octave = (semitone - natural - alter) // 12 - 1
                rank = (
                    abs(alter - signature[step]), abs(alter),
                    alter > 0 if fifths < 0 else alter < 0,
                )
                candidates.append((rank, step, alter, octave))
    _, step, alter, octave = min(candidates)
    return step, alter, octave


def _transpose_note(note: minidom.Element, semitones: int, fifths: int) -> None:
    if _child(note, "rest") is not None or _child(note, "unpitched") is not None:
        return
    pitch = _child(note, "pitch")
    if pitch is None:
        return
    step_element = _child(pitch, "step")
    octave_element = _child(pitch, "octave")
    alter_element = _child(pitch, "alter")
    alter = float(_text(alter_element)) if alter_element is not None else 0.0
    if not alter.is_integer():
        raise MusicXMLTranspositionError("Microtonal pitches are not supported.")
    original = (
        _STEPS[_text(step_element)] + int(alter)
        + (int(_text(octave_element)) + 1) * 12
    )
    step, alter, octave = _spell(original + semitones, fifths)
    _set_text(step_element, step)
    _set_text(octave_element, octave)
    if alter_element is not None:
        _set_text(alter_element, alter)
    elif alter:
        prefix = f"{pitch.prefix}:" if pitch.prefix else ""
        alter_element = pitch.ownerDocument.createElementNS(
            pitch.namespaceURI, prefix + "alter",
        )
        pitch.insertBefore(alter_element, octave_element)
        _set_text(alter_element, alter)
    accidental = _child(note, "accidental")
    if accidental is not None:
        _set_text(accidental, _ACCIDENTALS[alter])


def _transpose_key(key: minidom.Element, semitones: int) -> int:
    fifths = _child(key, "fifths")
    if fifths is None:
        raise MusicXMLTranspositionError(
            "Nontraditional key signatures are not supported."
        )
    mode_element = _child(key, "mode")
    mode = KeyMode(_text(mode_element)) if mode_element is not None else KeyMode.MAJOR
    destination = transpose_key_signature(
        KeySignature(fifths=int(_text(fifths)), mode=mode), semitones,
    )
    _set_text(fifths, destination.fifths)
    cancel = _child(key, "cancel")
    if cancel is not None:
        cancellation = transpose_key_signature(
            KeySignature(fifths=int(_text(cancel)), mode=mode), semitones,
        )
        _set_text(cancel, cancellation.fifths)
    return destination.fifths


def transpose_musicxml_document(contents: bytes, semitones: int) -> bytes:
    """Preserve XML nodes and ordering; change pitches, keys and printed accidentals.

    Zero transposition returns the validated original bytes, including formatting.
    Nonzero output retains the DOM, comments, processing instructions and doctype,
    but serialization may change quoting, encoding and empty-element formatting.
    """
    document = None
    try:
        # Expat does not fetch external DTDs. Refuse entity declarations before
        # constructing a DOM, avoiding expansion of uploaded internal entities.
        validator = expat.ParserCreate()

        def reject_entity(*args):
            raise MusicXMLTranspositionError("XML entity declarations are not supported.")

        validator.EntityDeclHandler = reject_entity
        validator.Parse(contents, True)
        document = minidom.parseString(contents)
        root = document.documentElement
        if root.localName != "score-partwise":
            raise MusicXMLTranspositionError("Expected a score-partwise MusicXML document.")
        if semitones == 0:
            return contents
        for part in _children(root, "part"):
            default_fifths = 0
            staff_keys: dict[str, int] = {}
            for measure in _children(part, "measure"):
                for event in measure.childNodes:
                    if (
                        event.nodeType != Node.ELEMENT_NODE
                        or event.namespaceURI != root.namespaceURI
                    ):
                        continue
                    if event.localName == "attributes":
                        for key in _children(event, "key"):
                            destination_fifths = _transpose_key(key, semitones)
                            if key.hasAttribute("number"):
                                staff_keys[key.getAttribute("number")] = destination_fifths
                            else:
                                default_fifths = destination_fifths
                                staff_keys.clear()
                    elif event.localName == "note":
                        staff = _child(event, "staff")
                        staff_number = _text(staff) if staff is not None else "1"
                        _transpose_note(
                            event, semitones,
                            staff_keys.get(staff_number, default_fifths),
                        )
        return document.toxml(encoding="utf-8")
    except MusicXMLTranspositionError:
        raise
    except (expat.ExpatError, ValueError, KeyError) as error:
        raise MusicXMLTranspositionError("Invalid or unsupported MusicXML musical values.") from error
    finally:
        if document is not None:
            document.unlink()
