import pytest
from app.core.config import Settings
from app.music.review.service import ReviewService
from app.music.review.storage import MemoryReviewStore, Source
from app.music.review.document import ReviewError
from app.music.review.models import EventPatch, PitchInput

XML=b'<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type><lyric number="2"><text>Ngai</text></lyric></note></measure></part></score-partwise>'

def setup():
 c=Settings();store=MemoryReviewStore(c);service=ReviewService(store,c,__import__('time').time);review=service.create(XML);session=store.get(review['id']);session.source=Source(b'original-pdf','application/pdf',1);session.source_evidence=[{'sha256':'retained-evidence','diagnostics':['synthetic retained evidence'],'logical_parts':[]}];return service,store,review

def test_document_correction_preserves_new_ids_source_evidence_and_history():
 service,store,before=setup()
 session=store.get(before['id']);node=session.document.refs.pop('e-1');session.document.refs['new-7-note']=node
 changed=XML.replace(b'<step>C</step>',b'<step>D</step>')
 after=service.document_correction(before['id'],before['revision'],changed)
 assert after['id']==before['id']
 assert 'new-7-note' in store.get(before['id']).document.refs
 assert service.source(before['id']).contents==b'original-pdf'
 assert store.get(before['id']).source_evidence==[{'sha256':'retained-evidence','diagnostics':['synthetic retained evidence'],'logical_parts':[]}]
 assert store.get(before['id']).document.original==XML
 undo=service.history(after['id'],after['revision'],'undo');assert service.musicxml(undo['id'])==XML
 redo=service.history(undo['id'],undo['revision'],'redo');assert b'<step>D</step>' in service.musicxml(redo['id'])

def test_document_correction_is_atomic_and_rejects_note_deletion_and_stale_revision():
 service,store,before=setup()
 with pytest.raises(ReviewError):service.document_correction(before['id'],before['revision'],XML.replace(XML[XML.index(b'<note>'):XML.index(b'</note>')+7],b''))
 assert service.musicxml(before['id'])==XML
 after=service.document_correction(before['id'],before['revision'],XML.replace(b'<step>C</step>',b'<step>D</step>'))
 with pytest.raises(ReviewError):service.document_correction(before['id'],before['revision'],XML)
 assert store.get(before['id']).revision==after['revision']

def test_expression_edits_preserve_note_ids_and_other_relationships():
 from app.music.review.models import NotationEdit
 service,store,before=setup()
 after=service.notation_edit(before['id'],before['revision'],'e-1',NotationEdit(field='dynamic',value='mf'))
 after=service.notation_edit(after['id'],after['revision'],'e-1',NotationEdit(field='dynamic',value='f'))
 data=service.musicxml(after['id']);assert data.count(b'<dynamics>')==1;assert b'<f' in data
 after=service.notation_edit(after['id'],after['revision'],'e-1',NotationEdit(field='dynamic',value='f',remove=True))
 assert b'<dynamics>' not in service.musicxml(after['id'])
 after=service.notation_edit(after['id'],after['revision'],'e-1',NotationEdit(field='fermata',value='normal'))
 after=service.notation_edit(after['id'],after['revision'],'e-1',NotationEdit(field='articulation',value='staccato'))
 assert b'<fermata>normal</fermata>' in service.musicxml(after['id'])
 assert b'<staccato' in service.musicxml(after['id'])
 assert b'number="2"' in service.musicxml(after['id'])
 assert service.source(after['id']).contents==b'original-pdf'
