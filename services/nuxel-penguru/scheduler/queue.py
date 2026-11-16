#!/usr/bin/env python3
"""Persistent PenGuru request queue (SQLite, local only).

Requests are bound to the authenticated app identity and an opaque client
session id resolved by the control plane.  Raw text is stored only when the
owner's retention setting keeps it; otherwise only routing metadata remains.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
  id TEXT PRIMARY KEY,
  app_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  conversation_id TEXT,
  mode TEXT NOT NULL,
  runtime_preference TEXT NOT NULL,
  text TEXT,
  text_sha256 TEXT,
  status TEXT NOT NULL,
  route TEXT,
  reason_code TEXT,
  confidence REAL,
  worker TEXT,
  engine TEXT,
  provider TEXT,
  variant_id TEXT,
  revision TEXT,
  output TEXT,
  error TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  cancelled INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS requests_owner ON requests(app_id, session_id, created_at);
"""
TERMINAL = ("done", "error", "cancelled", "awaiting_user")


class RequestQueue:
    def __init__(self, path: str, keep_text: bool = False):
        self.path = path
        self.keep_text = keep_text
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

    def submit(self, app_id: str, session_id: str, mode: str,
               runtime_preference: str, text: str,
               conversation_id: Optional[str] = None) -> Dict[str, Any]:
        rid = str(uuid.uuid4())
        now = time.time()
        import hashlib
        with self._lock:
            self._db.execute(
                "INSERT INTO requests (id, app_id, session_id, conversation_id,"
                " mode, runtime_preference, text, text_sha256, status,"
                " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid, app_id, session_id, conversation_id, mode,
                 runtime_preference, text[:64000] if self.keep_text else None,
                 hashlib.sha256(text.encode("utf-8")).hexdigest(),
                 "queued", now, now))
            self._db.commit()
        return {"request_id": rid, "status": "queued"}

    def update(self, rid: str, **fields) -> None:
        allowed = {"status", "route", "reason_code", "confidence", "worker",
                   "engine", "provider", "variant_id", "revision", "output",
                   "error", "cancelled", "conversation_id"}
        cols, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                cols.append("%s=?" % k)
                vals.append(v)
        if not cols:
            return
        cols.append("updated_at=?")
        vals.append(time.time())
        vals.append(rid)
        with self._lock:
            self._db.execute("UPDATE requests SET %s WHERE id=?" % ", ".join(cols), vals)
            self._db.commit()

    def get(self, rid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._db.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
        return dict(row) if row else None

    def owned(self, rid: str, app_id: str, session_id: str) -> bool:
        r = self.get(rid)
        return bool(r and r["app_id"] == app_id and r["session_id"] == session_id)

    def request_cancel(self, rid: str, app_id: str, session_id: str) -> bool:
        if not self.owned(rid, app_id, session_id):
            return False
        r = self.get(rid)
        if r["status"] in TERMINAL:
            return False
        self.update(rid, cancelled=1, error="cancelled_by_owner")
        return True

    def pending_count(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) AS n FROM requests WHERE status NOT IN (%s)"
                % ",".join("?" * len(TERMINAL)), TERMINAL).fetchone()
        return int(row["n"])

    def delete_conversation(self, app_id: str, session_id: str,
                            conversation_id: str) -> int:
        with self._lock:
            cur = self._db.execute(
                "DELETE FROM requests WHERE app_id=? AND session_id=? AND conversation_id=?",
                (app_id, session_id, conversation_id))
            self._db.commit()
        return cur.rowcount

    def clear_all(self, app_id: str, session_id: str) -> int:
        with self._lock:
            cur = self._db.execute(
                "DELETE FROM requests WHERE app_id=? AND session_id=?",
                (app_id, session_id))
            self._db.commit()
        return cur.rowcount
