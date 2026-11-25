"""Explicit draft rhythm edits. Musical diagnostics never veto these commands."""
from copy import deepcopy
from fractions import Fraction
from math import lcm
from xml.etree import ElementTree as ET
from .document import local, ReviewError
from .importer import rational
from .patcher import context, group, put, duration_patch, remove
from .triplets import refine_divisions, xml_units

VALUES={'maxima':32,'long':16,'breve':8,'whole':4,'half':2,'quarter':1,'eighth':Fraction(1,2),'16th':Fraction(1,4),'32nd':Fraction(1,8),'64th':Fraction(1,16),'128th':Fraction(1,32),'256th':Fraction(1,64)}

def edit_draft_tuplet(doc,identifier,request):
    selected={doc.get(key,'note') for key in request.event_ids}
    original_ids={node:key for key,node in doc.refs.items() if node in selected}
    blocks=[];seen=set()
    for node in list(doc.root.iter()):
        if node not in selected:continue
        members=group(doc,node);leader=members[0]
        if leader in seen:continue
        seen.add(leader);chosen=[n for n in members if n in selected]
        blocks.append((members,chosen))
    boundaries=[]
    original_written={n: None for _,chosen in blocks for n in chosen}
    def shift(measure,at,delta,scale):
        if not delta:return at
        n=ET.Element(doc.namespace+('forward' if delta>0 else 'backup'))
        ET.SubElement(n,doc.namespace+'duration').text=xml_units(abs(delta)*scale)
        measure.insert(at,n);return at+1
    def written(n,event):
        base=VALUES.get(doc.text(n,'type'))
        if base is not None:return Fraction(base)*sum((Fraction(1,2**i) for i in range(len(doc.children(n,'dot'))+1)),Fraction())
        value=rational(event.duration)
        if value is None or value<=0:raise ReviewError('The selected note has no readable duration to divide. Its XML is unchanged.')
        return value
    for n in original_written:
        original_written[n]=written(n,context(doc,n)[1])
    for block_index,(members,chosen) in enumerate(blocks):
        if request.action=='remove' and not any(doc.child(n,'time-modification') is not None or any(local(x.tag)=='tuplet' for x in n.iter()) for n in chosen):continue
        measure=doc.parent(members[0]);mid=next(k for k,v in doc.refs.items() if v is measure)
        infos=[context(doc,n) for n in chosen];events=[e for _,e in infos]
        scale=rational(infos[0][0].divisions)
        if scale is None or scale<=0:raise ReviewError('The selected note has no readable divisions for a duration edit. Its XML is unchanged.')
        ratio=Fraction(request.normal_notes,request.actual_notes)
        splitting=request.action=='split' or (request.action=='mixed' and len(blocks)==1)
        count=(2 if request.action=='mixed' else request.actual_notes) if splitting else 1
        values=[];durations=[]
        for n,e in zip(chosen,events):
            span=rational(e.duration) if not e.grace else written(n,e)
            if splitting:
                if span is None or span<=0:raise ReviewError('The selected note has no readable duration to divide. Its XML is unchanged.')
                effective=([span*Fraction(2,3),span*Fraction(1,3)] if request.action=='mixed' else [span/count]*count)
                visual=[v/ratio for v in effective]
            else:
                visual=[original_written[n]]
                if request.action=='mixed':visual=[visual[0] if block_index%2==0 else original_written[blocks[block_index-1][1][0]]/2]
                effective=[visual[0] if request.action=='remove' else visual[0]*ratio]
            values.append(visual);durations.append(effective)
        factor=lcm(*[(v*scale).denominator for row in values+durations for v in row])
        scale=refine_divisions(doc,measure,scale,factor)
        leader_grace=doc.child(members[0],'grace') is not None
        leader_units=rational(doc.text(members[0],'duration'))
        if not leader_grace and leader_units is None:raise ReviewError('The selected XML duration cannot be read. No changes applied.')
        old_advance=Fraction(0) if leader_grace else leader_units/scale
        # Apply changes at their explicit original positions. Never repack notes.
        displacement=Fraction(0)
        all_positions=[chosen]
        for position in range(1,count):
            new_members=[]
            for j,n in enumerate(chosen):
                clone=ET.Element(doc.namespace+'note',{k:v for k,v in n.attrib.items() if k!='id'})
                for tag in ['grace','cue','pitch','rest','unpitched','voice','staff','accidental','stem','notehead','type','dot']:
                    for child in doc.children(n,tag):clone.append(deepcopy(child))
                if j:put(doc,clone,'chord')
                doc.refs[f'{identifier}-split-{block_index}-{position}-{j}']=clone
                new_members.append(clone)
            all_positions.append(new_members)
        for position,notes in enumerate(all_positions):
            for j,n in enumerate(notes):
                remove(doc,n,'time-modification')
                for container in doc.children(n,'notations'):
                    for mark in list(container):
                        if local(mark.tag)=='tuplet':container.remove(mark)
                grace=doc.child(n,'grace') is not None
                duration_patch(doc,n,str(values[j][position]),str(scale),grace,draft_edit=True)
                if not grace:put(doc,n,'duration',xml_units(durations[j][position]*scale))
                if request.action!='remove':
                    modification=put(doc,n,'time-modification')
                    ET.SubElement(modification,doc.namespace+'actual-notes').text=str(request.actual_notes)
                    ET.SubElement(modification,doc.namespace+'normal-notes').text=str(request.normal_notes)
        new_advance=Fraction(0) if leader_grace else rational(doc.text(members[0],'duration'))/scale
        if splitting and count>1:
            at=list(measure).index(members[-1])+1
            first_span=Fraction(0) if events[0].grace else durations[0][0]
            at=shift(measure,at,first_span-new_advance,scale)
            total=first_span
            for notes in all_positions[1:]:
                for n in notes:measure.insert(at,n);at+=1
                if not events[0].grace:total+=rational(doc.text(notes[0],'duration'))/scale
            shift(measure,at,old_advance-total,scale)
            boundaries.append((all_positions[0][0],all_positions[-1][0]))
        else:
            at=list(measure).index(members[0]);shift(measure,at,displacement,scale)
            shift(measure,list(measure).index(members[-1])+1,old_advance-new_advance-displacement,scale)
            boundaries.append((chosen[0],chosen[-1]))
        doc.manual_changes[mid]=sorted(set(doc.manual_changes.get(mid,[]))|{'events','tuplet'})
        for n in chosen:doc.manual_changes[original_ids[n]]=sorted(set(doc.manual_changes.get(original_ids[n],[]))|{'duration','tuplet'})
    if request.action!='remove' and boundaries:
        pairs=boundaries if request.action in ('split','mixed') else [(boundaries[0][0],boundaries[-1][1])]
        for first,last in pairs:
            start=put(doc,first,'notations');ET.SubElement(start,doc.namespace+'tuplet',{'type':'start','number':'1','bracket':request.bracket,'placement':request.placement,'show-number':request.show_number})
            stop=put(doc,last,'notations');ET.SubElement(stop,doc.namespace+'tuplet',{'type':'stop','number':'1'})
    doc.changed=True
