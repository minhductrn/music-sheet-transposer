"""Bounded explicit same-part/voice/staff slurs; XML owns endpoint identity."""
from collections import defaultdict
from fractions import Fraction
from xml.etree import ElementTree as ET
from .document import ReviewError
from .importer import import_score


def pairs(doc):
    score, _ = import_score(doc)
    grouped = defaultdict(list)
    for part in score.parts:
        for measure in part.measures:
            for voice in measure.voices:
                for event in voice.events:
                    note = doc.refs[event.id]
                    for notations in doc.children(note, "notations"):
                        for slur in doc.children(notations, "slur"):
                            grouped[(part.id, slur.get("number", "1"))].append((event, slur, measure.index))
    result = []
    for (part, number), ends in grouped.items():
        # A number is a reusable lane, not a globally unique relationship ID.
        pending = None
        ambiguous = False
        ends.sort(key=lambda x: (x[2], Fraction(x[0].onset or '0'), 0 if x[1].get('type') == 'stop' else 1))
        for event, node, mi in ends:
            kind = node.get('type')
            if kind == 'start':
                if pending is not None: ambiguous = True
                else: pending = (event, node, mi)
            elif kind == 'continue':
                ambiguous = True  # Preserve continuation notation; do not invent its editing contract.
            elif kind == 'stop':
                if pending is not None and not ambiguous:
                    source, start, si = pending
                    if source.onset is not None and event.onset is not None and (si, Fraction(source.onset)) < (mi, Fraction(event.onset)) and (source.voice, source.staff) == (event.voice, event.staff):
                        result.append({'source_event_id':source.id,'target_event_id':event.id,'part_id':part,'number':number,'direction':'down' if start.get('placement')=='below' or (start.get('placement') is None and start.get('orientation')=='under') else 'up'})
                pending = None; ambiguous = False
    return result


def apply(doc, request):
    a = doc.get(request.source_event_id, "note"); b = doc.get(request.target_event_id, "note")
    score, _ = import_score(doc)
    owned = {e.id: (p.id, m.index, e) for p in score.parts for m in p.measures for v in m.voices for e in v.events}
    pa, ma, ea = owned[request.source_event_id]; pb, mb, eb = owned[request.target_event_id]
    if ea.kind != "note" or eb.kind != "note" or pa != pb or (ea.voice, ea.staff) != (eb.voice, eb.staff):
        raise ReviewError("Choose two pitched notes in the same part, voice and staff.")
    if ea.onset is None or eb.onset is None or (ma, Fraction(ea.onset)) >= (mb, Fraction(eb.onset)):
        raise ReviewError("Choose a later destination note.")
    existing = next((p for p in pairs(doc) if p['source_event_id'] == ea.id and p['target_event_id'] == eb.id), None)
    if existing:
        if not request.remove and 'direction' not in request.model_fields_set:
            return False  # Re-selecting an existing pair must not reset its chosen direction.
        for note, kind in ((a, 'start'), (b, 'stop')):
            for n in doc.children(note, "notations"):
                for slur in list(doc.children(n, "slur")):
                    if slur.get("number", "1") == existing['number'] and slur.get('type') == kind:
                        if request.remove: n.remove(slur)
                        else:
                            slur.set("placement", "above" if request.direction == "up" else "below")
                            slur.set("orientation", "over" if request.direction == "up" else "under")
        doc.changed = True
        return
    source_numbers = {s.get('number','1') for n in doc.children(a,'notations') for s in doc.children(n,'slur') if s.get('type') == 'start'}
    target_numbers = {s.get('number','1') for n in doc.children(b,'notations') for s in doc.children(n,'slur') if s.get('type') == 'stop'}
    if source_numbers & target_numbers:
        raise ReviewError('These endpoints contain an ambiguous existing slur; no duplicate was added.',409)
    if request.remove:
        raise ReviewError("This slur is missing or ambiguous; no data changed.", 409)
    used = {n.get("number", "1") for n in doc.root.iter(doc.namespace + "slur")}
    number = next((str(i) for i in range(1, 1001) if str(i) not in used), None)
    if number is None: raise ReviewError("No unambiguous slur number is available.")
    for note, kind in ((a, "start"), (b, "stop")):
        notation = doc.child(note, "notations")
        if notation is None:
            notation = ET.Element(doc.namespace + "notations")
            index = next((i for i, n in enumerate(note) if n.tag in {doc.namespace + t for t in ('lyric', 'play', 'listen')}), len(note))
            note.insert(index, notation)
        ET.SubElement(notation, doc.namespace + "slur", {"type": kind, "number": number, "placement": "above" if request.direction == "up" else "below"})
    doc.changed = True


def disconnect_deleted(doc, event_id):
    for pair in pairs(doc):
        if event_id not in (pair['source_event_id'], pair['target_event_id']): continue
        for identifier, kind in ((pair['source_event_id'],'start'), (pair['target_event_id'],'stop')):
            for n in doc.children(doc.refs[identifier], 'notations'):
                for slur in list(doc.children(n, 'slur')):
                    if slur.get('number', '1') == pair['number'] and slur.get('type') == kind: n.remove(slur)
