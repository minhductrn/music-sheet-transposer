from dataclasses import replace
from pathlib import Path
import pytest
from app.core.config import Settings
from app.music.review.disk_storage import DiskReviewStore
from app.music.review.document import Document,ReviewError
from app.music.review.storage import ReviewSession,Source
from test_phase4e_workflow import XML


def session():
    doc=Document.parse(XML);doc.refs['new-99']=doc.refs.pop('e-1');doc.positioned_events={'new-99'};doc.manual_changes={'new-99':['voice']}
    return ReviewSession('synthetic-review',doc,Source(b'original-pdf','application/pdf',2),2000,revision=114,sequence=100,undo=[doc.clone()],source_evidence=[{'sha256':'synthetic'}])


def test_restart_retains_bytes_ids_history_source_and_metadata(tmp_path):
    config=Settings();first=DiskReviewStore(config,tmp_path,lambda:1000);original=session();first.put(original)
    restored=DiskReviewStore(config,tmp_path,lambda:1000).get(original.id)
    assert restored.document.xml()==original.document.xml()
    assert restored.document.get('new-99','note') in list(restored.document.root.iter())
    assert restored.document.manual_changes==original.document.manual_changes
    assert restored.document.positioned_events=={'new-99'}
    assert restored.source==original.source and restored.revision==114 and restored.sequence==100
    assert restored.undo[0].xml()==original.undo[0].xml()


def test_only_explicit_recovery_session_ignores_stale_owner_release(tmp_path):
    config=Settings();store=DiskReviewStore(config,tmp_path,lambda:1000,protected_ids=['synthetic-review']);original=session();store.put(original);store.delete(original.id)
    assert store.get(original.id).revision==114
    other=replace(original,id='ordinary-session');store.put(other);store.delete(other.id)
    with pytest.raises(ReviewError):store.get(other.id)
    assert not (tmp_path/'ordinary-session.json').exists()


def test_checkpoint_write_failure_does_not_commit_memory_edit(tmp_path,monkeypatch):
    store=DiskReviewStore(Settings(),tmp_path,lambda:1000);original=session();store.put(original)
    def fail(*args):raise OSError('synthetic disk failure')
    monkeypatch.setattr(Path,'replace',fail)
    with pytest.raises(OSError):store.put(replace(original,revision=115))
    assert store.get(original.id).revision==114
    assert DiskReviewStore(Settings(),tmp_path,lambda:1000).get(original.id).revision==114
