"""Derive independent written Sax scores from concert-pitch MusicXML."""
from xml.etree import ElementTree as ET
from .transposer import MusicXMLTranspositionError, transpose_musicxml_document
from .concert_key import _document, _elements, _pitch
from app.music.review.document import Document

INSTRUMENTS = {"alto": (9, -5, -9, 0, "Alto Saxophone", 66),
               "soprano": (2, -1, -2, 0, "Soprano Saxophone", 65),
               "tenor": (14, -1, -2, -1, "Tenor Saxophone", 67)}


def instrument_score(contents: bytes, instrument: str, direction: str = "up") -> bytes:
    if instrument not in INSTRUMENTS:
        raise MusicXMLTranspositionError("Choose Alto, Soprano or Tenor Saxophone.")
    # Reject already-written scores; never apply the offset twice.
    doc = Document.parse(contents)
    parts = doc.children(doc.root, 'part')
    if len(parts) != 1:
        raise MusicXMLTranspositionError("Choose a single-part concert score for this Sax pilot.")
    for node in doc.root.iter(doc.namespace + 'transpose'):
        if doc.child(node, 'double') is not None or any(float(doc.text(node, t, '0')) != 0 for t in ('diatonic', 'chromatic', 'octave-change')):
            raise MusicXMLTranspositionError("This is already a written instrument score; open its concert source.")
    if any(doc.child(n, 'unpitched') is not None for n in doc.root.iter(doc.namespace + 'note')):
        raise MusicXMLTranspositionError("Unpitched percussion cannot become a Sax score.")
    offset, diatonic, chromatic, octave, name, program = INSTRUMENTS[instrument]
    if direction not in ('up','down'): raise MusicXMLTranspositionError('Choose Up or Down.')
    standard_offset=offset
    offset=offset if direction=='up' else offset%12-12
    written_diatonic=-diatonic-7*octave-7*((standard_offset-offset)//12)
    transposed = transpose_musicxml_document(contents, offset)
    with _document(transposed) as dom:
        for harmony in _elements(dom, 'harmony'):
            roots = [n for n in harmony.childNodes if getattr(n, 'localName', None) == 'root']
            if not roots: raise MusicXMLTranspositionError('Chord symbols need an explicit root for Sax transposition.')
            for root in roots: _pitch(root, 'root-step', 'root-alter', offset, written_diatonic)
            for bass in [n for n in harmony.childNodes if getattr(n, 'localName', None) == 'bass']:
                _pitch(bass, 'bass-step', 'bass-alter', offset, written_diatonic)
        transposed = dom.toxml(encoding='utf-8')
    output = Document.parse(transposed)
    ns = output.namespace
    for pitch in output.root.iter(ns+'pitch'):
        if not 0 <= int(output.text(pitch,'octave')) <= 9:
            raise MusicXMLTranspositionError('This direction exceeds the MusicXML octave range; choose the other direction.')
    part_list = output.child(output.root, 'part-list')
    if part_list is None: raise MusicXMLTranspositionError('The concert part definition is missing.')
    definitions = output.children(part_list, 'score-part')
    if len(definitions) != 1 or definitions[0].get('id') != parts[0].get('id'):
        raise MusicXMLTranspositionError("The concert part definition is ambiguous.")
    definition = definitions[0]
    # Keep unrelated credits/notation. Replace only instrument identity and transposition.
    for child in list(definition):
        if child.tag in {ns+t for t in ('part-name', 'part-abbreviation', 'part-name-display', 'part-abbreviation-display', 'score-instrument', 'midi-instrument')}: definition.remove(child)
    part_name = ET.Element(ns+'part-name'); part_name.text = name; definition.insert(0, part_name)
    abbreviation = ET.Element(ns+'part-abbreviation'); abbreviation.text = name.split()[0]+' Sax.'; definition.insert(1, abbreviation)
    iid = definition.get('id')+'-sax'
    for note in output.root.iter(ns+'note'):
        for reference in output.children(note, 'instrument'): reference.set('id', iid)
    for sound in output.root.iter(ns+'sound'):
        for midi_ref in output.children(sound, 'midi-instrument'): midi_ref.set('id', iid)
    si = ET.SubElement(definition, ns+'score-instrument', {'id': iid})
    ET.SubElement(si, ns+'instrument-name').text = name
    midi = ET.SubElement(definition, ns+'midi-instrument', {'id': iid})
    ET.SubElement(midi, ns+'midi-channel').text = '1'
    ET.SubElement(midi, ns+'midi-program').text = str(program)
    for part in output.children(output.root, 'part'):
        measures = output.children(part, 'measure')
        if not measures: raise MusicXMLTranspositionError("The concert part is empty.")
        for node in part.iter(ns+'attributes'):
            for old in output.children(node, 'transpose'): node.remove(old)
        attrs = output.child(measures[0], 'attributes')
        if attrs is None:
            attrs = ET.Element(ns+'attributes'); measures[0].insert(0, attrs)
        trans = ET.Element(ns+'transpose')
        ET.SubElement(trans, ns+'diatonic').text = str(diatonic)
        ET.SubElement(trans, ns+'chromatic').text = str(chromatic)
        if octave: ET.SubElement(trans, ns+'octave-change').text = str(octave)
        # MusicXML attributes order: transpose precedes directive/measure-style.
        index = next((i for i,n in enumerate(attrs) if n.tag in {ns+'directive',ns+'measure-style'}),len(attrs))
        attrs.insert(index, trans)
    output.changed = True
    return output.xml()
