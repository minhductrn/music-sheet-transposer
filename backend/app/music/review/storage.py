"""Replaceable, bounded local storage. IDs are capabilities, never paths."""

from dataclasses import dataclass, field
from threading import RLock
import time
from typing import Protocol

from app.core.config import Settings
from app.music.review.document import Document, ReviewError


@dataclass(frozen=True)
class Source:
    contents: bytes
    media_type: str
    pages: int


@dataclass
class ReviewSession:
    id: str
    document: Document
    source: Source | None
    expires_at: float
    state: str = "DRAFT"
    revision: int = 1
    sequence: int = 0
    undo: list[Document] = field(default_factory=list)
    redo: list[Document] = field(default_factory=list)

    def weight(self):
        return (self.document.weight() + (len(self.source.contents) if self.source else 0)
                + sum(d.weight() for d in self.undo + self.redo))


class ReviewStore(Protocol):
    lock: RLock

    def get(self, identifier: str) -> ReviewSession: ...
    def put(self, session: ReviewSession) -> None: ...
    def delete(self, identifier: str) -> None: ...
    def cleanup(self) -> int: ...


class MemoryReviewStore:
    """One process only. Fixed lifetimes, explicit release, and cleanup on access."""

    def __init__(self, config: Settings, clock=time.time):
        self.config, self.clock = config, clock
        self.lock = RLock()
        self._sessions: dict[str, ReviewSession] = {}

    def cleanup(self) -> int:
        with self.lock:
            expired = [key for key, session in self._sessions.items() if session.expires_at <= self.clock()]
            for key in expired:
                del self._sessions[key]
            return len(expired)

    def get(self, identifier: str) -> ReviewSession:
        with self.lock:
            self.cleanup()
            if identifier not in self._sessions:
                raise ReviewError("Review session was not found or has expired. Import the source again.", 404)
            return self._sessions[identifier]

    def put(self, session: ReviewSession) -> None:
        with self.lock:
            self.cleanup()
            if session.expires_at <= self.clock():
                raise ReviewError("Review session expired during the request. Import the source again.", 404)
            existing = self._sessions.get(session.id)
            if existing is None and len(self._sessions) >= self.config.review_max_sessions:
                raise ReviewError("Review storage is full. Close a review or wait for expiry.", 503)
            total = sum(item.weight() for key, item in self._sessions.items() if key != session.id) + session.weight()
            if total > self.config.review_max_total_bytes:
                raise ReviewError("Review storage exceeds its memory budget. Download corrections and close an unused review.", 503)
            self._sessions[session.id] = session

    def delete(self, identifier: str) -> None:
        with self.lock:
            self.get(identifier)
            del self._sessions[identifier]
