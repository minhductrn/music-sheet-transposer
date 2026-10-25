"""Atomic note/whole-chord replacement. Construction/timing belong to triplets.py."""
from dataclasses import asdict
from fractions import Fraction

from .document import ReviewError, local
from .importer import import_score, rational
from .models import TripletEdit
from .patcher import delete_preserving_timing, group, position_context
from .triplets import triplet

BASE_NAMES = {'4': 'whole', '2': 'half', '1': 'quarter', '1/2': 'eighth',
              '1/4': 'sixteenth', '1/8': 'thirty-second', '1/16': 'sixty-fourth'}


def target_context(doc, identifier):
    note = doc.get(identifier, 'note')
    score, _ = import_score(doc)
    for part in score.parts:
        for measure in part.measures:
            for voice in measure.voices:
                for event in voice.events:
                    if event.id == identifier:
                        return note, measure, event, score
    raise ReviewError('This note is no longer available. Select it again.')


def resolve_members(doc, note, measure, event, score):
    """Only canonical XML adjacency/chord IDs establish a rhythmic position."""
    nodes = group(doc, note)
    if note not in nodes or len(nodes) > 3 or doc.child(nodes[0], 'chord') is not None:
        raise ReviewError('The selected chord cannot be identified safely. Only single notes and complete two- or three-note chords are supported.')
    by_node = {doc.refs[e.id]: e for p in score.parts for m in p.measures if m.id == measure.id for v in m.voices for e in v.events}
    members = [(node, by_node.get(node)) for node in nodes]
    leader = members[0][1]
    if leader is None or any(e is None for _, e in members):
        raise ReviewError('The selected chord cannot be identified safely.')
    expected_ids = {e.id for _, e in members}
    if len(nodes) > 1:
        canonical_ids = {e.id for e in by_node.values() if e.chord_id == leader.id}
        if canonical_ids != expected_ids or any(
            e.kind != 'note' or e.pitch is None or e.grace or e.cue or
            (e.voice, e.staff, e.onset, e.duration, e.chord_id) !=
            (leader.voice, leader.staff, leader.onset, leader.duration, leader.id)
            for _, e in members
        ):
            raise ReviewError('The selected chord cannot be identified safely: its members must share one voice, staff, onset and effective duration.')
        pitches = {(e.pitch.step, rational(e.pitch.alter), e.pitch.octave) for _, e in members}
        if len(pitches) != len(members):
            raise ReviewError('The selected chord has ambiguous unison noteheads and cannot be identified safely.')
    elif event.chord_id is not None:
        raise ReviewError('The selected chord cannot be identified safely.')
    return members


def supported_target(doc, identifier, note, measure, event, score):
    if event.grace or event.cue:
        raise ReviewError('Grace and cue notes are not supported for single-note replacement.')
    if event.kind != 'note' or not event.pitch or event.staff is None:
        raise ReviewError('Replace with Triplet requires one duration-bearing pitched note.')
    if doc.child(note, 'time-modification') is not None or any(local(n.tag) == 'tuplet' for n in note.iter()):
        raise ReviewError('This note already belongs to a tuplet. Nested replacement is not supported.')
    # No guessing about which new member receives an association or custom notation.
    allowed = {'pitch', 'duration', 'voice', 'type', 'dot', 'accidental', 'stem', 'staff', 'chord'}
    if any(local(n.tag) not in allowed for n in note) or any(local(k) not in {'default-x', 'default-y', 'relative-x', 'relative-y'} for k in note.attrib):
        tags = {local(n.tag) for n in note.iter()}
        affected = 'lyrics' if 'lyric' in tags else 'ties' if tags & {'tie', 'tied'} else 'slurs' if 'slur' in tags else 'notation'
        raise ReviewError(f'This note or chord contains {affected} associations that require an explicit editing decision. No replacement was made.')
    if any(identifier == source or identifier == link.get('target') for source, link in doc.manual_ties.items()):
        raise ReviewError('This note has a tie association. Resolve it explicitly before replacement; no tie will be reassigned automatically.')
    xml_measure = doc.get(measure.id, 'measure')
    if any(local(n.tag) in {'link', 'bookmark'} for n in xml_measure.iter()):
        raise ReviewError('This measure contains link/bookmark associations that cannot be remapped safely by single-note replacement.')
    # Detect an enclosing preserved tuplet even if its interior note lacks ratio markup.
    by_node = {doc.refs[e.id]: e for p in score.parts for m in p.measures for v in m.voices for e in v.events}
    part = doc.parent(xml_measure)
    active = set()
    for n in part.iter(doc.namespace + 'note'):
        other = by_node.get(n)
        if other is None:
            continue
        lane = (other.voice, other.staff)
        if n is note and any(key[:2] == lane for key in active):
            raise ReviewError('This note is inside an existing tuplet. Nested replacement is not supported.')
        for marker in n.iter(doc.namespace + 'tuplet'):
            key = (*lane, marker.get('number', '1'))
            if marker.get('type') == 'start':
                active.add(key)
            elif marker.get('type') == 'stop':
                active.discard(key)
        if n is note:
            break
    position_context(doc, measure.id)  # Established exact XML cursor/context guards.
    duration, onset = rational(event.duration), rational(event.onset)
    if duration is None or duration <= 0 or onset is None:
        raise ReviewError('This note does not have a known positive canonical interval.')
    return duration, onset


def replacement_options(doc, revision, identifier):
    result = dict(revision=revision, eligible=False, original=None, patterns=[], explanation='')
    try:
        note, measure, event, score = target_context(doc, identifier)
        members = resolve_members(doc, note, measure, event, score)
        leader = members[0][1]
        duration, onset = rational(leader.duration), rational(leader.onset)
        result['original'] = dict(pitch=asdict(leader.pitch) if leader.pitch else None, duration=leader.duration,
                                  start=leader.onset, end=str(onset + duration) if onset is not None and duration is not None else None,
                                  member_count=len(members), members=[dict(id=e.id, pitch=asdict(e.pitch) if e.pitch else None) for _, e in members])
        for node, member in members:
            supported_target(doc, member.id, node, measure, member, score)
        base = str(duration / 2)
        if base in BASE_NAMES:
            result['patterns'].append(dict(id='equal', label=f'Three equal {BASE_NAMES[base]} notes', base_duration=base))
        if duration == 1:
            result['patterns'].append(dict(id='quarter-eighth', label='Quarter + eighth', base_duration='1'))
        if not result['patterns']:
            raise ReviewError('No supported triplet pattern fits this interval exactly. A different interval requires Replace Selected Rhythmic Range, which is not part of this task.')
        result.update(eligible=True, explanation='Choose a pattern and every pitch. The replacement must fit this interval exactly.')
    except ReviewError as error:
        result['explanation'] = str(error)
    return result


def event_signature(event):
    # Divisions refinement changes only numeric encoding, not musical semantics.
    return {key: value for key, value in asdict(event).items() if key not in {'divisions', 'duration_units'}}


def replace_single(doc, new_id, identifier, request):
    if request.preserve_associations:
        return preserve_mixed(doc, new_id, identifier, request)
    options = replacement_options(doc, 0, identifier)
    if not options['eligible']:
        raise ReviewError(options['explanation'])
    choice = next((p for p in options['patterns'] if p['id'] == request.pattern), None)
    if choice is None:
        raise ReviewError('This pattern does not fit the selected interval exactly. A different interval requires Replace Selected Rhythmic Range.')
    note, measure, selected, before = target_context(doc, identifier)
    members = resolve_members(doc, note, measure, selected, before)
    original = members[0][1]
    original_ids = {e.id for _, e in members}
    confirmed = request.original_member_ids
    if (len(members) > 1 and confirmed is None) or (confirmed is not None and confirmed != [e.id for _, e in members]):
        raise ReviewError('Review and confirm every original chord member before replacing the entire chord.')
    xml_measure = doc.get(measure.id, 'measure')
    original_children = list(xml_measure)
    index = original_children.index(members[0][0])
    start, duration = rational(original.onset), rational(original.duration)
    command = TripletEdit(measure_id=measure.id, voice=original.voice, staff=original.staff,
                          onset=original.onset, pattern=request.pattern, base_duration=choice['base_duration'],
                          member_counts=request.member_counts, pitches=request.pitches)
    # Reuse deletion's verified gap and the existing triplet builder on this
    # transaction's clone. Nothing is stored or put on history between these steps.
    for _, member in reversed(members):
        delete_preserving_timing(doc, member.id)
    gap = list(xml_measure)[index]
    before_insert = set(xml_measure)
    triplet(doc, new_id, command)
    created = [doc.refs[f'{new_id}-{i + 1}'] for i in range(len(request.pitches))]
    generated = [n for n in xml_measure if n not in before_insert]
    if set(n for n in generated if local(n.tag) == 'note') != set(created) or any(local(n.tag) not in {'note', 'backup', 'forward'} for n in generated):
        raise ReviewError('The replacement structure could not be isolated safely. No changes applied.')
    # Commit a local splice, not the builder's temporary isolated cursor stream:
    # only the original note is exchanged for new notes at that exact XML position.
    for n in generated:
        xml_measure.remove(n)
    xml_measure.remove(gap)
    for offset, n in enumerate(created):
        xml_measure.insert(index + offset, n)
    expected_children = original_children[:index] + created + original_children[index + len(members):]
    if list(xml_measure) != expected_children:
        raise ReviewError('Replacement would modify unrelated score structure. No changes applied.')
    after, _ = import_score(doc)
    old_events = {e.id: e for p in before.parts for m in p.measures for v in m.voices for e in v.events}
    new_events = {e.id: e for p in after.parts for m in p.measures for v in m.voices for e in v.events}
    if original_ids.intersection(new_events) or set(new_events) != (set(old_events) - original_ids) | {f'{new_id}-{i + 1}' for i in range(len(created))}:
        raise ReviewError('Replacement could not preserve canonical note identities.')
    for key, old in old_events.items():
        if key not in original_ids and event_signature(new_events[key]) != event_signature(old):
            raise ReviewError('Replacement would change an unrelated note or onset. No changes applied.')
    added = [new_events[f'{new_id}-{i + 1}'] for i in range(len(created))]
    if min(rational(e.onset) for e in added) != start or max(rational(e.onset) + rational(e.duration) for e in added) != start + duration or sum((rational(e.duration) for e in added if not e.chord_member), Fraction(0)) != duration:
        raise ReviewError('The replacement does not occupy the original interval exactly.')
    if before.lyrics != after.lyrics or before.texts != after.texts or before.harmonies != after.harmonies:
        raise ReviewError('Replacement would change an unrelated text or lyric association.')
    # Reuse the established technical timeline checks on the final local splice.
    position_context(doc, measure.id)
    for removed in original_ids:
        doc.manual_changes[removed] = sorted(set(doc.manual_changes.get(removed, [])) | {'deletion', 'triplet_replacement'})
    return options


def preview_replacement(doc, revision, identifier, request):
    if request.preserve_associations:
        result=dict(revision=revision,valid=False,eligible=False,fits_exactly=False,ratio='3:2',positions=2)
        try:
            result.update(preserve_mixed(doc.clone(),'preview-preserved',identifier,request))
            result.update(valid=True,fits_exactly=True,explanation='Original identities and associations stay on the first position.')
        except ReviewError as error:result['explanation']=str(error)
        return result
    result = replacement_options(doc, revision, identifier)
    result.update(valid=False, fits_exactly=False, ratio='3:2', proposed_duration=None,
                  positions=3 if request.pattern == 'equal' else 2,
                  noteheads_per_position=[1, 1, 1] if request.pattern == 'equal' else list(request.member_counts),
                  replacement_pitches=[p.model_dump() for p in request.pitches])
    if not result['eligible']:
        return result
    try:
        replace_single(doc.clone(), 'preview-replacement', identifier, request)
        result.update(valid=True, fits_exactly=True, proposed_duration=result['original']['duration'],
                      explanation='Validated: the replacement fits the original interval exactly.')
    except ReviewError as error:
        result['explanation'] = str(error)
    return result


def preserve_mixed(doc, new_id, identifier, request):
    """Opt-in: keep original first-position nodes/IDs/associations; append only the tail."""
    from copy import deepcopy
    from math import lcm
    from xml.etree import ElementTree as ET
    from .patcher import put, pitch_patch, duration_patch
    from .triplets import refine_divisions
    note, measure, event, before = target_context(doc, identifier)
    members = resolve_members(doc, note, measure, event, before)
    first_count, tail_count = request.member_counts
    if request.pattern != 'quarter-eighth' or first_count != len(members) or len(members) > 2:
        raise ReviewError('Preserving associations requires the complete original single/two-note chord in the first position.')
    if request.original_member_ids != [e.id for _, e in members]:
        raise ReviewError('Confirm every original note identity before conversion.')
    for (node, member), pitch in zip(members, request.pitches):
        if member.kind != 'note' or member.grace or member.cue or rational(member.duration) != 1:
            raise ReviewError('Choose an ordinary one-quarter-beat note or complete chord.')
        if doc.child(node,'time-modification') is not None or doc.children(node,'beam') or any(local(n.tag)=='tuplet' for n in node.iter()):
            raise ReviewError('Existing rhythmic groups cannot be nested or overwritten.')
        if (member.pitch.step, rational(member.pitch.alter), member.pitch.octave) != (pitch.step, rational(pitch.alter), pitch.octave):
            raise ReviewError('The original first-position pitches must stay unchanged when preserving associations.')
    # An unmarked interior of a surrounding tuplet is also ambiguous.
    active=set(); selected_nodes={n for n,_ in members}
    part=doc.parent(doc.get(measure.id,'measure'))
    for n in part.iter(doc.namespace+'note'):
        if n in selected_nodes and active: raise ReviewError('The original note lies inside an existing tuplet.')
        for marker in n.iter(doc.namespace+'tuplet'):
            key=marker.get('number','1')
            if marker.get('type')=='start': active.add(key)
            elif marker.get('type')=='stop': active.discard(key)
        if n is members[-1][0]: break
    _,_,scale=position_context(doc,measure.id)
    old_events={e.id:e for p in before.parts for m in p.measures for v in m.voices for e in v.events}
    old_ids={e.id for _,e in members}
    old_manual_ties=deepcopy(doc.manual_ties)
    xml_measure=doc.get(measure.id,'measure')
    scale=refine_divisions(doc,xml_measure,scale,lcm((scale/3).denominator,(scale/2).denominator))
    tails=[]
    for i,pitch in enumerate(request.pitches[first_count:]):
        node=ET.Element(doc.namespace+'note');pitch_patch(doc,node,pitch)
        if i:put(doc,node,'chord')
        for instrument in doc.children(members[0][0],'instrument'):node.append(deepcopy(instrument))
        put(doc,node,'voice',event.voice);put(doc,node,'staff',event.staff)
        tails.append(node);doc.refs[f'{new_id}-tail-{i+1}']=node
    if len({(p.step,rational(p.alter),p.octave) for p in request.pitches[first_count:]}) != tail_count:
        raise ReviewError('Tail chord pitches must be distinct.')
    for position,nodes in enumerate(([n for n,_ in members],tails)):
        for node in nodes:
            modification=put(doc,node,'time-modification')
            ET.SubElement(modification,doc.namespace+'actual-notes').text='3'
            ET.SubElement(modification,doc.namespace+'normal-notes').text='2'
            duration_patch(doc,node,'2/3' if position==0 else '1/3',str(scale))
        notation=put(doc,nodes[0],'notations')
        used={n.get('number','1') for n in part.iter(doc.namespace+'tuplet')}
        # Same fresh lane for both boundaries, without changing existing notation.
        if position==0: number=next(str(n) for n in range(1,10001) if str(n) not in used)
        ET.SubElement(notation,doc.namespace+'tuplet',{'type':'start' if position==0 else 'stop','number':number,**({'bracket':'yes','show-number':'actual'} if position==0 else {})})
    index=list(xml_measure).index(members[-1][0])+1
    for i,node in enumerate(tails):xml_measure.insert(index+i,node)
    doc.changed=True
    after,_=import_score(doc);new_events={e.id:e for p in after.parts for m in p.measures for v in m.voices for e in v.events}
    added={f'{new_id}-tail-{i+1}' for i in range(tail_count)}
    if set(new_events)!=set(old_events)|added or doc.manual_ties!=old_manual_ties:
        raise ReviewError('Conversion could not preserve original identities and tie endpoints.')
    for key,old in old_events.items():
        if key not in old_ids and event_signature(old)!=event_signature(new_events[key]):
            raise ReviewError('Conversion would change an unrelated note or onset.')
    if before.lyrics!=after.lyrics or before.texts!=after.texts or before.harmonies!=after.harmonies:
        raise ReviewError('Conversion would change a text or lyric association.')
    position_context(doc,measure.id)
    for key in old_ids|added:doc.manual_changes[key]=sorted(set(doc.manual_changes.get(key,[]))|{'triplet','duration'})
    return {'eligible':True,'preserved_original_ids':sorted(old_ids)}
