"""Explicit editable identities for non-note pedal marks; no music inference."""
from fractions import Fraction
from .document import local,ReviewError
from .importer import rational

def marks(doc):
 result=[];reverse={node:key for key,node in doc.refs.items()}
 for part in doc.children(doc.root,'part'):
  scale=Fraction(1)
  for measure in doc.children(part,'measure'):
   cursor=Fraction(0)
   for i,node in enumerate(measure):
    tag=local(node.tag)
    if tag=='attributes':
     value=doc.text(node,'divisions')
     if value:scale=rational(value)
     if scale is not None and scale<=0:scale=None
    elif tag in ('forward','backup'):
     duration=rational(doc.text(node,'duration','0'));cursor=cursor+duration/scale*(-1 if tag=='backup' else 1) if cursor is not None and duration is not None and scale else None
    elif tag=='note' and doc.child(node,'chord') is None and doc.child(node,'grace') is None:
     duration=rational(doc.text(node,'duration','0'));cursor=cursor+duration/scale if cursor is not None and duration is not None and scale else None
    elif tag=='direction':
     for j,kind in enumerate(doc.children(node,'direction-type')):
      for k,pedal in enumerate(kind):
       if local(pedal.tag) not in ('pedal','dynamics','wedge','metronome','segno','coda'):continue
       result.append({'id':f'{reverse[measure]}:{i}:{j}:{k}','kind':local(pedal.tag),'measure_id':reverse[measure],'onset':str(cursor+(rational(doc.text(node,'offset','0')) or 0)/scale) if cursor is not None and scale else None,'staff':int(doc.text(node,'staff','1')) if doc.text(node,'staff','1').isdigit() else None,'type':pedal.get('type','') or ' '.join(local(c.tag) for c in pedal)})
 return result

def delete_mark(doc,identifier):
 try:
  mid,i,j,k=identifier.rsplit(':',3)
  if any(int(v)<0 for v in (i,j,k)):raise ValueError('Invalid mark index')
  measure=doc.get(mid,'measure');direction=list(measure)[int(i)];kind=doc.children(direction,'direction-type')[int(j)];mark=list(kind)[int(k)]
 except (ValueError,IndexError):raise ReviewError('The selected score mark no longer exists.',409) from None
 if local(direction.tag)!='direction' or local(mark.tag) not in ('pedal','dynamics','wedge','metronome','segno','coda'):raise ReviewError('The selected object is not an editable score mark.',409)
 kind.remove(mark)
 # Remove playback attributes belonging to this deleted symbol, while retaining
 # independent tempo and other sound data. Do not affect a surviving same-kind mark.
 attribute={'pedal':'damper-pedal','dynamics':'dynamics'}.get(local(mark.tag))
 if attribute and not any(local(child.tag)==local(mark.tag) for child in direction.iter()):
  for sound in list(doc.children(direction,'sound')):
   sound.attrib.pop(attribute,None)
   if not sound.attrib and not len(sound) and not (sound.text or '').strip():direction.remove(sound)
 if not len(kind):direction.remove(kind)
 if not doc.children(direction,'direction-type'):
  if any(local(c.tag) not in ('staff','voice','offset') for c in direction):
   # Retain independent playback data in its original position. MusicXML
   # requires a direction-type, so use an invisible empty words anchor.
   from xml.etree import ElementTree as ET
   anchor=ET.Element(doc.namespace+'direction-type')
   ET.SubElement(anchor,doc.namespace+'words').text=''
   direction.insert(0,anchor)
  else:
   measure.remove(direction)
 doc.changed=True
