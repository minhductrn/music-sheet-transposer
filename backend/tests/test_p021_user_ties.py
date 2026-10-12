"""Human endpoint choices and read-only advisory checks, independent of recognition."""
from copy import deepcopy
from xml.etree import ElementTree as ET
import pytest
from test_phase4e_workflow import workflow, create, request, event, xml, verify, patch
from test_review_existing_ties import XML, tie, strip_tie


def snapshot(client, review):
    return client.get('/api/v1/reviews/' + review['id']).json()


def check(client, review):
    response = request(client, review, 'music-check')
    assert response.status_code == 200, response.text
    return response.json()


def third_note(contents=XML):
    root = ET.fromstring(contents, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    measure = root.find('.//measure')
    extra = deepcopy(measure.findall('note')[-1])
    extra.find('pitch/step').text = 'D'
    measure.insert(list(measure).index(measure.find('barline')), extra)
    return ET.tostring(root)


@pytest.mark.parametrize('target', ['e-2', 'e-3'])
def test_user_selects_exact_different_pitch_target_no_substitution_or_property_changes(workflow, target):
    client, service = workflow
    raw = third_note(XML.replace(b'<step>A</step>', b'<step>C</step>', 1))
    before = create(client, raw)
    assert target in event(before,'e-1')['tie_target_ids']
    response = tie(client, before, target)
    assert response.status_code == 200, response.text
    after = response.json()
    assert event(after,'e-1')['tie_target_id'] == target
    assert service.store.get(after['id']).document.manual_ties['e-1']['target'] == target
    assert strip_tie(xml(after)) == strip_tie(raw)
    for identifier in ['e-1','e-2','e-3']:
        for field in ['id','pitch','duration','onset','voice','staff','notated_duration','grace','display_size','lyric_ids','accidental']:
            assert event(after,identifier)[field] == event(before,identifier)[field]
    warning = next(d for d in check(client,after)['diagnostics'] if d['code']=='tie_pitch_mismatch')
    assert warning['category']=='MUSIC_WARNING' and not warning['blocking']
    assert verify(client,after)['state']=='VERIFIED'
    # Numbered visual endpoints retain user pairing on export/re-import, including mismatch.
    imported = create(client,xml(after))
    assert event(imported,'e-1')['tie_target_id']==target
    assert any(d['code']=='tie_pitch_mismatch' for d in check(client,imported)['diagnostics'])


def test_remove_only_chosen_relationship_and_history(workflow):
    client, _ = workflow
    before = create(client, third_note())
    first = tie(client,before).json()
    both = request(client,first,'events/e-2',{'tie_to_event_id':'e-3'},'PATCH').json()
    after = tie(client,both,None).json()
    assert event(after,'e-1')['ties']==[]
    assert event(after,'e-2')['ties']==['start']
    assert event(after,'e-2')['tie_target_id']=='e-3'
    assert event(after,'e-3')['ties']==['stop']
    assert strip_tie(xml(after))==strip_tie(xml(before))
    undo=request(client,after,'undo').json()
    assert xml(undo)==xml(both)
    redo=request(client,undo,'redo').json()
    assert xml(redo)==xml(after)
    undo_second=request(client,both,'undo') # stale revision safely refused
    assert undo_second.status_code==409


def test_creation_one_history_operation_and_exact_undo_redo(workflow):
    client, _=workflow
    before=create(client,XML)
    after=tie(client,before).json()
    assert after['revision']==before['revision']+1
    undo=request(client,after,'undo').json()
    assert xml(undo)==XML and not undo['can_undo']
    redo=request(client,undo,'redo').json()
    assert xml(redo)==xml(after)


@pytest.mark.parametrize('visual', [False,True])
def test_exact_duplicate_selected_endpoint_is_explicitly_deduplicated_and_undoable(workflow, visual):
    client, _=workflow
    original=tie(client,create(client,XML)).json()
    root=ET.fromstring(xml(original))
    source=root.find('.//note')
    parent=source.find('notations') if visual else source
    node=parent.find('tied' if visual else 'tie')
    parent.append(deepcopy(node))
    before=create(client,ET.tostring(root))
    assert any(d['code']=='tie_duplicate' for d in check(client,before)['diagnostics'])
    response=tie(client,before)
    assert response.status_code==200,response.text
    after=response.json()
    source=ET.fromstring(xml(after)).find('.//note')
    assert len(source.findall('tie'))==len(source.findall('notations/tied'))==1
    assert strip_tie(xml(after))==strip_tie(xml(before))
    assert xml(request(client,after,'undo').json())==xml(before)
    # Repeating an already-identical link does not serialize or commit another operation.
    current=snapshot(client,before)
    again=tie(client,current)
    assert again.status_code==200 # duplicate restored by undo, explicitly deduplicated again
    same=again.json(); repeated=tie(client,same)
    assert repeated.status_code==200 and repeated.json()['revision']==same['revision']
    assert snapshot(client,same)['revision']==same['revision']


def test_distinct_relationship_markings_are_preserved_and_explained(workflow):
    client, _=workflow
    raw=XML.replace(b'<notations><slur type="start"',b'<notations><tied type="start" number="1"/><tied type="start" number="2"/><slur type="start"',1)
    before=create(client,raw)
    assert event(before,'e-1')['tie_correction_error'] is None
    result=tie(client,before)
    assert result.status_code==200, result.text
    after=result.json()
    markings=ET.fromstring(xml(after)).find('.//note').findall('notations/tied')
    assert [n.get('number') for n in markings]==['1','2','3']
    assert any(d['code']=='tie_duplicate' and not d['blocking'] for d in check(client,after)['diagnostics'])
    removed=tie(client,after,None).json()
    assert [n.get('number') for n in ET.fromstring(xml(removed)).findall('.//note/notations/tied')]==['1','2']
    assert verify(client,removed)['state']=='VERIFIED'



@pytest.mark.parametrize('target,status', [('missing',404),('m-1',404),('e-1',422)])
def test_invalid_endpoint_is_atomic(workflow,target,status):
    client, _=workflow
    before=create(client,XML)
    assert tie(client,before,target).status_code==status
    assert snapshot(client,before)==before


def test_stale_revision_and_stale_internal_endpoint_fail_safely(workflow):
    client,service=workflow
    before=create(client,XML)
    after=tie(client,before).json()
    assert tie(client,before,None).status_code==409
    session=service.store.get(after['id'])
    session.document.manual_ties['e-1']['target']='missing'
    broken=snapshot(client,after)
    issue=next(d for d in broken['validation']['diagnostics'] if d['code']=='invalid_manual_tie')
    assert issue['blocking'] and issue['category']=='TECHNICAL_ERROR' and not issue['can_confirm_source']
    assert request(client,broken,'verify',{'confirmed_source_comparison':True}).status_code==409
    result=tie(client,broken,None)
    assert result.status_code==409 and snapshot(client,broken)==broken


def test_unresolved_imported_tie_requires_explicit_target_no_guessing(workflow):
    client,_=workflow
    raw=third_note().replace(b'<duration>8</duration>',b'<duration>8</duration><tie type="start"/>',1)
    before=create(client,raw)
    assert event(before,'e-1')['tie_target_id'] is None
    assert tie(client,before,None).status_code==422
    after=tie(client,before,'e-3').json()
    assert event(after,'e-1')['tie_target_id']=='e-3'
    assert event(after,'e-2')['ties']==[]
    assert strip_tie(xml(after))==strip_tie(raw)


@pytest.mark.parametrize('verified',[False,True])
def test_optional_check_is_read_only_for_document_session_history_and_verification(workflow,verified):
    client,service=workflow
    before=create(client,third_note())
    before=tie(client,before,'e-3').json()
    if verified:
        before=verify(client,before)
    session=service.store.get(before['id'])
    history=(len(session.undo),len(session.redo),session.sequence)
    result=check(client,before)
    assert result['revision']==before['revision'] and result['warning_count']>0
    assert snapshot(client,before)==before
    assert (len(session.undo),len(session.redo),session.sequence)==history
    assert request(client,{**before,'revision':before['revision']-1},'music-check').status_code==409


def test_music_warning_can_be_ignored_or_source_confirmed_but_malformed_xml_cannot(workflow):
    client,_=workflow
    before=create(client,third_note())
    check_result=check(client,before)
    warning=next(d for d in check_result['diagnostics'] if d['code']=='measure_overfilled')
    assert warning['severity']=='WARNING' and warning['can_confirm_source'] and not warning['blocking']
    assert verify(client,before)['state']=='VERIFIED'
    current=snapshot(client,before)
    accepted=request(client,current,'diagnostics/confirm-source',{'diagnostic_id':warning['id'],'note':'Matches the printed source.'}).json()
    assert xml(accepted)==xml(before)
    assert next(d for d in check(client,accepted)['diagnostics'] if d['id']==warning['id'])['source_confirmed']
    malformed=create(client,XML.replace(b'<duration>8</duration>',b'<duration>bad</duration>',1))
    technical=next(d for d in check(client,malformed)['diagnostics'] if d['category']=='TECHNICAL_ERROR')
    assert technical['blocking'] and not technical['can_confirm_source']
    assert tie(client,malformed).status_code==422
    assert request(client,malformed,'verify',{'confirmed_source_comparison':True}).status_code==409
    assert xml(snapshot(client,malformed))==xml(malformed)


def test_explicit_target_can_preserve_another_incoming_canonical_relationship(workflow):
    client, service = workflow
    before = create(client, third_note())
    first = tie(client, before, 'e-3').json()
    response = request(client, first, 'events/e-2', {'tie_to_event_id':'e-3'}, 'PATCH')
    assert response.status_code == 200, response.text
    both = response.json()
    assert event(both, 'e-1')['tie_relationship']['target_event_id'] == 'e-3'
    assert event(both, 'e-2')['tie_relationship']['target_event_id'] == 'e-3'
    removed = tie(client, both, None).json()
    assert event(removed, 'e-2')['tie_relationship']['target_event_id'] == 'e-3'
    assert event(removed, 'e-3')['ties'] == ['stop']
    # Ownership transfer survives export/re-import; final removal cleans owned stop.
    imported = create(client, xml(removed))
    final = request(client, imported, 'events/e-2', {'tie_to_event_id':None}, 'PATCH').json()
    assert event(final, 'e-3')['ties'] == []
    assert len(service.store.get(both['id']).document.manual_ties) == 1


def test_missing_source_and_missing_internal_target_data_are_technical(workflow):
    client, service = workflow
    before=create(client,XML)
    assert request(client,before,'events/missing',{'tie_to_event_id':'e-2'},'PATCH').status_code==404
    assert snapshot(client,before)==before
    after=tie(client,before).json()
    del service.store.get(after['id']).document.manual_ties['e-1']['target']
    current=snapshot(client,after)
    assert any(d['code']=='invalid_manual_tie' and d['blocking'] for d in current['validation']['diagnostics'])
    assert request(client,current,'verify',{'confirmed_source_comparison':True}).status_code==409


def test_duplicate_representations_on_unrelated_notes_are_not_normalized(workflow):
    client,_=workflow
    raw=third_note()
    root=ET.fromstring(raw)
    extra=root.findall('.//note')[2]
    for _ in range(2):
        ET.SubElement(extra,'tie',{'type':'start'})
    before=create(client,ET.tostring(root))
    unrelated=ET.tostring(ET.fromstring(xml(before)).findall('.//note')[2])
    after=tie(client,before,'e-2').json()
    assert ET.tostring(ET.fromstring(xml(after)).findall('.//note')[2])==unrelated
    assert any(d['code']=='tie_duplicate' and d['event_id']=='e-3' for d in check(client,after)['diagnostics'])


@pytest.mark.parametrize('attribute', [{'type':'start','number':'99'}, {'type':'unknown'}])
def test_invalid_markup_is_technical_and_check_does_not_repair_it(workflow,attribute):
    client,_=workflow
    root=ET.fromstring(XML)
    ET.SubElement(root.find('.//note/notations'),'tied',attribute)
    before=create(client,ET.tostring(root))
    result=check(client,before)
    issue=next(d for d in result['diagnostics'] if d['code']=='invalid_tie_markup')
    assert issue['category']=='TECHNICAL_ERROR' and issue['blocking'] and not issue['can_confirm_source']
    assert snapshot(client,before)==before
    assert request(client,before,'verify',{'confirmed_source_comparison':True}).status_code==409


def test_conventional_tie_is_not_blocked_by_unrelated_numbered_markings(workflow):
    client,_=workflow
    root=ET.fromstring(XML)
    extra=ET.SubElement(root.find('.//part'),'measure',{'number':'6'})
    note=ET.SubElement(extra,'note')
    ET.SubElement(note,'rest')
    ET.SubElement(note,'duration').text='10'
    notations=ET.SubElement(note,'notations')
    for number in range(1,17):
        ET.SubElement(notations,'tied',{'type':'let-ring','number':str(number)})
    before=create(client,ET.tostring(root))
    after=tie(client,before)
    assert after.status_code==200,after.text
    assert event(after.json(),'e-1')['tie_target_id']=='e-2'
    assert ET.tostring(ET.fromstring(xml(after.json())).findall('.//measure')[1])==ET.tostring(ET.fromstring(xml(before)).findall('.//measure')[1])


def test_nonconventional_pair_reserves_default_number_for_conventional_ties(workflow):
    client,_=workflow
    before=create(client,third_note())
    after=tie(client,before,'e-3').json()
    root=ET.fromstring(xml(after))
    assert root.find('.//note/notations/tied').get('number')!='1'
    assert event(create(client,xml(after)),'e-1')['tie_target_id']=='e-3'

@pytest.mark.parametrize('lyric,markings', [
    ('Mừng', '<tied type="start" number="1"/><tied type="start" number="2"/>'),
    ('Trời', '<tied type="start" number="3" placement="above"/><tied type="start" number="3" placement="below"/>'),
])
def test_browser_representative_distinct_fragments_allow_authoritative_selection(workflow, lyric, markings):
    client, service = workflow
    raw = XML.replace(b'<notations><slur', ('<notations>' + markings + '<slur').encode(), 1)
    raw = raw.replace(b'>one<', ('>' + lyric + '<').encode())
    before = create(client, raw)
    assert event(before, 'e-1')['tie_correction_error'] is None
    response = tie(client, before)
    assert response.status_code == 200, response.text
    after = response.json()
    assert service.store.get(after['id']).document.manual_ties['e-1']['target'] == 'e-2'
    source = ET.fromstring(xml(after)).find('.//note')
    original = ET.fromstring(raw).find('.//note')
    for marking in original.findall('notations/tied'):
        assert any(n.attrib == marking.attrib for n in source.findall('notations/tied'))
    removed = tie(client, after, None).json()
    assert [n.attrib for n in ET.fromstring(xml(removed)).findall('.//note/notations/tied')] == [n.attrib for n in original.findall('notations/tied')]
    assert xml(request(client, removed, 'undo').json()) == xml(after)


def test_browser_recognized_pair_is_not_a_canonical_user_correction(workflow):
    client, service = workflow
    raw = XML.replace(b'<duration>8</duration>', b'<duration>8</duration><tie type="start"/>', 1)
    raw = raw.replace(b'<duration>2</duration>', b'<duration>2</duration><tie type="stop"/>', 1)
    before = create(client, raw)
    response = tie(client, before)
    assert response.status_code == 200, response.text
    after = response.json()
    assert service.store.get(after['id']).document.manual_ties['e-1']['target'] == 'e-2'
    repeated = tie(client, after)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()['revision'] == after['revision']
    assert xml(repeated.json()) == xml(after)


def test_exact_serialization_conflict_reports_number_exhaustion_and_is_atomic(workflow):
    client, _ = workflow
    root = ET.fromstring(XML)
    parent = root.find('.//note/notations')
    for number in range(2, 17):
        ET.SubElement(parent, 'tied', {'type': 'start', 'number': str(number)})
    before = create(client, ET.tostring(root))
    assert event(before, 'e-1')['tie_source_editable']
    result = tie(client, before)
    assert result.status_code == 422
    assert '2–16' in result.json()['detail'] and 'occupied' in result.json()['detail']
    assert snapshot(client, before) == before


def test_missing_owned_visual_endpoint_is_repaired_instead_of_false_noop(workflow):
    client, service = workflow
    before = tie(client, create(client, XML)).json()
    doc = service.store.get(before['id']).document
    parent = doc.refs['e-2'].find('notations')
    parent.remove(parent.find('tied'))
    broken = snapshot(client, before)
    assert any(d['code'] == 'invalid_manual_tie' for d in broken['validation']['diagnostics'])
    response = tie(client, broken)
    assert response.status_code == 200, response.text
    after = response.json()
    assert after['revision'] == before['revision'] + 1
    assert event(after, 'e-1')['tie_relationship']['target_event_id'] == 'e-2'
    assert not any(d['code'] == 'invalid_manual_tie' for d in after['validation']['diagnostics'])
    assert len(ET.fromstring(xml(after)).find('.//note').findall('notations/tied')) == 1


def test_duplicated_export_identity_on_distinct_notes_is_not_promoted_as_canonical(workflow):
    client, service = workflow
    first = tie(client, create(client, XML)).json()
    root = ET.fromstring(xml(first))
    notes = root.findall('.//note')
    ET.SubElement(notes[1].find('notations'), 'tied', dict(notes[0].find('notations/tied').attrib))
    imported = create(client, ET.tostring(root))
    assert service.store.get(imported['id']).document.manual_ties == {}
    assert event(imported, 'e-1')['tie_relationship'] is None
    response = tie(client, imported)
    assert response.status_code == 200, response.text
    assert event(response.json(), 'e-1')['tie_relationship']['target_event_id'] == 'e-2'
