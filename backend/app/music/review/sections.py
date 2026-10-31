"""Explicit complete-measure copy/transpose/append; no recognition or composition."""
from copy import deepcopy
from fractions import Fraction
from uuid import uuid4
from xml.etree import ElementTree as ET
from .document import Document, ReviewError, local
from .importer import import_score
from .ties import entries_for, current_target, has
from .patcher import put
from app.music.musicxml.concert_key import transpose_concert_key, _interval
from app.music.musicxml.transposer import MusicXMLTranspositionError

def transpose_interval(contents, source, target, mode, semitones, written=False):
    """Use confirmed source interpretation, exact signed interval and existing speller."""
    tonic = 0 if mode == "major" else 9
    if ((tonic+7*target)-(tonic+7*source)-semitones) % 12:
        raise ReviewError("Destination key does not match the selected interval.")
    doc = Document.parse(contents)
    for part in doc.children(doc.root, "part"):
        measures = doc.children(part, "measure")
        if not measures:
            continue
        attributes = doc.child(measures[0], "attributes")
        if attributes is None:
            attributes = ET.Element(doc.namespace+"attributes")
            measures[0].insert(0, attributes)
        keys = doc.children(attributes, "key")
        if not keys:
            keys = [put(doc, attributes, "key", order=["divisions","key","time","staves","clef"])]
        for key in keys:
            put(doc,key,"fifths",source,["cancel","fifths","mode"])
            put(doc,key,"mode",mode,["cancel","fifths","mode"])
    metadata=[]
    if written:
        for pi,part in enumerate(doc.children(doc.root,"part")):
            for mi,measure in enumerate(doc.children(part,"measure")):
                for ai,attrs in enumerate(doc.children(measure,"attributes")):
                    for index,node in list(enumerate(attrs)):
                        if local(node.tag)=="transpose":
                            metadata.append((pi,mi,ai,index,deepcopy(node)))
                            attrs.remove(node)
    doc.changed = True
    direction = "down" if semitones < 0 else "up"
    base, _ = _interval(source,target,mode,direction)
    # Same-key register changes are applied exactly once below.
    result = transpose_concert_key(doc.xml(),target,"up" if source==target else direction,
                                   source_fifths=source,source_mode=mode)
    extra = semitones-base
    if extra % 12:
        raise ReviewError("Unsupported interval.")
    if extra:
        shifted = Document.parse(result)
        for note in shifted.root.iter(shifted.namespace+"note"):
            pitch=shifted.child(note,"pitch")
            if pitch is None:
                continue
            octave=int(shifted.text(pitch,"octave"))+extra//12
            if not 0<=octave<=9:
                raise ReviewError("This interval exceeds the MusicXML octave range.")
            put(shifted,pitch,"octave",octave)
        shifted.changed=True
        result=shifted.xml()
    if metadata:
        restored=Document.parse(result)
        parts=restored.children(restored.root,"part")
        for pi,mi,ai,index,node in metadata:
            attrs=restored.children(restored.children(parts[pi],"measure")[mi],"attributes")[ai]
            attrs.insert(min(index,len(attrs)),node)
        restored.changed=True
        result=restored.xml()
    return result

def append_section(doc, request, sequence):
    score,_=import_score(doc)
    if len(score.parts)!=1 or any(m.staves!=1 for p in score.parts for m in p.measures):
        raise ReviewError("Section v1 supports one part and one staff. Existing score is unchanged.")
    part=score.parts[0]
    ids=[m.id for m in part.measures]
    if request.start_measure_id not in ids or request.end_measure_id not in ids:
        raise ReviewError("Choose existing start and end measures.")
    start,end=ids.index(request.start_measure_id),ids.index(request.end_measure_id)
    if end<start:
        raise ReviewError("End measure must follow the start measure.")
    selected=part.measures[start:end+1]
    selected_ids={e.id for m in selected for v in m.voices for e in v.events}
    entries=entries_for(score)
    selected_ties=[]
    for key in entries:
        node=doc.refs[key]
        if has(doc,node,"start") or has(doc,node,"start",True):
            target=current_target(doc,key,entries)
            if key in selected_ids or target in selected_ids:
                if target is None or (key in selected_ids)!=(target in selected_ids):
                    raise ReviewError("Extend the selection to include the complete tie.")
                selected_ties.append((key,target))
        if key in selected_ids and (has(doc,node,"stop") or has(doc,node,"stop",True)):
            if not any(current_target(doc,s,entries)==key for s in entries if has(doc,doc.refs[s],"start") or has(doc,doc.refs[s],"start",True)):
                raise ReviewError("This selected tie is incomplete; include or correct its connection first.")
    nodes=[doc.refs[m.id] for m in selected]
    if any(local(n.tag) in {"repeat","ending"} for m in nodes for n in m.iter()):
        raise ReviewError("Section v1 cannot copy repeat or ending instructions. Choose a passage without those instructions.")
    # Reject cross-boundary slurs/tuplets instead of inventing clipped connections.
    for tag in ("slur","tuplet"):
        active={}
        for m in nodes:
            for note in doc.children(m,"note"):
                for n in note.iter(doc.namespace+tag):
                    key=(doc.text(note,"voice","1"),doc.text(note,"staff","1"),n.get("number","1"))
                    if n.get("type")=="start":active[key]=active.get(key,0)+1
                    elif n.get("type")=="stop":
                        if active.get(key,0)==0:
                            raise ReviewError("Extend the selection to include the complete "+tag+" on its voice.")
                        active[key]-=1
        if any(active.values()):
            raise ReviewError("Extend the selection to include the complete "+tag+".")
    root=ET.Element(doc.root.tag,doc.root.attrib)
    part_list=doc.child(doc.root,"part-list")
    if part_list is None:raise ReviewError("This score needs its MusicXML part list before copying a section.")
    root.append(deepcopy(part_list))
    excerpt=ET.SubElement(root,doc.namespace+"part",doc.refs[part.id].attrib)
    copies=deepcopy(nodes)
    copied_nodes={id(old):new for m,c in zip(nodes,copies) for old,new in zip(m.iter(),c.iter())}
    for m in copies:excerpt.append(m)
    # Seed inherited context, without altering original measures.
    context={}
    for mi,original in enumerate(doc.children(doc.refs[part.id],"measure")[:start+1]):
        for node in original:
            if local(node.tag) in {"note","forward","backup"} and mi==start:break
            if local(node.tag)=="attributes":
                for field in node:context[(local(field.tag),field.get("number",""))]=deepcopy(field)
    for node in list(copies[0]):
        if local(node.tag) in {"note","forward","backup"}:break
        if local(node.tag)=="attributes":copies[0].remove(node)
    attributes=ET.Element(doc.namespace+"attributes")
    order=["divisions","key","time","staves","part-symbol","instruments","clef","staff-details","transpose","measure-style"]
    for (_,field) in sorted(context.items(),key=lambda kv:order.index(kv[0][0]) if kv[0][0] in order else len(order)):
        attributes.append(field)
    copies[0].insert(0,attributes)
    # XML identity attributes are remapped for the copy only.
    token=uuid4().hex
    tie_tokens={}
    mapping={}
    for node in excerpt.iter():
        if local(node.tag)!="part" and "id" in node.attrib:
            old=node.get("id")
            mapping[old]=("review-tie-"+tie_tokens.setdefault(old[:43],uuid4().hex)+old[43:]) if old.startswith("review-tie-") and len(old)>43 else "section-"+token+"-"+old
    for node in excerpt.iter():
        if node.get("id") in mapping:node.set("id",mapping[node.get("id")])
        for name,value in list(node.attrib.items()):
            if name!="id" and value in mapping:node.set(name,mapping[value])
    used={n.get("number","1") for n in doc.root.iter(doc.namespace+"tied")}
    available=[str(i) for i in range(2,17) if str(i) not in used]
    def position(identifier):
        _,measure,event=entries[identifier]
        return (measure.index,Fraction(event.onset or "0"))
    occupied=[]
    numbered=[]
    for source,target in sorted(selected_ties,key=lambda pair:min(position(pair[0]),position(pair[1]))):
        start_pos,end_pos=sorted([position(source),position(target)])
        occupied=[item for item in occupied if item[1]>start_pos]
        number=next((n for n in available if n not in {item[0] for item in occupied}),None)
        if number is None:
            raise ReviewError("This passage exceeds the available simultaneous MusicXML tie numbers.")
        occupied.append((number,end_pos))
        numbered.append((source,target,number))
    for source,target,number in numbered:
        pair=uuid4().hex
        for identifier,kind in [(source,"start"),(target,"stop")]:
            copied=copied_nodes[id(doc.refs[identifier])]
            notations=doc.child(copied,"notations")
            if notations is None:notations=ET.SubElement(copied,doc.namespace+"notations")
            originals=[n for parent in doc.children(doc.refs[identifier],"notations") for n in doc.children(parent,"tied") if n.get("type")==kind]
            link=doc.manual_ties.get(source)
            if link:
                identity=link.get("source_visual_id" if kind=="start" else "target_visual_id")
                originals=[n for n in originals if n.get("id")==identity]
            else:
                source_marks=[n for parent in doc.children(doc.refs[source],"notations") for n in doc.children(parent,"tied") if n.get("type")=="start"]
                numbers={n.get("number","1") for n in source_marks}
                if len(numbers)==1:originals=[n for n in originals if n.get("number","1") in numbers]
            if len(originals)>1:raise ReviewError("This tie has ambiguous duplicate endpoints.")
            mark=copied_nodes[id(originals[0])] if originals else ET.SubElement(notations,doc.namespace+"tied",{"type":kind})
            mark.set("number",number)
            mark.set("id",f"review-tie-{pair}-s1-t1-{kind}")
    # Remove forced page/system breaks and final barline from the copied fragment.
    for m in copies:
        for child in list(m):
            if local(child.tag)=="print":
                child.attrib.pop("new-system",None);child.attrib.pop("new-page",None)
            if local(child.tag)=="barline" and doc.text(child,"bar-style") in {"light-heavy","heavy-heavy"}:
                m.remove(child)
    raw=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    try:transposed=Document.parse(transpose_interval(raw,request.source_fifths,request.target_fifths,request.mode,request.semitones,written=True))
    except MusicXMLTranspositionError as error:raise ReviewError(str(error)) from error
    new_part=transposed.children(transposed.root,"part")[0]
    new_measures=transposed.children(new_part,"measure")
    # Start a visible new section; preserve all existing original barlines.
    boundary=ET.Element(doc.namespace+"barline",{"location":"left"})
    ET.SubElement(boundary,doc.namespace+"bar-style").text="light-light"
    new_measures[0].insert(0,boundary)
    last_original=part.measures[-1].number
    number=int(last_original) if last_original.isdigit() else len(part.measures)
    refs_by_node={}
    for key,node in transposed.refs.items():refs_by_node.setdefault(id(node),[]).append(key)
    new_ref_ids={}
    for index,m in enumerate(new_measures,1):
        m.set("number",str(number+index))
        doc.refs[part.id].append(m)
        for node in m.iter():
            for key in refs_by_node.get(id(node),[]):
                new_id="section-"+sequence+"-"+key
                doc.refs[new_id]=node
                new_ref_ids[key]=new_id
    for source,link in transposed.manual_ties.items():
        copied_link=deepcopy(link)
        copied_link["target"]=new_ref_ids[link["target"]]
        doc.manual_ties[new_ref_ids[source]]=copied_link
    # Preserve original barlines; the appended section receives its own final barline.
    final=ET.SubElement(new_measures[-1],doc.namespace+"barline",{"location":"right"})
    ET.SubElement(final,doc.namespace+"bar-style").text="light-heavy"
    doc.changed=True
    return {"count":len(new_measures),"first_number":str(number+1),"last_number":str(number+len(new_measures))}
