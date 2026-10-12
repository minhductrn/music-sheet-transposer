"""Direction-only edits retain canonical endpoints and musical content."""
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, patch
from test_review_existing_ties import XML, tie


def without_orientation(contents):
    root = ET.fromstring(contents, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for node in root.findall('.//tied'):
        node.attrib.pop('orientation', None)
    return ET.tostring(root)


@pytest.mark.parametrize('direction,orientation', [('up', 'over'), ('down', 'under')])
def test_direction_preserves_endpoints_content_history_export(workflow, direction, orientation):
    client, service = workflow
    before = tie(client, create(client, XML)).json()
    sidecar = dict(service.store.get(before['id']).document.manual_ties['e-1'])
    after = patch(client, before, 'e-1', tie_direction=direction)
    assert event(after, 'e-1')['tie_direction'] == direction
    assert event(after, 'e-1')['tie_direction_editable']
    assert without_orientation(xml(after)) == without_orientation(xml(before))
    endpoints = ET.fromstring(xml(after)).findall('.//tied')
    assert len(endpoints) == 2 and all(n.get('orientation') == orientation for n in endpoints)
    assert service.store.get(after['id']).document.manual_ties['e-1'] == sidecar
    for identifier in ['e-1', 'e-2']:
        for key, value in event(before, identifier).items():
            if key not in {'tie_direction', 'provenance', 'manual_changes'}:
                assert event(after, identifier)[key] == value, key
        previous_provenance = event(before, identifier)['provenance']
        current_provenance = event(after, identifier)['provenance']
        assert current_provenance.keys() == previous_provenance.keys()
        for key, value in previous_provenance.items():
            if key != 'manual_fields':
                assert current_provenance[key] == value, key
        previous_fields = previous_provenance['manual_fields']
        current_fields = current_provenance['manual_fields']
        expected_fields = set(previous_fields) | ({'tie_direction'} if identifier == 'e-1' else set())
        assert set(current_fields) == expected_fields
        assert len(current_fields) == len(expected_fields)
    exported = service.musicxml(after['id'])
    assert exported == xml(after)
    imported = create(client, exported)
    assert event(imported, 'e-1')['tie_direction'] == direction
    assert event(imported, 'e-1')['tie_target_id'] == 'e-2'
    assert without_orientation(xml(imported)) == without_orientation(exported)
    undone = request(client, after, 'undo').json()
    assert xml(undone) == xml(before)
    redone = request(client, undone, 'redo').json()
    assert xml(redone) == xml(after)
    opposite = 'down' if direction == 'up' else 'up'
    switched = patch(client, redone, 'e-1', tie_direction=opposite)
    assert event(switched, 'e-1')['tie_relationship'] == event(before, 'e-1')['tie_relationship']
    replay = patch(client, switched, 'e-1', tie_direction=opposite)
    assert replay['revision'] == switched['revision']


def test_independent_simultaneous_directions(workflow):
    client, _ = workflow
    current = create(client, XML)
    for anchor in ['e-1', 'e-2']:
        result = request(client, current, 'events', dict(measure_id='m-1', same_onset_id=anchor,
            pitch=dict(step='C', octave=5), voice='1', staff=1, duration='1/2'))
        assert result.status_code == 200, result.text
        current = result.json()
    for source, target in [('e-1', 'e-2'), ('new-1', 'new-2')]:
        current = patch(client, current, source, tie_to_event_id=target)
    before = xml(current)
    owned = event(current, 'new-1')['tie_relationship']
    current = patch(client, current, 'e-1', tie_direction='up')
    assert event(current, 'new-1')['tie_direction'] is None
    current = patch(client, current, 'new-1', tie_direction='down')
    assert event(current, 'e-1')['tie_direction'] == 'up'
    assert event(current, 'new-1')['tie_relationship'] == owned
    assert without_orientation(xml(current)) == without_orientation(before)
    imported = create(client, xml(current))
    directions = [e['tie_direction'] for p in imported['score']['parts'] for m in p['measures']
                  for v in m['voices'] for e in v['events'] if e['tie_relationship']]
    assert sorted(directions) == ['down', 'up']


@pytest.mark.parametrize('fields', [dict(tie_direction='sideways'), dict(tie_direction=None),
    dict(tie_direction='up', tie_to_event_id='e-2'), dict(tie_direction='up', duration='1')])
def test_invalid_direction_request_is_atomic(workflow, fields):
    client, _ = workflow
    before = tie(client, create(client, XML)).json()
    response = request(client, before, 'events/e-1', fields, 'PATCH')
    assert response.status_code == 422
    assert client.get('/api/v1/reviews/' + before['id']).json() == before


@pytest.mark.parametrize('markings', ['', '<tied type="start" number="2"/>',
    '<tied type="start" number="2"/><tied type="start" number="3"/>'])
def test_unresolved_direction_is_atomic(workflow, markings):
    client, _ = workflow
    raw = XML.replace(b'<notations><slur type="start"', ('<notations>' + markings + '<slur type="start"').encode())
    before = create(client, raw)
    assert not event(before, 'e-1')['tie_direction_editable']
    response = request(client, before, 'events/e-1', dict(tie_direction='up'), 'PATCH')
    assert response.status_code == 422
    assert client.get('/api/v1/reviews/' + before['id']).json() == before


def test_imported_unique_attributes_retained_and_editable(workflow):
    client, _ = workflow
    raw = XML.replace(b'<notations><slur type="start"',
        b'<tie type="start"/><notations><tied type="start" number="4" orientation="under" placement="below" color="#123456"/><slur type="start"')
    raw = raw.replace(b'<notations><slur type="stop"',
        b'<tie type="stop"/><notations><tied type="stop" number="4" orientation="under" placement="below" color="#123456"/><slur type="stop"')
    before = create(client, raw)
    assert xml(before) == raw
    assert event(before, 'e-1')['tie_direction'] == 'down'
    after = patch(client, before, 'e-1', tie_direction='up')
    assert without_orientation(xml(after)) == without_orientation(raw)
    assert event(after, 'e-1')['tie_relationship'] is None  # No relationship reconstruction.
    imported = create(client, xml(after))
    assert event(imported, 'e-1')['tie_target_id'] == 'e-2'
    assert event(imported, 'e-1')['tie_direction'] == 'up'
