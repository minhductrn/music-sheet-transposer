from dataclasses import asdict
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.music.review.document import Document, ReviewError
from app.music.review.importer import import_score
from app.music.review.models import EventAdd, EventPatch, HarmonyPatch, PitchInput
from app.music.review.patcher import add_event, delete_event, patch_event, patch_harmony, patch_lyric


FIXTURE = Path(__file__).parent / "fixtures/review_mixed_size.musicxml"


def events(score):
    return [event for part in score.parts for measure in part.measures for voice in measure.voices for event in voice.events]


def document(xml=None):
    return Document.parse(xml or FIXTURE.read_bytes())


def test_import_projection_includes_inherited_attributes_and_exact_timeline():
    score, issues = import_score(document())
    assert not [issue for issue in issues if issue.severity != "INFO"]
    first, second = score.parts[0].measures
    assert first.divisions == second.divisions == "4"
    assert first.time_signature == second.time_signature == [{"staff": None, "pairs": [{"beats": "4", "beat_type": "4"}]}]
    assert first.key_signature == second.key_signature == [{"staff": None, "fifths": "-1", "mode": "major"}]
    assert first.actual_duration == first.expected_duration == "4"
    assert first.staves == second.staves == 2
    assert [v.id for v in first.voices] == ["1", "2"]
    a, c, rest, bass, last_rest, tied = events(score)
    assert (a.pitch.step, a.pitch.octave, a.onset, a.duration, a.voice, a.staff) == ("A", 4, "0", "1", "1", 1)
    assert (c.pitch.step, c.pitch.octave, c.onset, c.duration, c.display_size, c.grace) == ("C", 5, "0", "1", "small", False)
    assert a.chord_id == c.chord_id == a.id
    assert not a.chord_member and c.chord_member
    assert (rest.kind, rest.onset, rest.duration) == ("rest", "1", "3")
    assert (bass.onset, bass.duration, bass.voice, bass.staff) == ("0", "2", "2", 2)
    assert (last_rest.onset, last_rest.duration) == ("3", "1")
    assert a.ties == ["start"] and tied.ties == ["stop"]
    assert score.lyrics[0]["text"] == "ta" and score.lyrics[1]["segments"] == ["cùng", "đem"]
    assert a.lyric_ids == [score.lyrics[0]["id"]]
    assert score.harmonies[0]["root_step"] == "F" and score.harmonies[0]["onset"] == "0"


def test_unedited_roundtrip_is_byte_identical_and_ids_are_deterministic():
    contents = FIXTURE.read_bytes()
    one, two = document(), document()
    assert one.xml() == two.xml() == contents
    assert asdict(import_score(one)[0]) == asdict(import_score(two)[0])
    assert document(one.xml()).xml() == contents


def test_clone_keeps_sidecar_references_attached_and_edits_isolated():
    original = document()
    clone = original.clone()
    patch_event(clone, "e-2", EventPatch(pitch=PitchInput(step="D", octave=5)))
    assert clone.get("e-2", "note") in list(clone.get("m-1", "measure"))
    assert original.text(original.child(original.get("e-2", "note"), "pitch"), "step") == "C"
    assert clone.text(clone.child(clone.get("e-2", "note"), "pitch"), "step") == "D"


def test_pitch_patch_preserves_every_unrelated_element_structurally():
    doc = document()
    before = ET.fromstring(doc.xml())
    patch_event(doc, "e-2", EventPatch(pitch=PitchInput(step="B", alter="-1", octave=4)))
    after = ET.fromstring(doc.xml())
    # A structural oracle independent of our projection: remove the one intentionally edited pitch.
    before.findall(".//note")[1].remove(before.findall(".//note")[1].find("pitch"))
    after.findall(".//note")[1].remove(after.findall(".//note")[1].find("pitch"))
    assert ET.tostring(before) == ET.tostring(after)
    assert "<!-- Mixed sizes" in doc.xml().decode()


def test_duration_edit_updates_shared_chord_types_and_preserves_timing_events():
    doc = document()
    backup = ET.tostring(doc.root.find(".//backup"))
    forward = ET.tostring(doc.root.find(".//forward"))
    patch_event(doc, "e-2", EventPatch(duration="3/2"))
    notes = doc.root.findall(".//note")
    assert [n.findtext("duration") for n in notes[:2]] == ["6", "6"]
    assert [n.findtext("type") for n in notes[:2]] == ["quarter", "quarter"]
    assert all(n.find("dot") is not None for n in notes[:2])
    assert notes[1].find("notehead").get("font-size") == "small"
    assert ET.tostring(doc.root.find(".//backup")) == backup
    assert ET.tostring(doc.root.find(".//forward")) == forward
    assert "measure_duration_mismatch" in {i.code for i in import_score(doc)[1]}


@pytest.mark.parametrize("size", ["normal", "small", "cue"])
def test_size_never_changes_rhythmic_semantics(size):
    doc = document()
    patch_event(doc, "e-2", EventPatch(display_size=size))
    c = events(import_score(document(doc.xml()))[0])[1]
    assert c.display_size == size
    assert c.onset == "0" and c.duration == "1" and c.chord_member and not c.grace
    assert doc.get("e-2", "note").find("grace") is None
    assert doc.get("e-2", "note").find("cue") is None


def test_mixed_size_survives_unrelated_edit_export_and_reimport():
    doc = document()
    patch_lyric(doc, "l-1", "tạ")
    a, c = events(import_score(document(doc.xml()))[0])[:2]
    assert [(n.pitch.step, n.pitch.octave) for n in (a, c)] == [("A", 4), ("C", 5)]
    assert a.onset == c.onset == "0" and a.duration == c.duration == "1"
    assert (a.display_size, c.display_size) == ("normal", "small")
    assert not a.grace and not c.grace


def test_add_simultaneous_note_copies_duration_and_shared_stem_without_copying_lyrics_or_ties():
    doc = document()
    add_event(doc, "new-1", EventAdd(measure_id="m-1", chord_with_id="e-1", pitch=PitchInput(step="E", octave=5), display_size="small"))
    added = doc.get("new-1", "note")
    assert added.find("chord") is not None and added.findtext("stem") == "up"
    assert added.findtext("duration") == "4" and added.find("grace") is None
    assert added.find("lyric") is None and added.find("tie") is None
    es = events(import_score(doc)[0])
    new = next(e for e in es if e.id == "new-1")
    assert new.onset == "0" and new.duration == "1" and new.chord_id == "e-1"
    assert es[3].onset == "1"  # Rest remains in the same position.


@pytest.mark.parametrize("anchor", ["before_event_id", "after_event_id"])
def test_sequential_insert_is_relative_to_entire_chord(anchor):
    doc = document()
    add_event(doc, "new-1", EventAdd(measure_id="m-1", kind="rest", duration="1/2", **{anchor: "e-2"}))
    notes = doc.root.findall("./part/measure")[0].findall("note")
    assert notes[0 if anchor == "before_event_id" else 2] is doc.refs["new-1"]
    assert doc.text(doc.refs["new-1"], "type") == "eighth"
    assert doc.text(doc.refs["new-1"], "duration") == "2"


def test_delete_leading_note_promotes_surviving_chord_without_losing_onset():
    doc = document()
    delete_event(doc, "e-1")
    score, _ = import_score(doc)
    c = events(score)[0]
    assert c.id == "e-2" and not c.chord_member and c.duration == "1" and c.onset == "0"
    assert doc.get("e-2", "note").find("chord") is None
    assert "e-1" not in doc.refs and "l-1" not in doc.refs
    assert [l["id"] for l in score.lyrics] == ["l-2"]


def test_delete_member_does_not_advance_or_shift_remaining_events():
    doc = document()
    delete_event(doc, "e-2")
    a, rest = events(import_score(doc)[0])[:2]
    assert a.chord_id is None and rest.onset == "1"


def test_lyric_patch_preserves_syllabic_extend_elision_and_other_segments():
    doc = document()
    patch_lyric(doc, "l-1", "tạ")
    patch_lyric(doc, "l-2", "đêm", 1)
    assert doc.get("l-1", "lyric").find("extend").get("type") == "start"
    lyric = doc.get("l-2", "lyric")
    assert lyric.findtext("syllabic") == "begin" and lyric.find("elision") is not None
    assert [n.text for n in lyric.findall("text")] == ["cùng", "đêm"]


def test_harmony_patch_preserves_degrees_and_other_attributes():
    doc = document()
    degree = ET.tostring(doc.get("h-1", "harmony").find("degree"))
    patch_harmony(doc, "h-1", HarmonyPatch(root_step="B", root_alter="-1", kind="minor", text="Bb m"))
    node = doc.get("h-1", "harmony")
    assert node.findtext("root/root-step") == "B" and node.findtext("root/root-alter") == "-1"
    assert node.find("kind").text == "minor" and node.find("kind").get("text") == "Bb m"
    assert ET.tostring(node.find("degree")) == degree


def test_grace_conversion_is_explicit_and_applies_to_the_whole_chord():
    doc = document()
    patch_event(doc, "e-2", EventPatch(grace=True))
    a, c = events(import_score(doc)[0])[:2]
    assert a.grace and c.grace and a.duration is c.duration is None
    assert c.display_size == "small"
    with pytest.raises(ReviewError, match="explicit duration"):
        patch_event(doc.clone(), "e-2", EventPatch(grace=False))
    patch_event(doc, "e-2", EventPatch(grace=False, duration="1"))
    assert not events(import_score(doc)[0])[1].grace


@pytest.mark.parametrize("patch", [EventPatch(duration="0"), EventPatch(duration="-1"), EventPatch(duration="1/3"), EventPatch(duration="bogus"), EventPatch(staff=3), EventPatch(pitch=None), EventPatch()])
def test_invalid_edits_are_rejected(patch):
    with pytest.raises(ReviewError):
        patch_event(document(), "e-1", patch)


@pytest.mark.parametrize("xml", [b"<broken>", b"<score-timewise/>", b"<score-partwise/>",
    b'<!DOCTYPE score-partwise [<!ENTITY x "unsafe">]><score-partwise><part id="P1"/></score-partwise>'])
def test_unsafe_or_unsupported_document_is_rejected(xml):
    with pytest.raises(ReviewError):
        Document.parse(xml)


def test_node_budget_is_enforced_before_building_tree():
    with pytest.raises(ReviewError) as exc:
        Document.parse(FIXTURE.read_bytes(), max_nodes=5)
    assert exc.value.status_code == 413


def test_excessive_xml_depth_is_rejected_before_snapshotting():
    xml = b'<score-partwise><part id="P1">' + b'<nested>' * 65 + b'</nested>' * 65 + b'</part></score-partwise>'
    with pytest.raises(ReviewError) as exc:
        Document.parse(xml)
    assert exc.value.status_code == 413


def test_namespaced_document_edits_preserve_namespace_and_unsupported_elements():
    xml = FIXTURE.read_bytes().replace(b'<score-partwise version="4.0">', b'<score-partwise xmlns="urn:test:musicxml" version="4.0">')
    doc = document(xml)
    patch_event(doc, "e-2", EventPatch(pitch=PitchInput(step="D", octave=5)))
    root = ET.fromstring(doc.xml())
    assert root.findtext('.//{urn:test:musicxml}pitch/{urn:test:musicxml}step') == "A"
    assert root.find('.//{urn:test:musicxml}articulations/{urn:test:musicxml}accent') is not None


def test_divisions_change_uses_each_event_actual_scale_for_edits():
    xml = b'<score-partwise><part id="P1"><measure number="1"><attributes><divisions>2</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note><attributes><divisions>4</divisions></attributes><note><rest/><duration>4</duration><type>quarter</type></note></measure></part></score-partwise>'
    doc = document(xml)
    patch_event(doc, "e-1", EventPatch(duration="2"))
    assert doc.get("e-1", "note").findtext("duration") == "4"
    assert events(import_score(doc)[0])[0].duration == "2"


def test_tuplet_duration_patch_keeps_ratio_and_notations():
    xml = b'<score-partwise><part id="P1"><measure><attributes><divisions>3</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification><notations><tuplet type="start"/></notations></note></measure></part></score-partwise>'
    doc = document(xml)
    patch_event(doc, "e-1", EventPatch(duration="2/3"))
    note = doc.get("e-1", "note")
    assert note.findtext("type") == "quarter" and note.findtext("duration") == "2"
    assert note.findtext("time-modification/actual-notes") == "3"
    assert note.find("notations/tuplet") is not None


def test_explicit_tuplet_normal_type_is_preserved_and_duration_edit_rejected():
    xml = b'<score-partwise><part id="P1"><measure><attributes><divisions>3</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes><normal-type>eighth</normal-type></time-modification></note></measure></part></score-partwise>'
    doc = document(xml)
    with pytest.raises(ReviewError, match="normal-type"):
        patch_event(doc, "e-1", EventPatch(duration="2/3"))
    assert doc.xml() == xml


def test_tied_notation_without_sound_tie_is_exposed_in_model():
    xml = FIXTURE.read_bytes().replace(b'<tie type="start"/>', b'')
    first = events(import_score(document(xml))[0])[0]
    assert first.ties == ["start"]


def test_staff_specific_key_and_meter_changes_retain_other_staff_inheritance():
    xml = b'<score-partwise><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key number="1"><fifths>0</fifths></key><key number="2"><fifths>-1</fifths></key><time number="1"><beats>4</beats><beat-type>4</beat-type></time><time number="2"><beats>3</beats><beat-type>4</beat-type></time><staves>2</staves></attributes><note><rest/><duration>4</duration><type>whole</type></note></measure><measure number="2"><attributes><key number="1"><fifths>2</fifths></key><time number="1"><beats>3</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>3</duration><type>half</type><dot/></note></measure></part></score-partwise>'
    score, _ = import_score(document(xml))
    first, second = score.parts[0].measures
    assert first.expected_duration is None  # Different staff meters require manual review.
    assert second.expected_duration == "3"
    assert {k["staff"]: k["fifths"] for k in second.key_signature} == {"1": "2", "2": "-1"}


def test_display_override_preserves_explicit_cue_and_duration_semantics():
    xml = b'<score-partwise><part id="P1"><measure><attributes><divisions>1</divisions></attributes><note><cue/><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note></measure></part></score-partwise>'
    doc = document(xml)
    assert events(import_score(doc)[0])[0].display_size == "cue"
    patch_event(doc, "e-1", EventPatch(display_size="normal"))
    event = events(import_score(document(doc.xml()))[0])[0]
    assert event.display_size == "normal" and event.duration == "1" and not event.grace
    assert doc.get("e-1", "note").find("cue") is not None
