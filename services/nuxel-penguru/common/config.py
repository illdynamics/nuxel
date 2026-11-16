#!/usr/bin/env python3
"""Minimal, strict TOML configuration loader (stdlib tomllib).

Configuration expresses preferences only.  Capabilities and approvals live in
the canonical permission subsystem; nothing here can grant authority.
"""
from __future__ import annotations

import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "mode": "squad",
    "runtime_preference": "auto",
    "enable_llama_cpp": True,
    "enable_ort_genai": False,
    "max_heavy_workers": 1,
    "idle_unload_seconds": 120,
    "threads": 4,
    "sonarbird_enabled_in_squad": True,
    "low_confidence_action": "ask",
    "network_for_workers": False,
    "raw_prompt_routing_logs": False,
    "keep_prompt_text": False,
    "wake_word_enabled": False,
    "wake_word_background": False,
    "push_to_talk": False,
    "per_model_engine": {},
}
ALLOWED = set(DEFAULTS)


def load(path: str) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    try:
        import tomllib
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
    except FileNotFoundError:
        return cfg
    except Exception:
        # A malformed config is reported by the caller; never guess values.
        raise
    flat: Dict[str, Any] = {}
    for k, v in doc.items():
        if k in ("penguru", "privacy", "voice") and isinstance(v, dict):
            for kk, vv in v.items():
                flat[kk] = vv
        elif k == "runtime" and isinstance(v, dict):
            for kk, vv in v.items():
                flat[kk] = vv
        elif k == "models" and isinstance(v, dict):
            per = {}
            for mid, mv in v.items():
                if isinstance(mv, dict) and mv.get("preferred_engine"):
                    per[mid] = mv["preferred_engine"]
            flat["per_model_engine"] = per
        else:
            flat[k] = v
    for k, v in flat.items():
        if k in ALLOWED:
            cfg[k] = v
    # Invariants that are not preferences.
    cfg["max_heavy_workers"] = 1
    cfg["network_for_workers"] = False
    return cfg
