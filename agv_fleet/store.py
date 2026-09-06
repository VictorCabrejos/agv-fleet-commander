"""One atomic snapshot transaction holds vehicle, task, route, receipt and trace."""

import copy
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Protocol

from .domain import ConflictError, DomainError, State, StorageError


class Store(Protocol):
    def read(self) -> State: ...
    def commit(self, expected: int, state: State) -> None: ...


class MemoryStore:
    def __init__(self, state):
        state.validate()
        self._state = copy.deepcopy(state)
        self._lock = RLock()

    def read(self):
        with self._lock:
            return copy.deepcopy(self._state)

    def commit(self, expected, state):
        state.validate()
        if state.revision != expected + 1:
            raise DomainError("Commit must advance exactly one revision")
        with self._lock:
            if expected != self._state.revision:
                raise ConflictError("Stale state revision; submit a fresh proposal")
            self._state = copy.deepcopy(state)


class SQLiteStore:
    def __init__(self, path, initial):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        initial.validate()
        try:
            with self._connect() as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS fleet (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL)"
                )
                db.execute(
                    "INSERT OR IGNORE INTO fleet VALUES (1, ?, ?)", (initial.revision, self._encode(initial))
                )
        except sqlite3.Error as exc:
            raise StorageError("Cannot initialize fleet storage") from exc
        self.read()  # Corrupt or incompatible state fails closed; never silently resets.

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _encode(state):
        return json.dumps(state.encode(), allow_nan=False, sort_keys=True, separators=(",", ":"))

    def read(self):
        try:
            with self._connect() as db:
                row = db.execute("SELECT revision, body FROM fleet WHERE id=1").fetchone()
            state = State.decode(json.loads(row[1]))
            if state.revision != row[0]:
                raise StorageError("Stored revision disagrees with snapshot")
            return state
        except (sqlite3.Error, ValueError, TypeError, KeyError, IndexError) as exc:
            raise StorageError("Cannot read a valid fleet snapshot") from exc

    def commit(self, expected, state):
        state.validate()
        if state.revision != expected + 1:
            raise DomainError("Commit must advance exactly one revision")
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                cursor = db.execute(
                    "UPDATE fleet SET revision=?, body=? WHERE id=1 AND revision=?",
                    (state.revision, self._encode(state), expected),
                )
                if cursor.rowcount != 1:
                    raise ConflictError("Stale state revision; submit a fresh proposal")
                self._before_commit(db)
        except sqlite3.Error as exc:
            raise StorageError("State transaction failed; operation not acknowledged") from exc

    def _before_commit(self, db):
        """Fault-injection seam; transaction context rolls back on any exception."""
