#!/usr/bin/env python3
"""Line-delimited JSON protocol between the control plane and a model worker.

The worker is unprivileged, receives no broker credentials and no network.  It
reads one JSON job from stdin and writes events to stdout.  The control plane
only accepts a closed event vocabulary.
"""
from __future__ import annotations

import json
from typing import Any, Dict

SCHEMA_VERSION = 1
EVENT_KINDS = {"loading", "loaded", "token", "progress", "cancelled", "oom",
               "error", "unloaded", "done", "health"}


class ProtocolError(ValueError):
    pass


def encode(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"


def decode_event(line: str) -> Dict[str, Any]:
    try:
        doc = json.loads(line)
    except ValueError as exc:
        raise ProtocolError("worker emitted non-JSON output") from exc
    if not isinstance(doc, dict):
        raise ProtocolError("worker event is not an object")
    kind = doc.get("event")
    if kind not in EVENT_KINDS:
        raise ProtocolError("unknown worker event %r" % (kind,))
    return doc


def validate_job(doc: Any) -> Dict[str, Any]:
    if not isinstance(doc, dict):
        raise ProtocolError("job must be an object")
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ProtocolError("unsupported job schema")
    for key in ("op", "model", "package_dir"):
        if not isinstance(doc.get(key), str) or not doc[key]:
            raise ProtocolError("job.%s is required" % key)
    if doc["op"] not in ("generate", "self_test", "load_test"):
        raise ProtocolError("unsupported op")
    if len(doc.get("prompt", "") or "") > 64000:
        raise ProtocolError("prompt exceeds the limit")
    opts = doc.get("options") or {}
    if not isinstance(opts, dict):
        raise ProtocolError("options must be an object")
    return doc
