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
        import importlib.util
        present = self.available()
        deps = {name: importlib.util.find_spec(name) is not None
                for name in ("onnxruntime", "tokenizers", "numpy")}
        runnable = present and all(deps.values())
        return {"available": runnable, "package_present": present,
                "dependencies": deps, "engine": "onnxruntime", "package_dir": self.package_dir,
                "error": self._load_error if runnable else
                    (self._load_error or "Missing ONNX Runtime dependencies or package"),
                "version": ROUTER_VERSION}

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
            import numpy as np
            from .encoder import Encoder
            with open(os.path.join(self.package_dir, "classifier.json")) as fh:
                meta = json.load(fh)
            self._labels = meta["labels"]
            if set(self._labels) != {"CHAT", "CODE", "SYSTEM", "ASK"}:
                raise ValueError("Invalid classifier labels")
            self._weights = np.asarray(meta["weights"], dtype=np.float64)
            self._bias = np.asarray(meta["bias"], dtype=np.float64)
            self._references = np.asarray(meta["references"], dtype=np.float64)
            if self._weights.shape != (4,384) or self._bias.shape != (4,) or self._references.ndim != 2 or self._references.shape[1] != 384:
                raise ValueError("Classifier dimension mismatch")
            if not all(np.isfinite(x).all() for x in [self._weights,self._bias,self._references]):
                raise ValueError("Non-finite classifier")
            self._temperature = float(meta["temperature"])
            if not .1 <= self._temperature <= 10:
                raise ValueError("Invalid calibration temperature")
            self._thresholds = meta["thresholds"]
            self._session = Encoder(self.package_dir, self.threads)
            self._load_error = None
            return True
        except Exception as exc:
            self._load_error = "%s: %s" % (type(exc).__name__, exc)
            self._session = None
            return False

    def classify(self, text):
        if self._session is None and not self.load():
            return None, 0.0
        try:
            import numpy as np
            vector = self._session.encode([text])[0]
            if float((self._references @ vector).max()) < self._thresholds["similarity"]:
                return {"ASK": 1.0}, 1.0
            logits = (self._weights @ vector + self._bias) / self._temperature
            probs = np.exp(logits - logits.max())
            probs /= probs.sum()
            ordered = sorted(probs, reverse=True)
            return dict(zip(self._labels, map(float, probs))), float(ordered[0]-ordered[1])
        except Exception as exc:
            self._load_error = "inference failed: %s" % exc
            return None, 0.0

    def unload(self):
        self._session = None
        for name in ("_weights", "_bias", "_references"):
            if hasattr(self, name):
                delattr(self, name)


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
