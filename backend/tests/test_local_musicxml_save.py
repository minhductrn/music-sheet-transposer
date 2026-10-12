"""A saved local file survives a fresh temporary backend; no server score repository."""
from base64 import b64decode
from xml.etree import ElementTree as ET

import pytest

from app.core.config import Settings
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore
from test_phase4e_workflow import workflow, create, patch, request, verify, event
from test_review_existing_ties import XML


@pytest.mark.parametrize('direction', ['up', 'down'])
def test_saved_file_reopens_after_backend_restart_without_omr(workflow, tmp_path, direction, monkeypatch):
    client, old_service = workflow
    current = create(client, XML)
    for identifier in ['e-1', 'e-2']:
        current = patch(client, current, identifier, pitch={'step': 'C', 'octave': 4})
    added = request(client, current, 'events', {
        'measure_id': 'm-1', 'same_onset_id': 'e-1', 'pitch': {'step': 'E', 'octave': 4},
        'duration': '1', 'voice': '1', 'staff': 1,
    })
    assert added.status_code == 200, added.text
    current = added.json()
    current = patch(client, current, 'e-1', tie_to_event_id='e-2')
    current = patch(client, current, 'e-1', tie_direction=direction)
    lyric_id = event(current, 'e-1')['lyric_ids'][0]
    lyric = request(client, current, f'lyrics/{lyric_id}', {'text': 'Cùng đem tin mừng'}, 'PATCH')
    assert lyric.status_code == 200, lyric.text
    saved = verify(client, lyric.json())
    exported = client.get(f'/api/v1/reviews/{saved["id"]}/musicxml?verified_only=true')
    assert exported.status_code == 200
    local_file = tmp_path / 'concert.musicxml'
    local_file.write_bytes(exported.content)
    original_bytes = local_file.read_bytes()
    root = ET.fromstring(original_bytes)
    assert len(root.findall('.//note')) == 3
    assert root.find('.//chord') is not None
    assert 'Cùng đem tin mừng' in original_bytes.decode()
    assert all(t.get('orientation') == ('over' if direction == 'up' else 'under') for t in root.findall('.//tied'))
    endpoint_ids = [t.get('id') for t in root.findall('.//tied')]
    unsaved = patch(client, saved, 'e-1', display_size='small')
    assert unsaved['state'] != 'VERIFIED'
    assert local_file.read_bytes() == original_bytes
    old_service.delete(saved['id'])
    from app.music.recovery import service as recovery
    monkeypatch.setattr(recovery, 'recover', lambda *a, **k: pytest.fail('Open must not rerun recognition'))
    config = Settings()
    fresh_backend = ReviewService(MemoryReviewStore(config, lambda: 1000), config, lambda: 1000)
    reopened = fresh_backend.create(local_file.read_bytes())
    assert b64decode(reopened['musicxml_base64']) == original_bytes
    assert reopened['semantic_recovery'] is None
    assert reopened['state'] != 'VERIFIED'  # Open is not implicit confirmation.
    source = next(e for p in reopened['score']['parts'] for m in p['measures'] for v in m['voices']
                  for e in v['events'] if e['tie_relationship'])
    assert source['tie_direction'] == direction
    assert source['pitch']['step'] == 'C'
    assert source['tie_relationship']['source_visual_id'] == endpoint_ids[0]
    assert source['tie_relationship']['target_visual_id'] == endpoint_ids[1]
    assert fresh_backend.musicxml(reopened['id']) == original_bytes
