"""User-directed, non-nested tuplets on complete rhythmic selections."""
from copy import deepcopy
from fractions import Fraction
from math import lcm
from xml.etree import ElementTree as ET
from .document import ReviewError, local
from .patcher import context, group, put, position_context, duration_patch
from .importer import rational
from .triplets import refine_divisions, xml_units

VALUES = {'whole': Fraction(4), 'half': Fraction(2), 'quarter': Fraction(1),
          'eighth': Fraction(1,2), '16th': Fraction(1,4), '32nd': Fraction(1,8), '64th': Fraction(1,16)}


def edit_tuplet(doc, identifier, request):
    if len(set(request.event_ids)) != len(request.event_ids):
        raise ReviewError('Select each rhythmic event once.')
    nodes = [doc.get(key, 'note') for key in request.event_ids]
    measure = doc.parent(nodes[0])
    if any(doc.parent(n) is not measure for n in nodes):
        raise ReviewError('Select one measure; cross-measure tuplets are not supported.')
    selected = set(nodes)
    if any(set(group(doc,n)) - selected for n in nodes):
        raise ReviewError('Select every member of each chord.')
    nodes.sort(key=lambda n:list(measure).index(n))
    indexes = [list(measure).index(n) for n in nodes]
    if indexes != list(range(indexes[0],indexes[0]+len(nodes))):
        raise ReviewError('Select consecutive rhythmic positions; intervening objects are preserved.')
    groups=[]
    for n in nodes:
        members=group(doc,n)
        if not groups or members!=groups[-1]: groups.append(members)
    events=[context(doc,g[0])[1] for g in groups]
    first=events[0]
    if any(e.kind not in ('note','rest') or e.grace or e.cue or e.voice!=first.voice or e.staff!=first.staff or rational(e.onset) is None or rational(e.duration) is None for e in events):
        raise ReviewError('Select timed notes or rests in one voice and staff.')
    if any(rational(b.onset)!=rational(a.onset)+rational(a.duration) for a,b in zip(events,events[1:])):
        raise ReviewError('Select contiguous rhythmic positions.')
    # Reject incomplete, nested or ambiguous existing membership, including groups
    # whose boundaries lie outside this selection.
    active={}; starts=[]; stops=[]
    for n in measure:
        if local(n.tag)!='note':continue
        for mark in n.iter():
            if local(mark.tag)!='tuplet':continue
            number=mark.get('number','1');kind=mark.get('type')
            if kind=='start':
                if n in selected:
                    if active:raise ReviewError('Nested tuplets are not supported by this editor.')
                    starts.append(mark)
                active[number]=n
            elif kind=='stop':
                owner=active.pop(number,None)
                if n in selected:
                    if owner not in selected:raise ReviewError('Select the complete existing tuplet.')
                    stops.append(mark)
                elif owner in selected:raise ReviewError('Select the complete existing tuplet.')
        if n in selected and any(owner not in selected for owner in active.values()):
            raise ReviewError('Select the complete enclosing tuplet.')
    if any(owner in selected for owner in active.values()):raise ReviewError('The tuplet has no matching end.')
    modified=[n for n in nodes if doc.child(n,'time-modification') is not None]
    if modified and (len(modified)!=len(nodes) or len(starts)!=1 or len(stops)!=1):
        raise ReviewError('Select exactly one complete, non-nested tuplet.')
    if request.action=='remove' and not modified:
        raise ReviewError('Select an existing tuplet to remove its ratio.')
    written=[]
    for g in groups:
        if request.action=='split':
            written.append(rational(first.duration));continue
        value=VALUES.get(doc.text(g[0],'type'))
        dots=len(doc.children(g[0],'dot'))
        if value is None or dots>2:raise ReviewError('Choose supported written note values with at most two dots.')
        value*=sum((Fraction(1,2**i) for i in range(dots+1)),Fraction())
        if any(doc.text(n,'type')!=doc.text(g[0],'type') or len(doc.children(n,'dot'))!=dots for n in g):
            raise ReviewError('Chord members must have matching written durations.')
        written.append(value)
    measure_id=next(k for k,v in doc.refs.items() if v is measure)
    info,_,scale=position_context(doc,measure_id)
    onset=rational(first.onset);old_span=sum((rational(e.duration) for e in events),Fraction())
    ratio=Fraction(1) if request.action=='remove' else Fraction(request.normal_notes,request.actual_notes)
    if request.action=='split':
        if len(groups)!=1 or modified:raise ReviewError('Select one ordinary note, chord or rest to divide.')
        base=old_span/request.normal_notes
        if base not in VALUES.values():raise ReviewError('This span and ratio need unsupported written values; choose another ratio or edit a mixed selection.')
        written=[base]*request.actual_notes
    elif request.action=='apply' and len(groups)<2:
        raise ReviewError('Select at least two positions, or use Divide selected duration.')
    unit=sum(written,Fraction())/request.actual_notes
    unit_spelling=next(((kind,dots) for kind,base in VALUES.items() for dots in range(3)
                        if base*sum((Fraction(1,2**i) for i in range(dots+1)),Fraction())==unit),None)
    if request.action!='remove' and unit_spelling is None:
        raise ReviewError('The written selection does not form the requested number of supported tuplet units. Adjust the written values or divide a suitable duration.')
    effective=[v*ratio for v in written];new_span=sum(effective,Fraction())
    for voice in info.voices:
        for e in voice.events:
            if e.id in request.event_ids or e.voice!=first.voice or e.grace:continue
            start,duration=rational(e.onset),rational(e.duration)
            if start is not None and duration is not None and onset<start+duration and start<onset+new_span:
                raise ReviewError('The new tuplet would overlap another event. Choose space or adjust the selection first.')
    factor=lcm(*[(v*scale).denominator for v in effective+written+[onset,old_span,new_span]])
    scale=refine_divisions(doc,measure,scale,factor)
    # Remove only the selected group's ratio and boundaries; retain ties/slurs,
    # lyrics, accidentals, identities and unrelated notations.
    for n in nodes:
        for child in doc.children(n,'time-modification'):n.remove(child)
        for container in doc.children(n,'notations'):
            for mark in list(container):
                if local(mark.tag)=='tuplet':container.remove(mark)
    if request.action=='split':
        original=groups[0];at=list(measure).index(original[-1])+1;new_groups=[original]
        for position in range(1,request.actual_notes):
            members=[]
            for j,source in enumerate(original):
                n=ET.Element(doc.namespace+'note')
                for tag in ['chord','pitch','rest','voice','staff','accidental']:
                    for child in doc.children(source,tag):n.append(deepcopy(child))
                measure.insert(at,n);at+=1;members.append(n)
                doc.refs[f'{identifier}-tuplet-{position}-{j}']=n
            new_groups.append(members)
        groups=new_groups
    for i,(members,value,duration) in enumerate(zip(groups,written,effective)):
        for n in members:
            rest=doc.child(n,'rest')
            if rest is not None:rest.attrib.pop('measure',None)
            duration_patch(doc,n,str(value),str(scale))
            put(doc,n,'duration',xml_units(duration*scale))
            if request.action!='remove':
                modification=put(doc,n,'time-modification')
                ET.SubElement(modification,doc.namespace+'actual-notes').text=str(request.actual_notes)
                ET.SubElement(modification,doc.namespace+'normal-notes').text=str(request.normal_notes)
                ET.SubElement(modification,doc.namespace+'normal-type').text=unit_spelling[0]
                for _ in range(unit_spelling[1]):ET.SubElement(modification,doc.namespace+'normal-dot')
        if request.action!='remove' and i in (0,len(groups)-1):
            # A single-position group is not offered; split always has >=2.
            marks=put(doc,members[0],'notations')
            if i==0:ET.SubElement(marks,doc.namespace+'tuplet',{'type':'start','number':'1','bracket':request.bracket,'placement':request.placement,'show-number':request.show_number})
            if i==len(groups)-1:ET.SubElement(marks,doc.namespace+'tuplet',{'type':'stop','number':'1'})
    delta=old_span-new_span
    if delta:
        shift=ET.Element(doc.namespace+('forward' if delta>0 else 'backup'))
        ET.SubElement(shift,doc.namespace+'duration').text=xml_units(abs(delta)*scale)
        measure.insert(list(measure).index(groups[-1][-1])+1,shift)
    doc.manual_changes[measure_id]=sorted(set(doc.manual_changes.get(measure_id,[]))|{'events','tuplet'})
    for key,n in doc.refs.items():
        if any(n in g for g in groups):doc.manual_changes[key]=sorted(set(doc.manual_changes.get(key,[]))|{'tuplet','duration'})
    doc.changed=True
