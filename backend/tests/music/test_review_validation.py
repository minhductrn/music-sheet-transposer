import pytest

from app.music.review.document import Document
from app.music.review.importer import import_score


def score_xml(note, attributes="<divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time>"):
    return f'<score-partwise><part id="P1"><measure number="1"><attributes>{attributes}</attributes>{note}</measure></part></score-partwise>'.encode()


NOTE = '<note><pitch><step>C</step><octave>4</octave></pitch><duration>16</duration><voice>1</voice><type>whole</type><staff>1</staff></note>'


@pytest.mark.parametrize("xml,code", [
    (score_xml(NOTE.replace("<step>C</step>", "<step>H</step>")), "invalid_pitch"),
    (score_xml(NOTE.replace("<octave>4</octave>", "<octave>12</octave>")), "invalid_pitch"),
    (score_xml(NOTE.replace("<octave>4</octave>", "<octave>4.0</octave>")), "invalid_pitch"),
    (score_xml(NOTE.replace("<octave>4</octave>", "<alter>1/2</alter><octave>4</octave>")), "invalid_pitch"),
    (score_xml(NOTE.replace("<pitch><step>C</step><octave>4</octave></pitch>", "")), "missing_note_kind"),
    (score_xml(NOTE.replace("<duration>16</duration>", "<duration>0</duration>")), "invalid_duration"),
    (score_xml(NOTE.replace("<duration>16</duration>", "<duration>-4</duration>")), "invalid_duration"),
    (score_xml(NOTE.replace("<duration>16</duration>", "<duration>1/2</duration>")), "invalid_duration"),
    (score_xml(NOTE.replace("<duration>16</duration>", "")), "invalid_duration"),
    (score_xml(NOTE.replace("<voice>1</voice>", "<voice/>")), "invalid_voice"),
    (score_xml(NOTE.replace("<voice>1</voice>", "<voice>bad voice</voice>")), "invalid_voice"),
    (score_xml(NOTE.replace("<staff>1</staff>", "<staff>2</staff>")), "invalid_staff"),
    (score_xml(NOTE.replace("<pitch>", "<chord/><pitch>")), "broken_chord"),
    (score_xml(NOTE.replace("<pitch>", "<grace/><pitch>")), "grace_duration"),
    (score_xml(NOTE, "<divisions>0</divisions>"), "invalid_divisions"),
    (score_xml(NOTE, "<divisions>4</divisions><staves>0</staves>"), "invalid_staves"),
    (score_xml(NOTE, "<divisions>4</divisions><time><beats>4</beats></time>"), "invalid_meter"),
    (score_xml('<backup><duration>4</duration></backup>' + NOTE), "negative_onset"),
    (score_xml('<forward><duration>0</duration></forward>' + NOTE), "invalid_timing"),
])
def test_malformed_musical_fields_produce_errors_without_guessing(xml, code):
    doc = Document.parse(xml)
    _, diagnostics = import_score(doc)
    assert any(issue.code == code and issue.severity == "ERROR" for issue in diagnostics)
    assert doc.xml() == xml


@pytest.mark.parametrize("notes,code", [("", "empty_measure"), (NOTE.replace("<duration>16</duration>", "<duration>12</duration>"), "measure_duration_mismatch")])
def test_suspicious_measures_are_visible_warnings(notes, code):
    _, diagnostics = import_score(Document.parse(score_xml(notes)))
    assert any(issue.code == code and issue.severity == "WARNING" for issue in diagnostics)


def test_implicit_pickup_does_not_require_full_measure_duration():
    xml = score_xml(NOTE.replace("<duration>16</duration>", "<duration>4</duration>")).replace(b'<measure number="1">', b'<measure number="1" implicit="yes">')
    _, issues = import_score(Document.parse(xml))
    assert not any(issue.code == "measure_duration_mismatch" for issue in issues)


def test_chord_with_wrong_voice_or_longer_duration_is_an_error():
    second = NOTE.replace("<pitch>", "<chord/><pitch>").replace("<voice>1</voice>", "<voice>2</voice>")
    _, issues = import_score(Document.parse(score_xml(NOTE + second)))
    assert any(i.code == "broken_chord" and i.severity == "ERROR" for i in issues)
    second = second.replace("<voice>2</voice>", "<voice>1</voice>").replace("<duration>16</duration>", "<duration>20</duration>")
    _, issues = import_score(Document.parse(score_xml(NOTE + second)))
    assert any(i.code == "chord_duration" and i.severity == "ERROR" for i in issues)


def test_grace_and_size_are_independent_on_import():
    grace = NOTE.replace("<pitch>", "<grace/><pitch>").replace("<duration>16</duration>", "")
    small = NOTE.replace("<type>whole</type>", '<type size="cue">whole</type><notehead font-size="small">normal</notehead>')
    score, _ = import_score(Document.parse(score_xml(grace + small)))
    g, s = score.parts[0].measures[0].voices[0].events
    assert g.grace and g.display_size == "normal" and g.onset == "0"
    assert not s.grace and s.display_size == "small" and s.onset == "0" and s.duration == "4"


def test_unpitched_events_remain_unpitched_and_duration_bearing():
    note = NOTE.replace('<pitch><step>C</step><octave>4</octave></pitch>', '<unpitched><display-step>C</display-step><display-octave>4</display-octave></unpitched>')
    score, issues = import_score(Document.parse(score_xml(note)))
    event = score.parts[0].measures[0].voices[0].events[0]
    assert event.kind == "unpitched" and event.pitch is None and event.duration == "4"
    assert not any(i.severity == "ERROR" for i in issues)


def test_fractional_meter_timeline_remains_exact():
    note = NOTE.replace("<duration>16</duration>", "<duration>1</duration>")
    attributes = '<divisions>3</divisions><time><beats>1</beats><beat-type>12</beat-type></time>'
    score, _ = import_score(Document.parse(score_xml(note, attributes)))
    measure = score.parts[0].measures[0]
    assert measure.expected_duration == measure.actual_duration == "1/3"
