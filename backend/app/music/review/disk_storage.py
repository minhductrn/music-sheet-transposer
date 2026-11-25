"""Optional local preview store: atomic JSON checkpoints, never executable data."""
from base64 import b64encode,b64decode
from pathlib import Path
import json
import os
import time
from .storage import MemoryReviewStore,ReviewSession,Source
from .document import Document


def encode_document(doc):
    from xml.etree import ElementTree as ET
    indices={n:i for i,n in enumerate(doc.root.iter())}
    return {'xml':b64encode(ET.tostring(doc.root,encoding='utf-8')).decode(),'original':b64encode(doc.original).decode(),'changed':doc.changed,'refs':{k:indices[n] for k,n in doc.refs.items()},'manual_changes':doc.manual_changes,'manual_ties':doc.manual_ties,'candidate_events':doc.candidate_events,'positioned_events':sorted(doc.positioned_events),'source_confirmations':doc.source_confirmations}


def decode_document(data):
    doc=Document.parse(b64decode(data['xml']));nodes=list(doc.root.iter())
    doc.refs={k:nodes[i] for k,i in data['refs'].items()}
    doc.original=b64decode(data['original']);doc.changed=data['changed']
    for field in ('manual_changes','manual_ties','candidate_events','source_confirmations'):setattr(doc,field,data[field])
    doc.positioned_events=set(data['positioned_events'])
    return doc


class DiskReviewStore(MemoryReviewStore):
    def __init__(self,config,directory,clock=time.time,protected_ids=()):
        super().__init__(config,clock)
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.protected_ids=set(protected_ids)
        for path in self.directory.glob('*.json'):
            data=json.loads(path.read_text())
            if data['expires_at']<=clock():continue
            source=data.pop('source');data['source']=Source(b64decode(source['contents']),source['media_type'],source['pages']) if source else None
            data['document']=decode_document(data['document']);data['undo']=[decode_document(d) for d in data['undo']];data['redo']=[decode_document(d) for d in data['redo']]
            super().put(ReviewSession(**data))

    def put(self,session):
        with self.lock:
            previous=self._sessions.get(session.id)
            super().put(session)
            target=self.directory/(session.id+'.json');temporary=target.with_suffix('.tmp')
            try:
                data={k:getattr(session,k) for k in ('id','expires_at','state','revision','sequence','semantic_recovery','source_evidence')}
                data.update(document=encode_document(session.document),undo=[encode_document(d) for d in session.undo],redo=[encode_document(d) for d in session.redo],source={'contents':b64encode(session.source.contents).decode(),'media_type':session.source.media_type,'pages':session.source.pages} if session.source else None)
                with temporary.open('w') as stream:
                    json.dump(data,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
                os.chmod(temporary,0o600);temporary.replace(target)
            except Exception:
                if previous is None:self._sessions.pop(session.id,None)
                else:self._sessions[session.id]=previous
                temporary.unlink(missing_ok=True)
                raise

    def delete(self,identifier):
        with self.lock:
            # Only explicitly protected recovery sessions ignore stale pagehide
            # releases from the older owner tab. Other sessions delete normally.
            if identifier in self.protected_ids:return
            super().delete(identifier)
            (self.directory/(identifier+'.json')).unlink(missing_ok=True)
