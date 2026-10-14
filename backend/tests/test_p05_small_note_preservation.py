"""Source-labelled benchmark edits; geometry alone is not a size oracle."""
from base64 import b64decode
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from app.core.config import Settings
from app.music.recovery.service import recover
from app.music.review.document import Document
from app.music.review.importer import import_score
from app.music.review.models import EventPatch
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore
from test_semantic_recovery import archive, XML as SYNTHETIC_XML

RAW = (Path(__file__).parent / 'music/fixtures/p05_synthetic_preservation.musicxml').read_bytes()


def events(score):
    return [e for p in score.parts for m in p.measures for v in m.voices for e in v.events]


def without_size(raw):
    root = ET.fromstring(raw)
    for note in root.findall('.//note'):
        for child in list(note):
            if child.tag == 'type':
                child.attrib.pop('size', None)
            if child.tag == 'notehead' and child.get('font-size') == 'small':
                note.remove(child)
    return ET.tostring(root)


@pytest.mark.parametrize('ids', [('e-3',), ('e-5',), ('e-3', 'e-5'), ('e-31',)])
def test_source_confirmed_size_only_edit_roundtrip_and_history(ids):
    config = Settings()
    service = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    before = service.create(RAW)
    current = before
    original = events(import_score(Document.parse(RAW))[0])
    assert len(original) == 51
    # Independent source labels: upper ta=C5, upper cung=A4, tied upper m8=A4.
    for identifier in ids:
        current = service.event_patch(current['id'], current['revision'], identifier, EventPatch(display_size='small'))
    corrected = b64decode(current['musicxml_base64'])
    parsed = events(import_score(Document.parse(corrected))[0])
    assert len(parsed) == 51
    for old, new in zip(original, parsed):
        assert new.display_size == ('small' if old.id in ids else old.display_size)
        for field in ('id', 'pitch', 'duration', 'onset', 'voice', 'staff', 'chord_id', 'chord_member', 'lyric_ids', 'ties', 'cue', 'grace'):
            assert getattr(new, field) == getattr(old, field)
    # Raw tree oracle also covers independent tie endpoints, slurs, lyrics and stems.
    assert without_size(corrected) == without_size(RAW)
    for _ in ids:
        current = service.history(current['id'], current['revision'], 'undo')
    assert b64decode(current['musicxml_base64']) == RAW
    for _ in ids:
        current = service.history(current['id'], current['revision'], 'redo')
    assert b64decode(current['musicxml_base64']) == corrected
    again = service.event_patch(current['id'], current['revision'], ids[0], EventPatch(display_size='normal'))
    size = {e.id: e.display_size for e in events(import_score(Document.parse(b64decode(again['musicxml_base64'])))[0])}
    assert size[ids[0]] == 'normal'


def test_explicit_native_small_shape_survives_recovery_serialization_and_review():
    # Independent hand-authored graph labels head 11 SMALL and head 10 normal.
    result = recover(SYNTHETIC_XML, archive(), Settings())
    service = ReviewService(MemoryReviewStore(Settings(), lambda: 1000), Settings(), lambda: 1000)
    review = service.create(result.document.xml())
    projected = events(import_score(Document.parse(b64decode(review['musicxml_base64'])))[0])
    notes = [e for e in projected if e.kind == 'note']
    assert [(e.pitch.step, e.pitch.octave, e.display_size, e.onset, e.duration, e.voice, e.staff, e.grace, e.cue) for e in notes] == [
        ('A', 4, 'normal', '0', '1', '1', 1, False, False),
        ('C', 5, 'small', '0', '1', '1', 1, False, False),
    ]
