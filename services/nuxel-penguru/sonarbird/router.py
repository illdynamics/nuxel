#!/usr/bin/env python3
"""SonarBird router: Tier 0 rules + Tier 1 classifier policy.

The router selects a worker or ASK.  It never outputs approval, capabilities or
tool parameters.  Tier 1 is a standard ONNX Runtime encoder + Nuxel-trained
logistic head; if its package is missing the router still works using Tier 0
and abstains where it is not high-precision.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import rules

ROUTER_VERSION = "sonarbird-router-2026.11.15"
# Experimental starting points (not safety guarantees): a clear CHAT/CODE
# decision needs a calibrated probability at or above HIGH; the band between
# LOW and HIGH asks for clarification instead of guessing.
DEFAULT_HIGH = 0.82
DEFAULT_LOW = 0.60
MAX_MARGIN_SUPPRESSED = 0.10

# Classifier outputs that must never dispatch a heavy worker: SYSTEM needs a
# deterministic typed parse, and ASK is by definition uncertain.
CLASSIFIER_DISPATCHABLE = ("CHAT", "CODE")


@dataclass
class Route:
    route: str
    confidence: float
    reason_code: str
    router_version: str = ROUTER_VERSION
    worker: Optional[str] = None
    decision_source: str = "rules"

    def as_dict(self):
        return {
            "route": self.route,
            "confidence": round(float(self.confidence), 4),
            "reason_code": self.reason_code,
            "router_version": self.router_version,
            "worker": self.worker,
            "decision_source": self.decision_source,
        }


def _worker_for(route: str) -> Optional[str]:
    return {"CHAT": "chatbird", "CODE": "codebird"}.get(route)


class Classifier:
    """Optional Tier 1 inference.  Absent package => available() is False."""

    def __init__(self, package_dir: Optional[str] = None, threads: int = 2):
        self.package_dir = package_dir or os.environ.get(
            "NUXEL_SONARBIRD_PACKAGE", "/var/lib/nuxel-penguru/models/sonarbird")
        self.threads = max(1, int(threads))
        self._session = None
        self._labels = ["CHAT", "CODE", "SYSTEM", "ASK"]
        self._thresholds = {"high": DEFAULT_HIGH, "low": DEFAULT_LOW}
        self._load_error = None

    def status(self) -> Dict[str, Any]:
        return {"available": self.available(), "package_dir": self.package_dir,
                "error": self._load_error, "version": ROUTER_VERSION}

    def available(self) -> bool:
        if self._session is not None:
            return True
        if not os.path.isdir(self.package_dir):
            self._load_error = "package not installed"
            return False
        return all(os.path.exists(os.path.join(self.package_dir, f)) for f in (
            "encoder.onnx", "classifier.json", "tokenizer.json"))

    def load(self):
        if self._session is not None:
            return True
        try:
            import numpy as np  # noqa: F401
            import onnxruntime as ort
            meta_path = os.path.join(self.package_dir, "classifier.json")
            with open(meta_path) as fh:
                meta = json.load(fh)
            self._labels = list(meta.get("labels") or self._labels)
            th = meta.get("thresholds") or {}
            self._thresholds = {
                "high": float(th.get("high", DEFAULT_HIGH)),
                "low": float(th.get("low", DEFAULT_LOW)),
            }
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = self.threads
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                os.path.join(self.package_dir, "encoder.onnx"), opts,
                providers=["CPUExecutionProvider"])
            self._meta = meta
            self._load_error = None
            return True
        except Exception as exc:  # noqa: BLE001 - absent runtime = rules only
            self._load_error = "%s: %s" % (type(exc).__name__, exc)
            self._session = None
            return False

    def classify(self, text: str):
        """Return (probabilities dict, margin) or (None, 0.0) when unavailable."""
        if self._session is None and not self.load():
            return None, 0.0
        try:
            import numpy as np
            tok = self._meta.get("tokenizer", {})
            max_len = int(tok.get("max_length", 128))
            voc = tok.get("vocab", {})
            ids = [voc.get("[CLS]", 101)]
            for word in text.lower().split():
                ids.append(voc.get(word, voc.get("[UNK]", 100)))
                if len(ids) >= max_len - 1:
                    break
            ids.append(voc.get("[SEP]", 102))
            mask = [1] * len(ids)
            while len(ids) < max_len:
                ids.append(0)
                mask.append(0)
            feeds = {"input_ids": np.array([ids], dtype=np.int64),
                     "attention_mask": np.array([mask], dtype=np.int64)}
            for name in self._session.get_inputs():
                if name.name not in feeds and name.name == "token_type_ids":
                    feeds[name.name] = np.zeros((1, max_len), dtype=np.int64)
            out = self._session.run(None, feeds)[0][0]
            probs = np.exp(out - out.max())
            probs = probs / probs.sum()
            ordered = sorted(probs, reverse=True)
            margin = float(ordered[0] - ordered[1]) if len(ordered) > 1 else 1.0
            return ({lab: float(p) for lab, p in zip(self._labels, probs)}, margin)
        except Exception as exc:  # noqa: BLE001
            self._load_error = "inference failed: %s" % exc
            return None, 0.0


def route(text: str, classifier: Optional[Classifier] = None) -> Route:
    d = rules.route_rules(text)
    if d.label == "ASK":
        return Route("ASK", 1.0, d.rule_id)
    if d.label in ("CHAT", "CODE", "SYSTEM"):
        return Route(d.label, 1.0, d.rule_id, worker=_worker_for(d.label),
                     decision_source="rules")

    # Tier 1.  A classifier assertion can only choose CHAT/CODE, and only with
    # a high calibrated probability AND a clear margin; SYSTEM/ASK outputs
    # abstain.  Without a package, Tier 0 abstention is final.
    if classifier is None or not classifier.available():
        return Route("ASK", 0.0, "R_TIER1_UNAVAILABLE")
    probs, margin = classifier.classify(text)
    if not probs:
        return Route("ASK", 0.0, "R_TIER1_ERROR")
    label = max(probs, key=probs.get)
    conf = float(probs[label])
    low = classifier._thresholds.get("low", DEFAULT_LOW)
    high = classifier._thresholds.get("high", DEFAULT_HIGH)
    if label not in CLASSIFIER_DISPATCHABLE:
        return Route("ASK", conf, "R_TIER1_NONDISPATCH")
    if conf < low:
        return Route("ASK", conf, "R_TIER1_LOW_CONFIDENCE")
    if conf < high or margin < MAX_MARGIN_SUPPRESSED:
        return Route("ASK", conf, "R_TIER1_UNCERTAIN")
    return Route(label, conf, "R_TIER1_" + label, worker=_worker_for(label),
                 decision_source="classifier")
