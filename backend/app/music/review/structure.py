"""Read-only XML-bound structure. Theory reports conflicts; it never repairs XML."""
from copy import deepcopy
from fractions import Fraction

from .document import local


def project_structure(doc, score):
    pages, systems = [], []
    for part in score.parts:
        clefs = {}
        staff_ids = {}
        page, system = None, None
        scale = None
        has_breaks = any(p.get('new-system') == 'yes' or p.get('new-page') == 'yes'
                         for m in part.measures for p in doc.children(doc.refs[m.id], 'print'))
        for measure in part.measures:
            node = doc.refs[measure.id]
            context_changes = []
            cursor = Fraction(0)
            events_by_node = {doc.refs[e.id]: e for v in measure.voices for e in v.events}
            for child in node:
                tag = local(child.tag)
                if tag == 'attributes':
                    raw = doc.text(child, 'divisions')
                    if raw:
                        try:
                            scale = Fraction(raw)
                        except (ValueError, ZeroDivisionError):
                            scale = None
                    for name in ('clef', 'time', 'key'):
                        for value in doc.children(child, name):
                            entry = {'id': f'{measure.id}:context:{len(context_changes)}', 'measure_id': measure.id,
                                     'origin': 'RECOGNITION_INTERPRETATION',
                                     'kind': name, 'staff': value.get('number'),
                                     'onset': str(cursor) if measure.actual_duration is not None else None,
                                     'attributes': dict(value.attrib),
                                     'fields': [{'name': local(v.tag), 'text': v.text, 'attributes': dict(v.attrib)} for v in value]}
                            context_changes.append(entry)
                            if name == 'clef':
                                clefs[value.get('number', '1')] = entry
                elif tag in ('backup', 'forward') and scale:
                    try:
                        cursor += Fraction(doc.text(child, 'duration')) / scale * (-1 if tag == 'backup' else 1)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
                elif tag == 'note':
                    event = events_by_node.get(child)
                    if event:
                        event.measure_id = measure.id
                        event.clef = deepcopy(clefs.get(str(event.staff)))
                        event.accidental = {'text': doc.text(child, 'accidental'),
                                            'attributes': dict(doc.child(child, 'accidental').attrib) if doc.child(child, 'accidental') is not None else {}}
                        event.notated_duration = {'type': doc.text(child, 'type'), 'dots': len(doc.children(child, 'dot')),
                                                 'time_modification': [{ 'name': local(v.tag), 'text': v.text} for v in doc.child(child, 'time-modification')] if doc.child(child, 'time-modification') is not None else []}
                        if not event.grace and not event.chord_member and event.onset is not None and event.duration is not None:
                            cursor = Fraction(event.onset) + Fraction(event.duration)
                            scale = Fraction(event.divisions) if event.divisions else scale
            measure.context_changes = context_changes
            measure.clefs = deepcopy(list(clefs.values()))
            measure.barlines = [{'id': f'{measure.id}:barline:{i}', 'measure_id': measure.id, 'location': b.get('location', 'right'), 'style': doc.text(b, 'bar-style'),
                                 'repeat': dict(doc.child(b, 'repeat').attrib) if doc.child(b, 'repeat') is not None else None}
                                for i, b in enumerate(doc.children(node, 'barline'))]
            measure.partial = {'implicit': node.get('implicit') == 'yes', 'intent': 'EXPLICIT_PARTIAL' if node.get('implicit') == 'yes' else 'UNKNOWN'}
            measure.meter_context = []
            for signature in measure.time_signature:
                pairs = signature['pairs']
                groups = []
                for pair in pairs:
                    try:
                        beats, denominator = int(pair['beats']), int(pair['beat_type'])
                    except (ValueError, TypeError):
                        continue
                    compound = denominator == 8 and beats > 3 and beats % 3 == 0
                    groups.append({'numerator': beats, 'denominator': denominator,
                                   'subdivision_quarters': str(Fraction(4, denominator)) if denominator > 0 else None,
                                   'compound': compound, 'pulse_count': beats // 3 if compound else beats,
                                   'pulse_quarters': str(Fraction(12 if compound else 4, denominator)) if denominator > 0 else None})
                measure.meter_context.append({'staff': signature['staff'], 'pairs': deepcopy(pairs), 'groups': groups})
            expected, actual = measure.expected_duration, measure.actual_duration
            if expected is None or actual is None:
                state = 'STRUCTURALLY_AMBIGUOUS'
            elif Fraction(actual) > Fraction(expected):
                state = 'OVERFILLED'
            elif Fraction(actual) < Fraction(expected):
                state = 'PARTIAL' if measure.partial['implicit'] else 'UNDERFILLED'
            else:
                state = 'VALID'
            measure.rhythm_status = state
            measure.conflict_state = 'CONFLICT' if state in ('OVERFILLED', 'UNDERFILLED', 'STRUCTURALLY_AMBIGUOUS') else 'NONE'
            for staff in range(1, measure.staves + 1):
                staff_ids[staff] = {'id': f'{part.id}:staff:{staff}', 'number': staff}
            # Only explicit print instructions create source-review layout groups.
            prints = doc.children(node, 'print')
            new_page = any(p.get('new-page') == 'yes' for p in prints)
            new_system = new_page or any(p.get('new-system') == 'yes' for p in prints)
            if new_system or (has_breaks and system is None):
                if page is None or new_page:
                    page = {'id': f'{part.id}:xml-page:{len(pages)}', 'part_id': part.id, 'system_ids': [], 'origin': 'RECOGNITION_INTERPRETATION'}
                    pages.append(page)
                system = {'id': f'{part.id}:xml-system:{len(systems)}', 'page_id': page['id'], 'part_id': part.id,
                          'measure_ids': [], 'origin': 'RECOGNITION_INTERPRETATION', 'explicit_break_measure_id': measure.id,
                          'new_page': new_page}
                systems.append(system)
                page['system_ids'].append(system['id'])
            if system is not None:
                system['measure_ids'].append(measure.id)
        part.staffs = list(staff_ids.values())
    score.pages, score.systems = pages, systems
    score.layout = {'mode': 'SOURCE_REVIEW' if systems else 'RESPONSIVE', 'origin': 'MUSICXML_PRINT' if systems else None,
                    'systems': systems, 'geometry_available': False}
    score.schema_version = '4F.1'
    return score


def source_layout(score, evidence):
    """Bind complete ordered source measure lists only; uncertain lists stay evidence."""
    if score.systems:  # Explicit MusicXML breaks already provide review organization.
        return
    for archive in evidence:
        if archive['diagnostics'] or len(archive['logical_parts']) != len(score.parts):
            continue
        groups = []
        for logical, part in zip(archive['logical_parts'], score.parts):
            source_groups = [(sheet, system, [m for m in system['measures'] if m['part'] == logical])
                             for sheet in archive['sheets'] for system in sheet['systems']]
            source_groups = [(s, sys, ms) for s, sys, ms in source_groups if ms]
            observed = [m['id'] for _, _, ms in source_groups for m in ms]
            numbers = [m.number for m in part.measures]
            if observed != numbers or len(set(numbers)) != len(numbers):
                groups = []
                break
            by_number = {m.number: m.id for m in part.measures}
            previous_page = None
            for sheet, system, measures in source_groups:
                groups.append({'id': f"{archive['sha256']}:{sheet['number']}:{system['page_id']}:{system['id']}:{part.id}",
                               'part_id': part.id, 'measure_ids': [by_number[m['id']] for m in measures],
                               'explicit_break_measure_id': by_number[measures[0]['id']],
                               'new_page': previous_page is not None and previous_page != (sheet['number'], system['page_id']), 'origin': 'SOURCE_OBSERVATION',
                               'sheet': sheet['number'], 'source_page_id': system['page_id'],
                               'binding': 'ORDERED_RECOGNITION_MATCH'})
                previous_page = (sheet['number'], system['page_id'])
        if groups:
            source_pages = {}
            for group in groups:
                page_id = f"{archive['sha256']}:{group['sheet']}:{group['source_page_id']}:{group['part_id']}"
                group['page_id'] = page_id
                source_pages.setdefault(page_id, {'id': page_id, 'part_id': group['part_id'],
                                                   'sheet': group['sheet'], 'source_page_id': group['source_page_id'],
                                                   'origin': 'SOURCE_OBSERVATION', 'system_ids': []})['system_ids'].append(group['id'])
            score.pages, score.systems = list(source_pages.values()), groups
            score.layout = {'mode': 'SOURCE_REVIEW', 'origin': 'OMR_ORDERED_MEASURES', 'systems': groups,
                            'geometry_available': any(m.get('left') is not None and m.get('right') is not None
                                                      for sh in archive['sheets'] for sy in sh['systems'] for m in sy['measures'])}
            return
