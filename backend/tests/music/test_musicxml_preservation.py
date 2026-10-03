from copy import deepcopy
import xml.etree.ElementTree as ET

import pytest

from app.music.musicxml.transposer import (
    MusicXMLTranspositionError,
    transpose_musicxml_document,
)


DOCUMENT = b'''<?xml version="1.0"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "https://www.musicxml.com/dtds/partwise.dtd">
<?application preserve-this?>
<score-partwise version="4.0">
  <!-- keep this comment -->
  <work><work-title>Preservation regression</work-title></work>
  <defaults><scaling><millimeters>7</millimeters><tenths>40</tenths></scaling></defaults>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1" implicit="no" width="200">
      <print new-system="yes"><system-layout><system-distance>100</system-distance></system-layout></print>
      <attributes><divisions>12</divisions><key><fifths>-5</fifths><mode>major</mode></key>
        <time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef>
      </attributes>
      <direction placement="above"><direction-type><words>Expressive</words></direction-type>
        <direction-type><dynamics><mf/></dynamics></direction-type><staff>1</staff><sound tempo="90"/>
      </direction>
      <note default-x="10"><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch>
        <duration>9</duration><tie type="start"/><voice>1</voice><type>eighth</type><dot/>
        <accidental cautionary="yes">sharp</accidental>
        <time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>
        <stem>up</stem><staff>1</staff><beam number="1">begin</beam>
        <notations><tied type="start"/><tuplet type="start" number="1"/>
          <articulations><staccato/></articulations><slur type="start" number="1"/></notations>
        <lyric number="1"><syllabic>single</syllabic><text>Hello</text></lyric>
      </note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>9</duration>
        <voice>1</voice><type>eighth</type><dot/><staff>1</staff><beam number="1">end</beam></note>
      <backup><duration>9</duration></backup>
      <note><rest measure="yes"/><duration>48</duration><voice>2</voice><staff>2</staff></note>
      <forward><duration>3</duration><voice>2</voice><staff>2</staff></forward>
      <note><unpitched><display-step>C</display-step><display-octave>5</display-octave></unpitched>
        <duration>12</duration><voice>3</voice><type>quarter</type><staff>2</staff></note>
      <barline location="right"><bar-style>light-heavy</bar-style></barline>
    </measure>
    <measure number="2"><note><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch>
      <duration>12</duration><tie type="stop"/><voice>1</voice><type>quarter</type><staff>1</staff>
      <notations><tied type="stop"/></notations></note></measure>
  </part>
</score-partwise>'''


def musical_skeleton(root):
    """Compare every node except the scalar values intentionally transposed."""
    root = deepcopy(root)
    for pitch in root.findall('.//note/pitch'):
        pitch.clear()
    for element in root.findall('.//key/fifths') + root.findall('.//note/accidental'):
        element.text = 'TRANSPOSED'
    return ET.tostring(root)


def test_transposition_preserves_complete_notation_and_event_order():
    output = transpose_musicxml_document(DOCUMENT, 2)
    original = ET.fromstring(DOCUMENT)
    result = ET.fromstring(output)
    assert musical_skeleton(result) == musical_skeleton(original)
    assert result.findtext('.//key/fifths') == '-3'
    pitches = result.findall('.//note/pitch')
    assert [(p.findtext('step'), p.findtext('alter'), p.findtext('octave')) for p in pitches] == [
        ('E', '-1', '4'), ('G', '-1', '4'), ('E', '-1', '4'),
    ]
    assert result.findtext('.//note/accidental') == 'flat'
    assert result.find('.//note/accidental').attrib == {'cautionary': 'yes'}
    for tag in ('rest', 'unpitched', 'backup', 'forward', 'beam', 'tie', 'dot',
                'time-modification', 'notations', 'lyric', 'direction', 'staff',
                'voice', 'chord', 'print', 'dynamics'):
        before = original.findall(f'.//{tag}')
        after = result.findall(f'.//{tag}')
        assert before, tag
        assert [ET.tostring(e) for e in after] == [ET.tostring(e) for e in before], tag
    assert b'<!-- keep this comment -->' in output
    assert b'<?application preserve-this?>' in output
    assert b'<!DOCTYPE score-partwise' in output


def test_zero_transposition_preserves_original_bytes():
    assert transpose_musicxml_document(DOCUMENT, 0) == DOCUMENT


def test_zero_preserves_unsupported_musical_values():
    source = score_xml(
        '<grace slash="yes"/><pitch><step>C</step><alter>0.5</alter>'
        '<octave>4</octave></pitch><accidental>quarter-sharp</accidental>',
        '<attributes><key><key-step>C</key-step><key-alter>0.5</key-alter>'
        '</key></attributes>',
    )
    assert transpose_musicxml_document(source, 0) == source


def test_grace_pitch_attributes_and_foreign_extensions_are_preserved():
    source = score_xml(
        '<grace slash="yes"/><pitch><step>C</step>'
        '<alter print-object="no">1</alter><octave>4</octave></pitch>'
        '<extension:note xmlns:extension="urn:custom"><extension:pitch>C4'
        '</extension:pitch></extension:note>',
    )
    result = ET.fromstring(transpose_musicxml_document(source, -1))
    assert result.find('.//grace').attrib == {'slash': 'yes'}
    assert result.findtext('.//pitch/alter') == '0'
    assert result.find('.//pitch/alter').attrib == {'print-object': 'no'}
    assert result.findtext('.//{urn:custom}pitch') == 'C4'


def test_prefixed_namespace_retained_when_inserting_alter():
    source = b'''<m:score-partwise xmlns:m="urn:musicxml"><m:part id="P1">
    <m:measure number="1"><m:note><m:pitch><m:step>C</m:step><m:octave>4</m:octave>
    </m:pitch></m:note></m:measure></m:part></m:score-partwise>'''
    output = transpose_musicxml_document(source, 1)
    assert b'<m:alter>1</m:alter>' in output
    result = ET.fromstring(output)
    assert result.findtext('.//{urn:musicxml}step') == 'C'


def score_xml(pitch, attributes='', namespace=''):
    return (f'<score-partwise {namespace}><part id="P1"><measure number="1">'
            f'{attributes}<note>{pitch}</note></measure></part></score-partwise>').encode()


@pytest.mark.parametrize(('step', 'octave', 'interval', 'expected'), [
    ('B', 4, 1, ('C', '5')),
    ('C', 4, -1, ('B', '3')),
    ('C', 4, 12, ('C', '5')),
    ('C', 4, -12, ('C', '3')),
])
def test_octave_crossing(step, octave, interval, expected):
    source = score_xml(f'<pitch><step>{step}</step><octave>{octave}</octave></pitch>')
    result = ET.fromstring(transpose_musicxml_document(source, interval))
    assert (result.findtext('.//pitch/step'), result.findtext('.//pitch/octave')) == expected


def test_minor_key_and_diatonic_spelling():
    source = score_xml('<pitch><step>B</step><octave>4</octave></pitch>',
                       '<attributes><key><fifths>-5</fifths><mode>minor</mode></key></attributes>')
    result = ET.fromstring(transpose_musicxml_document(source, 2))
    assert result.findtext('.//key/fifths') == '-3'
    assert result.findtext('.//key/mode') == 'minor'
    assert result.findtext('.//pitch/step') == 'D'
    assert result.findtext('.//pitch/alter') == '-1'


def test_key_changes_in_document_order_staff_inheritance_and_part_isolation():
    note = '<note><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch>{}</note>'
    source = ('<score-partwise><part id="P1"><measure number="1">'
              '<attributes><key number="1"><fifths>-5</fifths></key>'
              '<key number="2"><fifths>0</fifths></key></attributes>'
              + note.format('<staff>1</staff>') + note.format('<staff>2</staff>')
              + '</measure><measure number="2">' + note.format('<staff>1</staff>')
              + '<attributes><key><fifths>0</fifths></key></attributes>'
              + note.format('<staff>1</staff>') + '</measure></part><part id="P2">'
              '<measure number="1">' + note.format('') + '</measure></part></score-partwise>').encode()
    result = ET.fromstring(transpose_musicxml_document(source, 2))
    assert [p.findtext('step') for p in result.findall('.//pitch')] == ['E', 'D', 'E', 'D', 'D']
    assert [k.text for k in result.findall('.//key/fifths')] == ['-3', '2', '2']


@pytest.mark.parametrize('namespace', ['', 'xmlns="http://www.musicxml.org/ns/musicxml"'])
def test_namespace_preserved(namespace):
    source = score_xml('<pitch><step>C</step><octave>4</octave></pitch>', namespace=namespace)
    root = ET.fromstring(transpose_musicxml_document(source, 1))
    prefix = '{http://www.musicxml.org/ns/musicxml}' if namespace else ''
    pitch = root.find(f'.//{prefix}pitch')
    assert pitch.findtext(prefix + 'step') == 'C'
    assert pitch.findtext(prefix + 'alter') == '1'


def test_key_aware_spelling_handles_enharmonic_octave():
    source = score_xml('<pitch><step>F</step><octave>4</octave></pitch>',
                       '<attributes><key><fifths>0</fifths></key></attributes>')
    result = ET.fromstring(transpose_musicxml_document(source, 6))
    assert result.findtext('.//key/fifths') == '-6'
    assert result.findtext('.//pitch/step') == 'C'
    assert result.findtext('.//pitch/alter') == '-1'
    assert result.findtext('.//pitch/octave') == '5'


def test_key_cancellation_is_transposed():
    source = score_xml('<pitch><step>C</step><octave>4</octave></pitch>',
                       '<attributes><key><cancel location="left">0</cancel>'
                       '<fifths>-5</fifths></key></attributes>')
    result = ET.fromstring(transpose_musicxml_document(source, 2))
    assert result.findtext('.//key/cancel') == '2'
    assert result.find('.//key/cancel').attrib == {'location': 'left'}
    assert result.findtext('.//key/fifths') == '-3'


@pytest.mark.parametrize('source', [
    b'<broken>', b'<score-timewise/>',
    score_xml('<pitch><step>H</step><octave>4</octave></pitch>'),
    score_xml('<pitch><step>C</step><alter>0.5</alter><octave>4</octave></pitch>'),
    score_xml('<pitch><step>C</step><octave>4</octave></pitch>',
              '<attributes><key><key-step>C</key-step><key-alter>1</key-alter></key></attributes>'),
    b'<!DOCTYPE score-partwise [<!ENTITY value "expanded">]><score-partwise/>',
])
def test_invalid_or_unsupported_input_is_rejected(source):
    with pytest.raises(MusicXMLTranspositionError):
        transpose_musicxml_document(source, 1)
