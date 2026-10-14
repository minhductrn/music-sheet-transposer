"""Explicit concert-key intervals applied to a notation-preserving MusicXML DOM."""
from contextlib import contextmanager
from xml.dom import minidom
from xml.parsers import expat

from app.music.musicxml.transposer import (
    MusicXMLTranspositionError, _ACCIDENTALS, _STEPS,
    _child, _children, _set_text, _text,
)

LETTERS = "CDEFGAB"


@contextmanager
def _document(contents: bytes):
    document = None
    try:
        parser = expat.ParserCreate()

        def reject_entity(*args):
            raise MusicXMLTranspositionError("XML entity declarations are not supported.")

        parser.EntityDeclHandler = reject_entity
        parser.Parse(contents, True)
        document = minidom.parseString(contents)
        if document.documentElement.localName != "score-partwise":
            raise MusicXMLTranspositionError("Open a score-partwise Concert MusicXML file.")
        yield document
    except (expat.ExpatError, ValueError, KeyError, OverflowError) as error:
        if isinstance(error, MusicXMLTranspositionError):
            raise
        raise MusicXMLTranspositionError("Invalid or unsupported MusicXML musical values.") from error
    finally:
        if document is not None:
            document.unlink()


def _elements(document, name):
    return [e for e in document.getElementsByTagNameNS("*", name)
            if e.namespaceURI == document.documentElement.namespaceURI]


def _percussion_parts(document):
    result = set()
    for part in _elements(document, "score-part"):
        flags = [_child(m, "midi-unpitched") is not None
                 or any(_text(c) == "10" for c in _children(m, "midi-channel"))
                 for m in _children(part, "midi-instrument")]
        if any(flags):
            if not all(flags):
                raise MusicXMLTranspositionError("Mixed pitched and percussion instruments within one part cannot be transposed safely.")
            result.add(part.getAttribute("id"))
    return result


def _source(document):
    percussion = _percussion_parts(document)
    parts = [p for p in _children(document.documentElement, "part")
             if p.getAttribute("id") not in percussion]
    signatures = set()
    modes = set()
    keys = []
    for part in parts:
        measures = _children(part, "measure")
        initial = [k for a in _children(measures[0], "attributes")
                   for k in _children(a, "key")] if measures else []
        if not initial:
            raise MusicXMLTranspositionError("The source key is missing. Save a score with an explicit major or minor key first.")
        if all(k.hasAttribute("number") for k in initial):
            staffs = {_text(s) if s is not None else "1" for m in measures for n in _children(m, "note")
                      if _child(n, "pitch") is not None for s in [_child(n, "staff")]}
            if not staffs:
                staffs = {"1"}
            if not staffs <= {k.getAttribute("number") for k in initial}:
                raise MusicXMLTranspositionError("Each pitched staff needs an explicit source key.")
        for measure in measures:
            for attributes in _children(measure, "attributes"):
                for key in _children(attributes, "key"):
                    if _children(key, "key-octave"):
                        raise MusicXMLTranspositionError("Custom key-signature octave placement is not supported by Concert Transpose.")
                    mode = _child(key, "mode")
                    fifths = _child(key, "fifths")
                    if fifths is None or (mode is not None and _text(mode) not in ("major", "minor")):
                        raise MusicXMLTranspositionError("The source needs a traditional key signature; unsupported modes cannot be used for major/minor transposition.")
                    value = int(_text(fifths))
                    if not -7 <= value <= 7:
                        raise MusicXMLTranspositionError("Source keys beyond seven sharps or flats are not supported.")
                    signatures.add(value)
                    if mode is not None:
                        modes.add(_text(mode))
                    keys.append(key)
    if len(signatures) != 1 or len(modes) > 1:
        raise MusicXMLTranspositionError("Key changes or conflicting part/staff keys are not supported by Concert Transpose.")
    # This operation accepts concert-pitch scores only, not written instrument scores.
    for transposition in _elements(document, "transpose"):
        if _child(transposition, "double") is not None:
            raise MusicXMLTranspositionError("Octave-doubled instrument transposition is not supported by Concert Transpose.")
        for name in ("diatonic", "chromatic", "octave-change"):
            value = _child(transposition, name)
            if value is not None and float(_text(value)) != 0:
                raise MusicXMLTranspositionError("Open a concert-pitch score without instrument transposition metadata.")
    if _elements(document, "scordatura"):
        raise MusicXMLTranspositionError("Scordatura tuning is not supported by Concert Transpose.")
    if _elements(document, "accidental-mark"):
        raise MusicXMLTranspositionError("Explicit ornament accidentals cannot yet be transposed safely.")
    if any(e.hasAttribute("smufl") or e.hasAttribute("text")
           for name in ("accidental", "root-alter", "bass-alter") for e in _elements(document, name)):
        raise MusicXMLTranspositionError("Custom accidental display overrides cannot be transposed safely.")
    return (next(iter(signatures)), next(iter(modes), None)), parts, keys


def _check_integrity(contents):
    # Reuse Stage 1's technical diagnostics; musical/OMR warnings stay advisory.
    from app.music.review.document import Document, ReviewError
    from app.music.recovery.musicxml import XmlContext
    from app.music.review.music_check import category
    try:
        context = XmlContext(Document.parse(contents))
        errors = [issue.message for issue in context.diagnostics
                  if category(issue) == "TECHNICAL_ERROR"]
        if errors:
            raise MusicXMLTranspositionError("Repair the source MusicXML before transposing: " + "; ".join(errors))
    except ReviewError as error:
        raise MusicXMLTranspositionError(str(error)) from error


def concert_key_info(contents: bytes) -> dict:
    with _document(contents) as document:
        (fifths, mode), _, _ = _source(document)
        _check_integrity(contents)
        candidates = [{"fifths": fifths, "mode": candidate} for candidate in ("major", "minor")]
        return {"fifths": fifths, "mode": mode, "candidates": candidates,
                "suggested": {"fifths": fifths, "mode": mode} if mode else None}


def _interval(source: int, target: int, mode: str, direction: str):
    tonic = 0 if mode == "major" else 9
    letter = 0 if mode == "major" else 5
    source_pc, target_pc = (tonic + 7 * source) % 12, (tonic + 7 * target) % 12
    source_letter, target_letter = (letter + 4 * source) % 7, (letter + 4 * target) % 7
    chromatic = (target_pc - source_pc) % 12
    if chromatic and direction == "down":
        chromatic -= 12

    def tonic_alter(fifths, index):
        order = "FCGDAEB" if fifths >= 0 else "BEADGCF"
        return (1 if fifths >= 0 else -1) if LETTERS[index] in order[:abs(fifths)] else 0

    source_pitch = 48 + _STEPS[LETTERS[source_letter]] + tonic_alter(source, source_letter)
    target_natural = _STEPS[LETTERS[target_letter]] + tonic_alter(target, target_letter)
    target_octave = (source_pitch + chromatic - target_natural) // 12
    return chromatic, (target_octave - 4) * 7 + target_letter - source_letter


def _integer_alter(element):
    value = float(_text(element)) if element is not None else 0.0
    if not value.is_integer():
        raise MusicXMLTranspositionError("Microtonal pitches are not supported by Concert Transpose.")
    return int(value)


def _pitch(container, step_name, alter_name, chromatic, diatonic, octave_name=None):
    step = _child(container, step_name)
    if step is None or _text(step) not in LETTERS:
        raise MusicXMLTranspositionError("A pitched element has no supported note spelling.")
    if step.hasAttribute("text"):
        raise MusicXMLTranspositionError("Custom chord root/bass display text cannot be transposed safely.")
    alter = _child(container, alter_name)
    octave = _child(container, octave_name) if octave_name else None
    source_octave = int(_text(octave)) if octave_name else 4
    source_letter = LETTERS.index(_text(step))
    target_index = source_octave * 7 + source_letter + diatonic
    target_octave, target_letter = divmod(target_index, 7)
    target_step = LETTERS[target_letter]
    sounding = source_octave * 12 + _STEPS[_text(step)] + _integer_alter(alter) + chromatic
    target_alter = sounding - (target_octave * 12 + _STEPS[target_step])
    if target_alter not in _ACCIDENTALS:
        raise MusicXMLTranspositionError("This interval requires an accidental beyond a double sharp/flat; choose another target spelling.")
    _set_text(step, target_step)
    if octave is not None:
        if not 0 <= target_octave <= 9:
            raise MusicXMLTranspositionError("The resulting pitch is outside supported MusicXML octaves 0–9.")
        _set_text(octave, target_octave)
    if alter is not None:
        _set_text(alter, target_alter)
    elif target_alter:
        prefix = f"{container.prefix}:" if container.prefix else ""
        alter = container.ownerDocument.createElementNS(container.namespaceURI, prefix + alter_name)
        container.insertBefore(alter, step.nextSibling)
        _set_text(alter, target_alter)
    return target_alter


def transpose_concert_key(contents: bytes, target_fifths: int, direction: str, *,
                          source_fifths: int | None = None, source_mode: str | None = None) -> bytes:
    if not -7 <= target_fifths <= 7 or direction not in ("up", "down"):
        raise MusicXMLTranspositionError("Choose a supported target key and Up or Down interval.")
    with _document(contents) as document:
        (detected_fifths, declared_mode), parts, keys = _source(document)
        if source_fifths is not None and source_fifths != detected_fifths:
            raise MusicXMLTranspositionError("The confirmed Source Key is incompatible with the score's key signature. Choose a compatible major or minor key.")
        source_fifths = detected_fifths
        mode = source_mode if source_mode is not None else declared_mode
        if mode not in ("major", "minor"):
            raise MusicXMLTranspositionError("Select and confirm a major or minor Source Key before transposing; its mode will not be guessed.")
        _check_integrity(contents)
        if source_fifths == target_fifths and all(
                _child(key, "mode") is not None and _text(_child(key, "mode")) == mode for key in keys):
            return contents
        chromatic, diatonic = _interval(source_fifths, target_fifths, mode, direction)
        for key in keys:
            _set_text(_child(key, "fifths"), target_fifths)
            mode_element = _child(key, "mode")
            if mode_element is None:
                prefix = f"{key.prefix}:" if key.prefix else ""
                mode_element = document.createElementNS(key.namespaceURI, prefix + "mode")
                key.insertBefore(mode_element, _child(key, "fifths").nextSibling)
            _set_text(mode_element, mode)
            cancel = _child(key, "cancel")
            if cancel is not None:
                value = int(_text(cancel)) + target_fifths - source_fifths
                if not -7 <= value <= 7:
                    raise MusicXMLTranspositionError("The transposed key cancellation cannot be represented safely.")
                _set_text(cancel, value)
        for part in (parts if source_fifths != target_fifths else []):
            for measure in _children(part, "measure"):
                for note in _children(measure, "note"):
                    pitch = _child(note, "pitch")
                    if pitch is None or _child(note, "unpitched") is not None or _child(note, "rest") is not None:
                        continue
                    alter = _pitch(pitch, "step", "alter", chromatic, diatonic, "octave")
                    accidental = _child(note, "accidental")
                    if accidental is not None:
                        _set_text(accidental, _ACCIDENTALS[alter])
                for harmony in _children(measure, "harmony"):
                    roots = _children(harmony, "root")
                    if not roots:
                        raise MusicXMLTranspositionError("Chord symbols without an explicit pitch root are not supported.")
                    for root in roots:
                        _pitch(root, "root-step", "root-alter", chromatic, diatonic)
                    for bass in _children(harmony, "bass"):
                        _pitch(bass, "bass-step", "bass-alter", chromatic, diatonic)
        output = document.toxml(encoding="utf-8")
        _check_integrity(output)
        return output
