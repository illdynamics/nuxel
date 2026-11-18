#!/usr/bin/env python3
"""PenGuru lifecycle state machine.

    DISABLED -> IDLE -> ROUTING -> LOADING -> ACTIVE
    ACTIVE -> DRAINING -> UNLOADING -> IDLE
    any -> WAITING_USER (ASK) | ERROR
"""
from __future__ import annotations

from typing import Dict, Iterable

STATES = ("DISABLED", "IDLE", "ROUTING", "LOADING", "ACTIVE", "WAITING_USER",
          "DRAINING", "UNLOADING", "ERROR")

TRANSITIONS = {
    "DISABLED": {"IDLE"},
    "IDLE": {"ROUTING", "LOADING", "DISABLED", "ERROR"},
    "ROUTING": {"ACTIVE", "LOADING", "WAITING_USER", "IDLE", "ERROR"},
    "LOADING": {"ACTIVE", "IDLE", "ERROR"},
    "ACTIVE": {"ACTIVE", "DRAINING", "IDLE", "WAITING_USER", "ERROR"},
    "WAITING_USER": {"IDLE", "ROUTING", "LOADING", "DISABLED", "ERROR"},
    "DRAINING": {"UNLOADING", "ERROR"},
    "UNLOADING": {"IDLE", "LOADING", "DISABLED", "ERROR"},
    "ERROR": {"IDLE", "DISABLED"},
}


class InvalidTransition(RuntimeError):
    pass


class Lifecycle:
    def __init__(self):
        self.state = "DISABLED"
        self.history = ["DISABLED"]

    def can(self, target: str) -> bool:
        return target in TRANSITIONS.get(self.state, set())

    def set(self, target: str) -> str:
        if target not in STATES:
            raise InvalidTransition("unknown state %r" % target)
        if target == self.state:
            return self.state
        if not self.can(target):
            raise InvalidTransition("%s -> %s" % (self.state, target))
        self.state = target
        self.history.append(target)
        del self.history[:-64]
        return self.state

    def as_dict(self) -> Dict[str, object]:
        return {"state": self.state, "history": list(self.history[-8:])}
