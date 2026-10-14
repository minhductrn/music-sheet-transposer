"""Controlled concert-key fixtures; no private files or OMR dependencies."""
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest

from app.music.musicxml.concert_key import concert_key_info, transpose_concert_key
from app.music.musicxml.transposer import MusicXMLTranspositionError
from app.music.review.document import Document


def score(fifths=0, mode='major', step='C', alter=0):
    notes = []
    for measure, kind in [(1, 'start'), (2, 'stop')]:
        body = ''
        for index, (pitch, alteration, orientation) in enumerate([(step, alter, 'over'), ('E', 0, 'under')]):
            owned = f'review-tie-{str(index + 1) * 32}-s1-t1-{kind}'
            body += f'''<note id="note-{measure}-{index}">{'<chord/>' if index else ''}
<pitch><step>{pitch}</step><alter>{alteration}</alter><octave>4</octave></pitch>
<duration>4</duration><tie type="{kind}"/><voice>1</voice><type{' size="cue"' if index == 0 else ''}>whole</type>
<accidental cautionary="yes">natural</accidental><staff>1</staff><notehead{' font-size="small"' if index == 0 else ''}>normal</notehead>
<notations><tied type="{kind}" number="{index+2}" id="{owned}" orientation="{orientation}"/>
<slur type="{kind}" number="1"/><articulations><accent/></articulations></notations>
<lyric number="1"><syllabic>single</syllabic><text>Việt {index}</text></lyric></note>'''
        body += '<backup><duration>4</duration></backup><note><rest/><duration>4</duration><voice>2</voice><type>whole</type><staff>1</staff></note>'
        notes.append(f'<measure number="{measure}">' + (f'''<attributes><divisions>1</divisions><key><fifths>{fifths}</fifths><mode>{mode}</mode></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
<harmony id="h1"><root><root-step>C</root-step></root><kind text="maj7">major-seventh</kind><bass><bass-step>G</bass-step></bass><degree><degree-value>9</degree-value><degree-alter>1</degree-alter><degree-type>add</degree-type></degree></harmony>''' if measure == 1 else '') + body + '</measure>')
    return ('<?xml version="1.0"?><score-partwise version="4.0"><!--retain--><part-list><score-part id="P1"><part-name>Concert</part-name></score-part></part-list><part id="P1">' + ''.join(notes) + '</part></score-partwise>').encode()


def pitch(contents):
    p = ET.fromstring(contents).find('.//pitch')
    return p.findtext('step'), int(p.findtext('alter', '0')), int(p.findtext('octave'))


@pytest.mark.parametrize('source,mode,step,alter,target,direction,expected', [
    (0, 'major', 'C', 0, 2, 'up', ('D', 0, 4)),
    (0, 'major', 'C', 0, 2, 'down', ('D', 0, 3)),
    (0, 'minor', 'A', 0, -3, 'up', ('C', 0, 5)),
    (0, 'minor', 'A', 0, -3, 'down', ('C', 0, 4)),
    (0, 'minor', 'G', 1, -3, 'up', ('B', 0, 4)),
    (0, 'major', 'F', 1, -2, 'down', ('E', 0, 4)),
    (0, 'major', 'C', 1, -5, 'up', ('D', 0, 4)),
    (0, 'major', 'C', 1, 7, 'up', ('C', 2, 4)),
    (7, 'major', 'C', 1, -5, 'down', ('D', -1, 4)),
    (0, 'major', 'C', 0, 7, 'down', ('C', 1, 3)),
    (7, 'major', 'C', 1, 0, 'up', ('C', 0, 5)),
    (5, 'major', 'B', 0, -7, 'up', ('C', -1, 5)),
])
def test_key_intervals_and_spelling(source, mode, step, alter, target, direction, expected):
    original = score(source, mode, step, alter)
    output = transpose_concert_key(original, target, direction)
    assert pitch(output) == expected
    assert concert_key_info(output)['suggested'] == {'fifths': target, 'mode': mode}


def invariant(contents):
    root = ET.fromstring(contents, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for node in root.iter():
        for child in list(node):
            if child.tag in {'pitch', 'accidental', 'key', 'root', 'bass'}:
                node.remove(child)
        if node.text and not node.text.strip():
            node.text = None
        if node.tail and not node.tail.strip():
            node.tail = None
    return ET.tostring(root)


def test_chords_and_all_unrelated_notation_survive():
    original = score()
    before_links = deepcopy(Document.parse(original).manual_ties)
    output = transpose_concert_key(original, 2, 'up')
    root = ET.fromstring(output)
    assert root.findtext('.//harmony/root/root-step') == 'D'
    assert root.findtext('.//harmony/bass/bass-step') == 'A'
    assert invariant(output) == invariant(original)
    assert Document.parse(output).manual_ties == before_links
    assert len(before_links) == 2
    assert [n.get('orientation') for n in root.findall('.//tied')] == ['over', 'under', 'over', 'under']
    assert [n.findtext('pitch/step') for n in root.findall('.//note') if n.find('pitch') is not None] == ['D', 'F', 'D', 'F']
    assert all(n.findtext('pitch/alter') == '1' for n in root.findall('.//note') if n.findtext('pitch/step') == 'F')
    assert transpose_concert_key(original, 0, 'down') == original


def test_unpitched_and_percussion_are_untouched():
    original = score().replace(b'</part-list>', b'<score-part id="P2"><part-name>Drums</part-name><midi-instrument id="drum"><midi-channel>10</midi-channel></midi-instrument></score-part></part-list>')
    drums = b'<part id="P2"><measure number="1"><attributes><divisions>1</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note><note><unpitched><display-step>F</display-step><display-octave>4</display-octave></unpitched><duration>4</duration></note></measure></part>'
    original = original.replace(b'</score-partwise>', drums + b'</score-partwise>')
    output = transpose_concert_key(original, 2, 'up')
    assert ET.tostring(ET.fromstring(output).find("part[@id='P2']")) == ET.tostring(ET.fromstring(original).find("part[@id='P2']"))


@pytest.mark.parametrize('replacement,expected', [
    ((b'<mode>major</mode>', b''), 'mode will not be guessed'),
    ((b'<key><fifths>0</fifths><mode>major</mode></key>', b''), 'source key is missing'),
    ((b'<mode>major</mode>', b'<mode>dorian</mode>'), 'unsupported modes'),
    ((b'<alter>0</alter>', b'<alter>0.5</alter>'), 'Microtonal'),
    ((b'<measure number="2">', b'<measure number="2"><attributes><key><fifths>1</fifths><mode>major</mode></key></attributes>'), 'Key changes'),
    ((b'<divisions>1</divisions>', b'<divisions>1</divisions><transpose><diatonic>1</diatonic><chromatic>2</chromatic></transpose>'), 'concert-pitch'),
    ((b'<root-step>C</root-step>', b'<root-step text="Do">C</root-step>'), 'Custom chord'),
    ((b'<duration>4</duration>', b'<duration>-1</duration>'), 'positive duration'),
    ((b'<mode>major</mode>', b'<mode>major</mode><key-octave number="1">4</key-octave>'), 'octave placement'),
    ((b'<slur type=', b'<accidental-mark>sharp</accidental-mark><slur type='), 'ornament accidentals'),
    ((b'<accidental cautionary="yes">', b'<accidental smufl="accidentalNatural" cautionary="yes">'), 'display overrides'),
])
def test_unsafe_or_uncertain_inputs_fail_without_changing_source(replacement, expected):
    original = score().replace(*replacement)
    snapshot = bytes(original)
    with pytest.raises(MusicXMLTranspositionError, match=expected):
        transpose_concert_key(original, 2, 'up')
    assert original == snapshot


def test_namespaces_preserve_owned_identity_and_chromatic_chord_alterations():
    original = score().replace(b'<score-partwise version="4.0">', b'<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" version="4.0">')
    original = original.replace(b'<root-step>C</root-step>', b'<root-step>C</root-step><root-alter>1</root-alter>')
    output = transpose_concert_key(original, -5, 'up')
    root = ET.fromstring(output)
    ns = {'m': 'http://www.musicxml.org/ns/musicxml'}
    assert root.findtext('.//m:root/m:root-step', namespaces=ns) == 'D'
    assert root.findtext('.//m:root/m:root-alter', namespaces=ns) == '0'
    assert Document.parse(output).manual_ties == Document.parse(original).manual_ties


def test_explicit_f_major_is_a_suggestion_not_a_forced_mode():
    original = score(-1, 'major', 'F')
    detected = concert_key_info(original)
    assert detected == {'fifths': -1, 'mode': 'major', 'suggested': {'fifths': -1, 'mode': 'major'},
                        'candidates': [{'fifths': -1, 'mode': 'major'}, {'fifths': -1, 'mode': 'minor'}]}
    # The user may correct a declared mode while retaining the same signature.
    output = transpose_concert_key(original, 1, 'up', source_fifths=-1, source_mode='minor')
    assert concert_key_info(output)['suggested'] == {'fifths': 1, 'mode': 'minor'}
    assert pitch(output) == ('G', 0, 4)


@pytest.mark.parametrize('mode,step', [('major', 'F'), ('minor', 'D')])
def test_one_flat_without_mode_uses_confirmed_key_and_preserves_notation(mode, step):
    original = score(-1, 'major', step).replace(b'<mode>major</mode>', b'')
    snapshot = bytes(original)
    detected = concert_key_info(original)
    assert detected['mode'] is None and detected['suggested'] is None
    assert detected['candidates'] == [{'fifths': -1, 'mode': 'major'}, {'fifths': -1, 'mode': 'minor'}]
    output = transpose_concert_key(original, 1, 'up', source_fifths=-1, source_mode=mode)
    assert pitch(output) == (('G' if mode == 'major' else 'E'), 0, 4)
    assert concert_key_info(output)['suggested'] == {'fifths': 1, 'mode': mode}
    assert invariant(output) == invariant(original)
    assert Document.parse(output).manual_ties == Document.parse(original).manual_ties
    assert original == snapshot


def test_incompatible_source_key_is_rejected_without_mutation():
    original = score(-1).replace(b'<mode>major</mode>', b'')
    with pytest.raises(MusicXMLTranspositionError, match='incompatible'):
        transpose_concert_key(original, 2, 'up', source_fifths=0, source_mode='major')
    assert b'<fifths>-1</fifths>' in original
    assert b'<mode>' not in original


def test_same_signature_confirmation_only_adds_mode_to_independent_result():
    original = score(-1).replace(b'<mode>major</mode>', b'')
    output = transpose_concert_key(original, -1, 'up', source_fifths=-1, source_mode='major')
    before, after = ET.fromstring(original), ET.fromstring(output)
    for key in after.findall('.//key'):
        assert key.findtext('mode') == 'major'
        key.remove(key.find('mode'))
    assert ET.tostring(before) == ET.tostring(after)
    assert b'<mode>' not in original
