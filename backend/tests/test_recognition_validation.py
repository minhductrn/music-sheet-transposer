import pytest

from app.music.recognition.errors import RecognitionError
from app.music.recognition.validation import validate_musicxml


def note(step='C', duration=4, extra='', voice=1):
    return (f'<note>{extra}<pitch><step>{step}</step><octave>4</octave></pitch>'
            f'<duration>{duration}</duration><voice>{voice}</voice><type>whole</type></note>')


def score(body, attributes='<divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time>', measure_attrs=''):
    return (f'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Music</part-name>'
            f'</score-part></part-list><part id="P1"><measure number="1" {measure_attrs}>'
            f'<attributes>{attributes}</attributes>{body}</measure></part></score-partwise>').encode()


def codes(contents, expect_lyrics=False):
    return {issue.code for issue in validate_musicxml(contents, expect_lyrics=expect_lyrics)[1]}


def test_complete_duration_chords_voices_and_backups():
    body = note() + note('E', extra='<chord/>') + '<backup><duration>4</duration></backup>' + note('G', voice=2)
    metadata, issues = validate_musicxml(score(body), expect_lyrics=False)
    assert not issues
    assert metadata['counts']['notes'] == 3
    assert metadata['counts']['pitched_notes'] == 3
    assert metadata['counts']['chord_notes'] == 1
    assert metadata['voices'] == ['1', '2']


def test_forward_preserves_duration_without_inventing_notes():
    assert not codes(score('<forward><duration>2</duration></forward>' + note(duration=2)))


def test_inherited_divisions_and_time_detect_missing_beats():
    xml = score(note()).replace(b'</part>', b'<measure number="2">' + note(duration=2).encode() + b'</measure></part>')
    metadata, issues = validate_musicxml(xml, expect_lyrics=False)
    assert metadata['counts']['measures'] == 2
    assert issues[0].code == 'measure_duration_mismatch'
    assert issues[0].measure == '2'
    assert issues[0].details['expected_quarter_beats'] == '4'
    assert issues[0].details['actual_quarter_beats'] == '2'


def test_grace_notes_do_not_advance_rhythmic_position():
    grace = '<note><grace/><pitch><step>D</step><octave>4</octave></pitch><type>eighth</type></note>'
    metadata, issues = validate_musicxml(score(grace + note()), expect_lyrics=False)
    assert not issues
    assert metadata['counts']['grace_notes'] == 1


def test_duration_bearing_cue_sizing_does_not_change_timing():
    xml = score(note() + note('E', extra='<chord/>')).replace(b'<type>whole</type>', b'<type size="cue">whole</type>', 1)
    assert not codes(xml)


def test_rest_and_unpitched_notes_are_counted():
    body = '<note><rest/><duration>2</duration></note><note><unpitched><display-step>C</display-step><display-octave>4</display-octave></unpitched><duration>2</duration></note>'
    metadata, issues = validate_musicxml(score(body), expect_lyrics=False)
    assert not issues
    assert metadata['counts']['pitched_notes'] == 0
    assert metadata['counts']['rest_notes'] == 1
    assert metadata['counts']['unpitched_notes'] == 1


def test_suspicious_empty_measure_is_reported():
    xml = score(note()).replace(b'</part>', b'<measure number="2"><direction/></measure></part>')
    assert codes(xml) == {'empty_measure'}


def test_lyrics_expected_and_nonempty_text_check():
    assert 'missing_lyrics' in codes(score(note()), expect_lyrics=True)
    xml = score(note(extra='<lyric><text>Chúng</text></lyric>'))
    assert 'missing_lyrics' not in codes(xml, expect_lyrics=True)


@pytest.mark.parametrize('xml', [
    b'<broken>', b'<score-partwise/>', b'<score-timewise/>', b'<notscore-partwise/>',
    b'<score-partwise><part id="P1"/></score-partwise>',
    b'<score-partwise><part id="P1"><measure number="1"/></part></score-partwise>',
    score('<note><duration>4</duration></note>'),
    score(note(step='H')), score(note()).replace(b'<octave>4</octave>', b'<octave>12</octave>'),
    score(note()).replace(b'<step>C</step>', b''),
    score(note()).replace(b'<octave>4</octave>', b'<alter>NaN</alter><octave>4</octave>'),
])
def test_malformed_or_nonmusical_document_rejected_with_diagnostics(xml):
    with pytest.raises(RecognitionError) as exc:
        validate_musicxml(xml, expect_lyrics=False)
    assert exc.value.status_code == 502
    assert exc.value.diagnostics[0].code == 'invalid_musicxml'


def test_musicxml_namespace_supported():
    xml = score(note()).replace(b'<score-partwise ', b'<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" ')
    assert not codes(xml)


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_entity_expansion_is_rejected_before_parsing(encoding):
    xml = ('<?xml version="1.0" encoding="' + encoding + '"?>'
           '<!DOCTYPE score-partwise [<!ENTITY secret "untrusted">]>'
           '<score-partwise>&secret;</score-partwise>').encode(encoding)
    with pytest.raises(RecognitionError):
        validate_musicxml(xml, expect_lyrics=False)


def test_external_musicxml_doctype_is_not_fetched():
    xml = b'<!DOCTYPE score-partwise SYSTEM "https://invalid.example/score.dtd">' + score(note())
    assert not codes(xml)


@pytest.mark.parametrize(('body', 'expected_code'), [
    (note(duration=2), 'measure_duration_mismatch'),
    (note(duration=5), 'measure_duration_mismatch'),
    (note().replace('<duration>4</duration>', ''), 'unknown_note_duration'),
    (note(duration=0), 'unknown_note_duration'),
    ('<backup><duration>1</duration></backup>' + note(), 'negative_measure_position'),
    (note(extra='<chord/>'), 'orphan_chord'),
])
def test_timing_uncertainty_is_reported(body, expected_code):
    assert expected_code in codes(score(body))


def test_implicit_pickup_is_allowed_but_overfull_measure_is_reported():
    assert not codes(score(note(duration=1), measure_attrs='implicit="yes"'))
    assert 'measure_duration_mismatch' in codes(score(note(duration=5), measure_attrs='implicit="yes"'))


def test_additive_time_and_fractional_divisions():
    attributes = '<divisions>2</divisions><time><beats>3+2</beats><beat-type>8</beat-type></time>'
    assert not codes(score(note(duration=5), attributes=attributes))


def test_divisions_change_and_cross_staff_chord():
    body = note(duration=2, extra='<staff>1</staff>') + '<attributes><divisions>2</divisions></attributes>'
    body += note('E', duration=4, extra='<staff>2</staff>') + note('G', duration=4, extra='<chord/><staff>1</staff>')
    assert not codes(score(body))


def test_distinct_staff_meters_are_not_guessed():
    attributes = ('<divisions>1</divisions><time number="1"><beats>4</beats><beat-type>4</beat-type></time>'
                  '<time number="2"><beats>3</beats><beat-type>4</beat-type></time>')
    assert 'measure_duration_mismatch' not in codes(score(note(duration=3), attributes=attributes))


def test_diagnostics_are_bounded_without_losing_uncertainty():
    xml = score(note(duration=1)).replace(b'</part>', b'<measure number="2"/><measure number="3"/></part>')
    metadata, issues = validate_musicxml(xml, expect_lyrics=True, max_issues=2)
    assert len(issues) == 2
    assert issues[-1].code == 'diagnostics_truncated'
    assert metadata['issue_count'] == 4
