"""Explicit atomic 3:2 commands on the existing authoritative MusicXML tree."""
from fractions import Fraction
from math import lcm
from xml.etree import ElementTree as ET

from .document import ReviewError, local
from .importer import rational
from .patcher import context, group, put, position_context, duration_patch


def xml_units(value):
    """MusicXML divisions are decimal values, never rational slash strings."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ReviewError('The timing cannot be written as exact MusicXML decimal units.')
    places = max(twos, fives)
    integer = value.numerator * 2 ** (places - twos) * 5 ** (places - fives)
    if not places:
        return str(integer)
    digits = str(abs(integer)).zfill(places + 1)
    return ('-' if integer < 0 else '') + digits[:-places] + '.' + digits[-places:]


def refine_divisions(doc, measure, scale, factor):
    if factor > 1:
        part = doc.parent(measure)
        parents = {child: parent for parent in part.iter() for child in parent}
        for node in part.iter():
            parent = parents.get(node)
            if parent is None:
                continue
            tag = local(node.tag)
            for attribute in ({'note': ('attack', 'release'), 'grace': ('make-time',), 'sound': ('divisions',)}.get(tag, ())):
                if attribute in node.attrib:
                    value = rational(node.attrib[attribute])
                    if value is None:
                        raise ReviewError('Cannot refine invalid MusicXML timing attributes.')
                    node.set(attribute, xml_units(value * factor))
            timing = tag == 'duration' and local(parent.tag) in ('note', 'backup', 'forward', 'figured-bass')
            timing |= tag == 'divisions' and local(parent.tag) == 'attributes'
            timing |= tag == 'offset' and local(parent.tag) in ('direction', 'harmony', 'sound')
            if timing:
                value = rational(node.text.strip() if node.text else None)
                if value is None:
                    raise ReviewError('Cannot refine invalid MusicXML timing units.')
                node.text = xml_units(value * factor)
        scale *= factor
    return scale


def triplet(doc, identifier, request):
    if request.pattern == 'quarter-eighth':
        return mixed_triplet(doc, identifier, request)
    measure = doc.get(request.measure_id, 'measure')
    info, cursor, scale = position_context(doc, request.measure_id)
    base = Fraction(request.base_duration)
    count = request.actual_notes
    effective = base * Fraction(request.normal_notes, count)
    selected = [doc.get(key, 'note') for key in request.event_ids]
    old_span = None
    if selected:
        if len(set(request.event_ids)) != count or any(doc.parent(n) is not measure for n in selected):
            raise ReviewError('Choose three distinct notes in the same measure.')
        indexes = [list(measure).index(n) for n in selected]
        if indexes != list(range(indexes[0], indexes[0] + count)):
            raise ReviewError('Choose three consecutive notes in score order; intervening notation is preserved.')
        events = [context(doc, n)[1] for n in selected]
        if any(e.kind != 'note' or e.grace or e.cue or len(group(doc, n)) != 1
               or e.voice != request.voice or e.staff != request.staff for n, e in zip(selected, events)):
            raise ReviewError('Triplet conversion requires three duration-bearing single notes in the chosen voice and staff.')
        if any(doc.child(n, 'time-modification') is not None or
               any(local(v.tag) == 'tuplet' for v in n.iter()) for n in selected):
            raise ReviewError('Existing tuplet membership must not be guessed. Use explicit deletion and replacement for this group.')
        onset = rational(events[0].onset)
        old_span = sum((rational(e.duration) for e in events), Fraction(0))
        if onset is None or any(rational(b.onset) != rational(a.onset) + rational(a.duration) for a, b in zip(events, events[1:])):
            raise ReviewError('The selected notes do not have a contiguous known timeline.')
        if count * effective > old_span:
            raise ReviewError('The triplet exceeds the selected interval. Delete and choose an explicit unoccupied location instead.')
    else:
        onset = rational(request.onset)
        if onset is None or not 0 <= onset <= 1024:
            raise ReviewError('Choose an explicit nonnegative triplet onset.')
        if request.staff > info.staves:
            raise ReviewError('Staff exceeds the declared staff count.')
        for voice in info.voices:
            for e in voice.events:
                if e.voice == request.voice and not e.grace:
                    start, duration = rational(e.onset), rational(e.duration)
                    if start is None or duration is None:
                        raise ReviewError('Triplet insertion requires known event timing.')
                    if onset < start + duration and start < onset + count * effective:
                        raise ReviewError('The triplet overlaps existing content. Delete the incorrect notes with timing preserved or choose an empty location.')
        gaps = [g for g in info.insertion_gaps if g['voice'] == request.voice and g['staff'] == request.staff
                and rational(g['onset']) <= onset < rational(g['onset']) + rational(g['duration'])]
        if gaps and all(onset + count * effective > rational(g['onset']) + rational(g['duration']) for g in gaps):
            raise ReviewError('The triplet exceeds the selected preserved gap.')
    # Refine integer divisions only when required; scale all timing units in this
    # part together, including later inherited divisions. Musical times do not change.
    factor = lcm((effective * scale).denominator, (base * scale).denominator, (onset * scale).denominator)
    scale = refine_divisions(doc, measure, scale, factor)
    notes = selected
    if not notes:
        notes = []
        for index, pitch in enumerate(request.pitches):
            note = ET.Element(doc.namespace + 'note')
            from .patcher import pitch_patch
            pitch_patch(doc, note, pitch)
            put(doc, note, 'voice', request.voice)
            put(doc, note, 'staff', request.staff)
            notes.append(note)
            doc.refs[f'{identifier}-{index + 1}'] = note
        at = next((i for i, n in enumerate(measure) if local(n.tag) == 'barline' and n.get('location', 'right') == 'right'), len(measure))
        stream = []
        def shift(delta):
            if delta:
                node = ET.Element(doc.namespace + ('forward' if delta > 0 else 'backup'))
                ET.SubElement(node, doc.namespace + 'duration').text = xml_units(abs(delta) * scale)
                stream.append(node)
        shift(onset - cursor)
        stream.extend(notes)
        shift(cursor - onset - effective * count)
        for index, node in enumerate(stream):
            measure.insert(at + index, node)
    for index, note in enumerate(notes):
        # Spell the written value before introducing the effective ratio.
        duration_patch(doc, note, str(base), str(scale))
        put(doc, note, 'duration', xml_units(effective * scale))
        modification = put(doc, note, 'time-modification')
        ET.SubElement(modification, doc.namespace + 'actual-notes').text = str(count)
        ET.SubElement(modification, doc.namespace + 'normal-notes').text = str(request.normal_notes)
        if index in (0, count - 1):
            notations = put(doc, note, 'notations')
            ET.SubElement(notations, doc.namespace + 'tuplet', {'type': 'start' if index == 0 else 'stop', 'number': '1', **({'bracket': 'yes', 'show-number': 'actual' if count == 3 and request.normal_notes == 2 else 'both'} if index == 0 else {})})
    if old_span is not None and old_span != effective * count:
        node = ET.Element(doc.namespace + 'forward')
        ET.SubElement(node, doc.namespace + 'duration').text = xml_units((old_span - effective * count) * scale)
        measure.insert(list(measure).index(notes[-1]) + 1, node)
    doc.manual_changes[request.measure_id] = sorted(set(doc.manual_changes.get(request.measure_id, [])) | {'events', 'triplet'})
    for key, node in doc.refs.items():
        if node in notes:
            doc.manual_changes[key] = sorted(set(doc.manual_changes.get(key, [])) | {'triplet', 'duration'})
    doc.changed = True


def mixed_triplet(doc, identifier, request):
    """Exactly two rhythmic positions: quarter then eighth, both scaled 2/3.

    Insertion creates two two-pitch chords. Conversion accepts complete groups
    of one or two notes, explicitly selected in XML order. No inferred members.
    """
    from .patcher import pitch_patch
    measure = doc.get(request.measure_id, 'measure')
    info, cursor, scale = position_context(doc, request.measure_id)
    selected = [doc.get(key, 'note') for key in request.event_ids]
    old_span = None
    if selected:
        if len(set(request.event_ids)) != len(selected) or any(doc.parent(n) is not measure for n in selected):
            raise ReviewError('Choose distinct notes in the same measure.')
        indexes = [list(measure).index(n) for n in selected]
        if indexes != list(range(indexes[0], indexes[0] + len(selected))):
            raise ReviewError('Select the complete contiguous group in score order; intervening events cannot be changed.')
        groups = []
        for note in selected:
            members = group(doc, note)
            if not groups or members != groups[-1]:
                groups.append(members)
        if len(groups) != 2 or any(not 1 <= len(g) <= 2 for g in groups) or [n for g in groups for n in g] != selected:
            raise ReviewError('Choose both complete rhythmic positions, each a single note or two-note chord. Partial chords are not supported.')
        starts = []
        for members, base in zip(groups, (Fraction(1), Fraction(1, 2))):
            contexts = [context(doc, n)[1] for n in members]
            for note, event in zip(members, contexts):
                if event.kind != 'note' or event.grace or event.cue or event.staff != request.staff or event.voice != request.voice:
                    raise ReviewError('Choose duration-bearing pitched notes in one voice and staff.')
                if doc.child(note, 'time-modification') is not None or any(local(v.tag) == 'tuplet' for v in note.iter()):
                    raise ReviewError('Existing tuplet membership cannot be inferred; use explicit deletion and replacement.')
                if event.onset is None or rational(event.duration) != base or doc.text(note, 'type') != ('quarter' if base == 1 else 'eighth') or doc.children(note, 'dot'):
                    raise ReviewError('Conversion requires an undotted written quarter position followed by an eighth position, with matching member durations.')
            if len({e.onset for e in contexts}) != 1:
                raise ReviewError('Chord members must share their onset.')
            starts.append(rational(contexts[0].onset))
        if starts[1] != starts[0] + 1:
            raise ReviewError('The quarter and eighth positions must be contiguous.')
        onset, old_span = starts[0], Fraction(3, 2)
    else:
        onset = rational(request.onset)
        if onset is None or not 0 <= onset <= 1024 or request.staff > info.staves:
            raise ReviewError('Choose a nonnegative onset and a declared staff.')
        groups = []
        pitch_index = 0
        for index, count in enumerate(request.member_counts):
            members = []
            for offset in range(count):
                note = ET.Element(doc.namespace + 'note')
                pitch_patch(doc, note, request.pitches[pitch_index])
                pitch_index += 1
                if offset:
                    put(doc, note, 'chord')
                put(doc, note, 'voice', request.voice)
                put(doc, note, 'staff', request.staff)
                members.append(note)
            groups.append(members)
        for voice in info.voices:
            for e in voice.events:
                if e.voice == request.voice and not e.grace:
                    start, duration = rational(e.onset), rational(e.duration)
                    if start is None or duration is None:
                        raise ReviewError('Insertion requires known musical timing.')
                    if onset < start + duration and start < onset + 1:
                        raise ReviewError('The triplet overlaps existing content. Delete with timing preserved or choose an unoccupied location.')
        gaps = [g for g in info.insertion_gaps if g['voice'] == request.voice and g['staff'] == request.staff
                and rational(g['onset']) <= onset < rational(g['onset']) + rational(g['duration'])]
        if gaps and all(onset + 1 > rational(g['onset']) + rational(g['duration']) for g in gaps):
            raise ReviewError('The triplet exceeds the preserved gap.')
    for members in groups:
        pitches = [(doc.text(doc.child(n, 'pitch'), 'step'), rational(doc.text(doc.child(n, 'pitch'), 'alter', '0')),
                    doc.text(doc.child(n, 'pitch'), 'octave')) for n in members]
        if len(set(pitches)) != len(pitches):
            raise ReviewError('Shared unison noteheads cannot be identified independently. Choose distinct pitches for this workflow.')
    factor = lcm((scale / 3).denominator, (scale / 2).denominator, (onset * scale).denominator)
    scale = refine_divisions(doc, measure, scale, factor)
    flattened = [n for g in groups for n in g]
    if not selected:
        stream = []
        def shift(delta):
            if delta:
                node = ET.Element(doc.namespace + ('forward' if delta > 0 else 'backup'))
                ET.SubElement(node, doc.namespace + 'duration').text = xml_units(abs(delta) * scale)
                stream.append(node)
        shift(onset - cursor)
        stream.extend(flattened)
        shift(cursor - onset - 1)
        at = next((i for i, n in enumerate(measure) if local(n.tag) == 'barline' and n.get('location', 'right') == 'right'), len(measure))
        for index, node in enumerate(stream):
            measure.insert(at + index, node)
        for index, note in enumerate(flattened):
            doc.refs[f'{identifier}-{index + 1}'] = note
    for index, (members, base) in enumerate(zip(groups, (Fraction(1), Fraction(1, 2)))):
        for note in members:
            duration_patch(doc, note, str(base), str(scale))
            put(doc, note, 'duration', xml_units(base * Fraction(2, 3) * scale))
            modification = put(doc, note, 'time-modification')
            ET.SubElement(modification, doc.namespace + 'actual-notes').text = '3'
            ET.SubElement(modification, doc.namespace + 'normal-notes').text = '2'
        # One boundary per rhythmic position, on its canonical leader only.
        notations = put(doc, members[0], 'notations')
        ET.SubElement(notations, doc.namespace + 'tuplet', {'type': 'start' if index == 0 else 'stop', 'number': '1', **({'bracket': 'yes', 'show-number': 'actual'} if index == 0 else {})})
    if old_span is not None:
        node = ET.Element(doc.namespace + 'forward')
        ET.SubElement(node, doc.namespace + 'duration').text = xml_units((old_span - 1) * scale)
        measure.insert(list(measure).index(flattened[-1]) + 1, node)
    doc.manual_changes[request.measure_id] = sorted(set(doc.manual_changes.get(request.measure_id, [])) | {'events', 'triplet'})
    for key, node in doc.refs.items():
        if node in flattened:
            doc.manual_changes[key] = sorted(set(doc.manual_changes.get(key, [])) | {'triplet', 'duration'})
    doc.changed = True


def preview_selection(doc, revision, identifiers):
    """Read-only canonical validation; reuse the existing engine on a clone."""
    from .models import TripletEdit
    from .importer import import_score
    result = {'revision': revision, 'valid': False, 'noteheads': len(identifiers),
              'positions': 0, 'pattern': None, 'ratio': '3:2', 'command': None}
    def invalid(message):
        return dict(result, explanation=message)
    if not identifiers or len(identifiers) > 4:
        return invalid('Select three consecutive notes or a quarter-and-eighth group.')
    if len(set(identifiers)) != len(identifiers):
        return invalid('Select each notehead only once.')
    score, _ = import_score(doc)
    found = {e.id: (m, e) for p in score.parts for m in p.measures for v in m.voices for e in v.events if e.id in identifiers}
    if len(found) != len(identifiers):
        return invalid('This selection is no longer available. Select the notes again.')
    chosen = [found[key] for key in identifiers]
    result['positions'] = len({(m.id, e.voice, e.staff, e.onset) for m, e in chosen})
    if len({m.id for m, e in chosen}) != 1:
        return invalid('Select notes in the same measure.')
    if len({e.voice for m, e in chosen}) != 1 or len({e.staff for m, e in chosen}) != 1:
        return invalid('Select notes in the same voice and staff.')
    if any(e.kind != 'note' or e.grace or e.cue or e.onset is None or e.staff is None for m, e in chosen):
        return invalid('Select duration-bearing pitched notes with known timing.')
    measure = doc.get(chosen[0][0].id, 'measure')
    index = {n: i for i, n in enumerate(measure)}
    ordered = sorted(identifiers, key=lambda key: (rational(found[key][1].onset), index[doc.get(key, 'note')]))
    selected = [doc.get(key, 'note') for key in ordered]
    selected_set = set(selected)
    if any(any(member not in selected_set for member in group(doc, n)) for n in selected):
        return invalid('Select all notes belonging to this chord.')
    if any(doc.child(n, 'time-modification') is not None or any(local(c.tag) == 'tuplet' for c in n.iter()) for n in selected):
        return invalid('This selection includes an existing tuplet that is not supported for conversion.')
    groups = []
    for n in selected:
        members = group(doc, n)
        if not groups or members != groups[-1]:
            groups.append(members)
    bases = {'whole': '4', 'half': '2', 'quarter': '1', 'eighth': '1/2', '16th': '1/4', '32nd': '1/8', '64th': '1/16'}
    types = [doc.text(g[0], 'type') for g in groups]
    if len(groups) == 3 and all(len(g) == 1 for g in groups) and len(set(types)) == 1 and types[0] in bases:
        base, pattern, label = bases[types[0]], 'equal', 'Three equal notes'
    elif len(groups) == 2 and types == ['quarter', 'eighth'] and all(1 <= len(g) <= 2 for g in groups):
        base, pattern, label = '1', 'quarter-eighth', 'Quarter + eighth'
    else:
        return invalid('This group contains unsupported durations. Select three equal single notes or a quarter-and-eighth group.')
    for members in groups:
        base_value = rational(bases.get(doc.text(members[0], 'type')))
        if any(doc.children(n, 'dot') or rational(found[next(key for key in ordered if doc.refs[key] is n)][1].duration) != base_value for n in members):
            return invalid('This group contains unsupported durations.')
    indexes = [index[n] for n in selected]
    if indexes != list(range(indexes[0], indexes[0] + len(selected))):
        return invalid('These notes are not consecutive; unrelated events intervene.')
    starts = [found[next(key for key in ordered if doc.refs[key] is g[0])][1] for g in groups]
    if any(rational(b.onset) != rational(a.onset) + rational(a.duration) for a, b in zip(starts, starts[1:])):
        return invalid('These notes are not rhythmically contiguous.')
    first = found[ordered[0]]
    command = TripletEdit(measure_id=first[0].id, voice=first[1].voice, staff=first[1].staff,
                          base_duration=base, pattern=pattern, event_ids=ordered)
    try:
        triplet(doc.clone(), 'preview-triplet', command)
    except ReviewError as error:
        return invalid(str(error))
    return dict(result, valid=True, pattern=label, command=command.model_dump(exclude_none=True),
                explanation='Selection validated. Convert this group to triplet 3:2.')
