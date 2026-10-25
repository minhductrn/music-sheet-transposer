"""Synthetic text foundation regressions; no OMR or user artifacts."""
from xml.etree import ElementTree as ET

import pytest
from app.core.config import Settings
from app.music.review.document import ReviewError
from app.music.review.models import ScoreTextAdd, TextPatch
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore
from test_review_api import setup_review

XML = '''<score-partwise xmlns="urn:text" version="4.0"><work><work-title>Work</work-title></work><movement-title>Movement</movement-title><identification><creator type="composer">Tác giả</creator><creator type="lyricist">Lời</creator><rights>Keep</rights></identification><credit page="1"><credit-type>composer</credit-type><credit-words font-size="14">Printed credit</credit-words></credit><part-list><score-part id="P"><part-name>Voice</part-name></score-part></part-list><part id="P"><measure number="1"><attributes><divisions>1</divisions><time><beats>2</beats><beat-type>4</beat-type></time></attributes><direction placement="above"><direction-type><words default-y="20" font-style="italic">ĐK: Xin dâng...</words><words>Keep second segment</words></direction-type><sound tempo="96"/></direction><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type><lyric number="2"><syllabic>single</syllabic><text>Ngài</text></lyric></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>'''.encode()
NS = {'m': 'urn:text'}


@pytest.fixture
def score():
    config = Settings()
    service = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    return service, service.create(XML)


def xml(service, review):
    return service.musicxml(review['id'])


@pytest.mark.parametrize('text_id', ['wt-1', 'mt-1', 'cr-1', 'cr-2', 'c-1', 'w-1'])
def test_edit_preserves_other_text_notation_history_and_roundtrip(score, tmp_path, text_id):
    service, before = score
    value = 'Ngài cũng yêu thương & <Việt>'
    after = service.score_text_patch(before['id'], before['revision'], text_id, TextPatch(text=value))
    changed = xml(service, after)
    original, edited = ET.fromstring(XML), ET.fromstring(changed)
    for path in ['.//m:note', './/m:sound']:
        assert [ET.tostring(n) for n in original.findall(path, NS)] == [ET.tostring(n) for n in edited.findall(path, NS)]
    previous = {t['id']: t for t in before['score']['texts']}
    for t in after['score']['texts']:
        if t['id'] != text_id:
            assert t == previous[t['id']]
    doc = service.store.get(before['id']).document
    if text_id == 'w-1':
        assert doc.refs[text_id].attrib == {'default-y': '20', 'font-style': 'italic'}
    undo = service.history(before['id'], after['revision'], 'undo')
    assert xml(service, undo) == XML
    redo = service.history(before['id'], undo['revision'], 'redo')
    assert xml(service, redo) == changed
    verified = service.verify(before['id'], redo['revision'])
    file = tmp_path / 'canonical.musicxml'
    file.write_bytes(service.musicxml(verified['id'], verified_only=True))
    reopened = service.create(file.read_bytes())
    assert any(t['text'] == value for t in reopened['score']['texts'])
    assert reopened['score']['lyrics'][0]['segments'] == ['Ngài']


@pytest.mark.parametrize('role', ['composer', 'lyricist', 'credit', 'direction'])
def test_add_delete_unicode_text_and_reimport(score, role):
    service, before = score
    created = service.score_text_add(before['id'], before['revision'], ScoreTextAdd(role=role, text='Mới cùng Ngài', event_id='e-2' if role == 'direction' else None))
    item = next(t for t in created['score']['texts'] if t['id'].startswith('new-'))
    assert item['role'] == role
    if role == 'direction':
        assert item['measure_id'] == 'm-1'
        nodes = list(ET.fromstring(xml(service, created)).find('.//m:measure', NS))
        index = next(i for i, n in enumerate(nodes) if n.findtext('m:direction-type/m:words', namespaces=NS) == 'Mới cùng Ngài')
        assert nodes[index + 1].findtext('m:pitch/m:step', namespaces=NS) == 'D'
    reopened = service.create(xml(service, created))
    assert any(t['text'] == 'Mới cùng Ngài' for t in reopened['score']['texts'])
    deleted = service.score_text_delete(created['id'], created['revision'], item['id'])
    assert all(t['text'] != 'Mới cùng Ngài' for t in deleted['score']['texts'])
    assert deleted['score']['lyrics'] == before['score']['lyrics']
    reopened_deleted = service.create(xml(service, deleted))
    assert all(t['text'] != 'Mới cùng Ngài' for t in reopened_deleted['score']['texts'])


@pytest.mark.parametrize('role,tag', [('work_title', 'work-title'), ('movement_title', 'movement-title')])
def test_title_creation_and_deletion_are_independent(score, role, tag):
    service, before = score
    text_id = next(t['id'] for t in before['score']['texts'] if t['role'] == role)
    deleted = service.score_text_delete(before['id'], before['revision'], text_id)
    created = service.score_text_add(before['id'], deleted['revision'], ScoreTextAdd(role=role, text='New title'))
    tree = ET.fromstring(xml(service, created))
    assert tree.findtext('.//m:' + tag, namespaces=NS) == 'New title'
    other = 'movement-title' if tag == 'work-title' else 'work-title'
    assert tree.findtext('.//m:' + other, namespaces=NS) == ('Movement' if other == 'movement-title' else 'Work')


def test_delete_one_words_preserves_sound_and_other_words_but_rejects_orphan_sound(score):
    service, before = score
    after = service.score_text_delete(before['id'], before['revision'], 'w-1')
    saved = xml(service, after)
    assert ET.fromstring(saved).find('.//m:sound', NS).get('tempo') == '96'
    with pytest.raises(ReviewError, match='shares a direction'):
        service.score_text_delete(after['id'], after['revision'], 'w-2')
    assert xml(service, after) == saved


def test_invalid_requests_are_atomic(score):
    service, before = score
    for action in [
        lambda: service.score_text_patch(before['id'], 0, 'w-1', TextPatch(text='stale')),
        lambda: service.score_text_delete(before['id'], 1, 'missing'),
        lambda: service.score_text_add(before['id'], 1, ScoreTextAdd(role='direction', text='No target')),
        lambda: service.score_text_add(before['id'], 1, ScoreTextAdd(role='work_title', text='Duplicate')),
    ]:
        with pytest.raises(ReviewError):
            action()
        assert xml(service, before) == XML


def test_text_api_requires_revision_and_preserves_lyric_parentage(setup_review):
    client, _, _ = setup_review
    review = client.post('/api/v1/reviews', files={'musicxml': ('text.musicxml', XML)}).json()
    path = f'/api/v1/reviews/{review["id"]}/texts/w-1'
    assert client.patch(path, json={'text': 'mới'}).status_code == 428
    updated = client.patch(path, json={'text': 'mới'}, headers={'If-Match': '"1"'})
    assert updated.status_code == 200, updated.text
    assert updated.json()['score']['lyrics'] == review['score']['lyrics']
    assert client.delete(path, headers={'If-Match': '"1"'}).status_code == 409
    created = client.post(f'/api/v1/reviews/{review["id"]}/texts', json={'role': 'direction', 'text': 'Mới', 'event_id': 'e-2'}, headers={'If-Match': '"2"'})
    assert created.status_code == 200, created.text
    new_id = next(t['id'] for t in created.json()['score']['texts'] if t['text'] == 'Mới')
    deleted = client.delete(f'/api/v1/reviews/{review["id"]}/texts/{new_id}', headers={'If-Match': '"3"'})
    assert deleted.status_code == 200, deleted.text
    assert all(t['id'] != new_id for t in deleted.json()['score']['texts'])


def test_add_and_delete_history_restores_complete_text_nodes(score):
    service, before = score
    created = service.score_text_add(before['id'], 1, ScoreTextAdd(role='direction', text='Mới', event_id='e-2'))
    created_xml = xml(service, created)
    new_id = next(t['id'] for t in created['score']['texts'] if t['text'] == 'Mới')
    deleted = service.score_text_delete(before['id'], 2, new_id)
    undo_delete = service.history(before['id'], deleted['revision'], 'undo')
    assert xml(service, undo_delete) == created_xml
    undo_add = service.history(before['id'], undo_delete['revision'], 'undo')
    assert xml(service, undo_add) == XML
    redo_add = service.history(before['id'], undo_add['revision'], 'redo')
    assert xml(service, redo_add) == created_xml
